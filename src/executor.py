"""Executor: Expression 평가와 Statement 실행을 함께 처리한다.

Public API:
    evaluate(expr, storage) -> Any   - Expr 트리를 평가해 값 하나를 반환
    execute(stmt, storage) -> None   - Stmt 하나를 실행 (부수효과만 발생)
    stringify(value) -> str          - print 출력 / 오류 메시지용 문자열 변환

"""

import operator
from typing import Any, Callable, Dict, Type

from nodes import (
    AssignExpr,
    BinaryExpr,
    BlockStmt,
    Expr,
    ExpressionStmt,
    ForStmt,
    GroupingExpr,
    IfStmt,
    LiteralExpr,
    LogicalExpr,
    PrintStmt,
    Stmt,
    UnaryExpr,
    VarDeclStmt,
    VariableExpr,
)
from nodes.token_type import TokenType
from storage import Storage


class ExecutionError(Exception):
    """Executor 실행 중 발생하는 오류의 최상위 타입."""


class TypeMismatchError(ExecutionError):
    """피연산자 타입이 연산자와 맞지 않을 때. 예: 3 - "hello" (PDF p.86)"""


class DivideByZeroError(ExecutionError):
    """나눗셈의 제수(divisor)가 0일 때. 예: 3 / 0 (PDF p.88)"""


def _is_number(value: Any) -> bool:
    # bool은 int의 서브클래스라서 True/False가 숫자로 오인되지 않도록 따로 걸러낸다.
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _check_number_operand(value: Any) -> None:
    if not _is_number(value):
        raise TypeMismatchError("피연산자는 반드시 숫자여야 합니다.")


def _check_number_operands(left: Any, right: Any) -> None:
    if not _is_number(left) or not _is_number(right):
        raise TypeMismatchError("피연산자는 반드시 숫자여야 합니다.")


# ── Expression 평가 ───────────────────────────────────────────────────────────


def _evaluate_literal(expr: LiteralExpr, storage: Storage) -> Any:
    return expr.value


def _evaluate_variable(expr: VariableExpr, storage: Storage) -> Any:
    return storage.get(expr.name.lexeme)


def _evaluate_assign(expr: AssignExpr, storage: Storage) -> Any:
    value = evaluate(expr.value, storage)
    storage.set(expr.name.lexeme, value)
    return value


def _evaluate_grouping(expr: GroupingExpr, storage: Storage) -> Any:
    return evaluate(expr.expression, storage)


def _evaluate_unary(expr: UnaryExpr, storage: Storage) -> Any:
    right = evaluate(expr.right, storage)
    if expr.operator.type == TokenType.MINUS:
        _check_number_operand(right)
        return -right
    if expr.operator.type == TokenType.BANG:
        return not right
    raise TypeMismatchError(f"지원하지 않는 단항 연산자 '{expr.operator.lexeme}'")


def _evaluate_logical(expr: LogicalExpr, storage: Storage) -> Any:
    left = evaluate(expr.left, storage)
    if expr.operator.type == TokenType.OR:
        if left:
            return left
        return evaluate(expr.right, storage)
    # AND: 왼쪽이 falsy면 오른쪽을 평가하지 않고 그대로 반환한다 (단축 평가).
    if not left:
        return left
    return evaluate(expr.right, storage)


# SLASH는 0으로 나누기 검사가 별도로 필요해서 이 dict에는 넣지 않고 따로 처리한다.
_NUMERIC_BINARY_OPS: Dict[TokenType, Callable[[Any, Any], Any]] = {
    TokenType.PLUS: operator.add,
    TokenType.MINUS: operator.sub,
    TokenType.STAR: operator.mul,
    TokenType.GREATER: operator.gt,
    TokenType.LESS: operator.lt,
}


def _evaluate_binary(expr: BinaryExpr, storage: Storage) -> Any:
    left = evaluate(expr.left, storage)
    right = evaluate(expr.right, storage)
    op = expr.operator.type

    if op == TokenType.SLASH:
        _check_number_operands(left, right)
        if right == 0:
            raise DivideByZeroError("0으로 나눌 수 없습니다.")
        return left / right

    numeric_op = _NUMERIC_BINARY_OPS.get(op)
    if numeric_op is None:
        raise TypeMismatchError(f"지원하지 않는 이항 연산자 '{expr.operator.lexeme}'")
    _check_number_operands(left, right)
    return numeric_op(left, right)


_EXPR_EVALUATORS: Dict[Type[Expr], Callable[[Any, Storage], Any]] = {
    LiteralExpr: _evaluate_literal,
    VariableExpr: _evaluate_variable,
    AssignExpr: _evaluate_assign,
    GroupingExpr: _evaluate_grouping,
    UnaryExpr: _evaluate_unary,
    LogicalExpr: _evaluate_logical,
    BinaryExpr: _evaluate_binary,
}


def evaluate(expr: Expr, storage: Storage) -> Any:
    """Expr 트리를 재귀적으로 평가해 값 하나를 반환한다."""
    handler = _EXPR_EVALUATORS.get(type(expr))
    if handler is None:
        raise NotImplementedError(f"{type(expr).__name__} 평가는 아직 구현되지 않았습니다.")
    return handler(expr, storage)


# ── Statement 실행 ────────────────────────────────────────────────────────────


def _execute_expression_stmt(stmt: ExpressionStmt, storage: Storage) -> None:
    evaluate(stmt.expression, storage)


def _execute_print_stmt(stmt: PrintStmt, storage: Storage) -> None:
    value = evaluate(stmt.expression, storage)
    print(stringify(value))


def _execute_var_decl_stmt(stmt: VarDeclStmt, storage: Storage) -> None:
    value = evaluate(stmt.initializer, storage) if stmt.initializer is not None else None
    storage.define(stmt.name.lexeme, value)


def _execute_block_stmt(stmt: BlockStmt, storage: Storage) -> None:
    # PDF p.82-83 : 블록 진입 시 새 로컬 스코프 생성, 종료 시 소멸.
    storage.push_scope()
    try:
        for inner_stmt in stmt.statements:
            execute(inner_stmt, storage)
    finally:
        storage.pop_scope()


def _execute_if_stmt(stmt: IfStmt, storage: Storage) -> None:
    if evaluate(stmt.condition, storage):
        execute(stmt.then_branch, storage)
    elif stmt.else_branch is not None:
        execute(stmt.else_branch, storage)


def _execute_for_stmt(stmt: ForStmt, storage: Storage) -> None:
    """C-style ForStmt를 실행한다. for (initializer; condition; increment) body"""
    if stmt.initializer is not None:
        execute(stmt.initializer, storage)
    while True:
        if stmt.condition is not None:
            if not evaluate(stmt.condition, storage):
                break
        execute(stmt.body, storage)
        if stmt.increment is not None:
            evaluate(stmt.increment, storage)


_STMT_EXECUTORS: Dict[Type[Stmt], Callable[[Any, Storage], None]] = {
    ExpressionStmt: _execute_expression_stmt,
    PrintStmt: _execute_print_stmt,
    VarDeclStmt: _execute_var_decl_stmt,
    BlockStmt: _execute_block_stmt,
    IfStmt: _execute_if_stmt,
    ForStmt: _execute_for_stmt,
}


def execute(stmt: Stmt, storage: Storage) -> None:
    """Stmt 하나를 실행한다."""
    handler = _STMT_EXECUTORS.get(type(stmt))
    if handler is None:
        raise NotImplementedError(f"{type(stmt).__name__} 실행은 아직 구현되지 않았습니다.")
    handler(stmt, storage)


def stringify(value: Any) -> str:
    """print 출력 / 오류 메시지에 쓸 문자열 표현을 만든다.

    정수 값을 갖는 float(예: 5.0)은 "5.0"이 아닌 "5"로 표시한다.
    (PDF p.77 실행 예시 "print(5) 출력" 참고)
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return str(value)
    return str(value)
