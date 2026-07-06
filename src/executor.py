"""Executor: Expression 평가와 Statement 실행을 함께 처리한다.

Public API:
    evaluate(expr, storage) -> Any   - Expr 트리를 평가해 값 하나를 반환
    execute(stmt, storage) -> None   - Stmt 하나를 실행 (부수효과만 발생)
    stringify(value) -> str          - print 출력 / 오류 메시지용 문자열 변환

TDD Red 단계 - tests/test_executor.py 를 통과하도록 구현해나갈 것.
"""

from typing import Any

from nodes import (
    AssignExpr,
    BinaryExpr,
    BlockStmt,
    Expr,
    ExpressionStmt,
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


def evaluate(expr: Expr, storage: Storage) -> Any:
    """Expr 트리를 재귀적으로 평가해 값 하나를 반환한다."""
    if isinstance(expr, LiteralExpr):
        return expr.value

    if isinstance(expr, VariableExpr):
        return storage.get(expr.name.lexeme)

    if isinstance(expr, AssignExpr):
        value = evaluate(expr.value, storage)
        storage.set(expr.name.lexeme, value)
        return value

    if isinstance(expr, GroupingExpr):
        return evaluate(expr.expression, storage)

    if isinstance(expr, UnaryExpr):
        right = evaluate(expr.right, storage)
        if expr.operator.type == TokenType.MINUS:
            _check_number_operand(right)
            return -right
        if expr.operator.type == TokenType.BANG:
            return not right
        raise TypeMismatchError(f"지원하지 않는 단항 연산자 '{expr.operator.lexeme}'")

    if isinstance(expr, LogicalExpr):
        left = evaluate(expr.left, storage)
        if expr.operator.type == TokenType.OR:
            if left:
                return left
            return evaluate(expr.right, storage)
        # AND: 왼쪽이 falsy면 오른쪽을 평가하지 않고 그대로 반환한다 (단축 평가).
        if not left:
            return left
        return evaluate(expr.right, storage)

    if isinstance(expr, BinaryExpr):
        left = evaluate(expr.left, storage)
        right = evaluate(expr.right, storage)
        op = expr.operator.type

        if op == TokenType.PLUS:
            _check_number_operands(left, right)
            return left + right
        if op == TokenType.MINUS:
            _check_number_operands(left, right)
            return left - right
        if op == TokenType.STAR:
            _check_number_operands(left, right)
            return left * right
        if op == TokenType.SLASH:
            _check_number_operands(left, right)
            if right == 0:
                raise DivideByZeroError("0으로 나눌 수 없습니다.")
            return left / right
        if op == TokenType.GREATER:
            _check_number_operands(left, right)
            return left > right
        if op == TokenType.LESS:
            _check_number_operands(left, right)
            return left < right
        raise TypeMismatchError(f"지원하지 않는 이항 연산자 '{expr.operator.lexeme}'")

    raise NotImplementedError(f"{type(expr).__name__} 평가는 아직 구현되지 않았습니다.")


def execute(stmt: Stmt, storage: Storage) -> None:
    """Stmt 하나를 실행한다."""
    if isinstance(stmt, ExpressionStmt):
        evaluate(stmt.expression, storage)
        return

    if isinstance(stmt, PrintStmt):
        value = evaluate(stmt.expression, storage)
        print(stringify(value))
        return

    if isinstance(stmt, VarDeclStmt):
        value = evaluate(stmt.initializer, storage) if stmt.initializer is not None else None
        storage.define(stmt.name.lexeme, value)
        return

    if isinstance(stmt, BlockStmt):
        # PDF p.82-83 : 블록 진입 시 새 로컬 스코프 생성, 종료 시 소멸.
        storage.push_scope()
        try:
            for inner_stmt in stmt.statements:
                execute(inner_stmt, storage)
        finally:
            storage.pop_scope()
        return

    if isinstance(stmt, IfStmt):
        if evaluate(stmt.condition, storage):
            execute(stmt.then_branch, storage)
        elif stmt.else_branch is not None:
            execute(stmt.else_branch, storage)
        return

    raise NotImplementedError(f"{type(stmt).__name__} 실행은 아직 구현되지 않았습니다.")


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
