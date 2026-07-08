import operator
from typing import Any, Callable, Dict, Type

from nodes import (
    AssignExpr,
    BinaryExpr,
    Expr,
    GroupingExpr,
    LiteralExpr,
    LogicalExpr,
    UnaryExpr,
    VariableExpr,
)
from nodes.token_type import TokenType
from ._storage import Storage
from .errors import DivideByZeroError, TypeMismatchError, UndefinedVariableError


def _is_number(value: Any) -> bool:
    # bool은 int의 서브클래스라서 True/False가 숫자로 오인되지 않도록 따로 걸러낸다.
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _check_number_operand(value: Any, token) -> None:
    if not _is_number(value):
        raise TypeMismatchError("피연산자는 반드시 숫자여야 합니다.", token)


def _check_number_operands(left: Any, right: Any, token) -> None:
    if not _is_number(left) or not _is_number(right):
        raise TypeMismatchError("피연산자는 반드시 숫자여야 합니다.", token)


def _is_string(value: Any) -> bool:
    return isinstance(value, str)


def _evaluate_literal(expr: LiteralExpr, storage: Storage) -> Any:
    return expr.value


def _evaluate_variable(expr: VariableExpr, storage: Storage) -> Any:
    try:
        return storage.get(expr.name.lexeme)
    except UndefinedVariableError as e:
        e.token = expr.name
        raise


def _evaluate_assign(expr: AssignExpr, storage: Storage) -> Any:
    value = evaluate(expr.value, storage)
    try:
        storage.set(expr.name.lexeme, value)
    except UndefinedVariableError as e:
        e.token = expr.name
        raise
    return value


def _evaluate_grouping(expr: GroupingExpr, storage: Storage) -> Any:
    return evaluate(expr.expression, storage)


def _evaluate_unary(expr: UnaryExpr, storage: Storage) -> Any:
    right = evaluate(expr.right, storage)
    if expr.operator.type == TokenType.MINUS:
        _check_number_operand(right, expr.operator)
        return -right
    if expr.operator.type == TokenType.PLUS:
        _check_number_operand(right, expr.operator)
        return right
    if expr.operator.type == TokenType.BANG:
        return not right
    raise TypeMismatchError(f"지원하지 않는 단항 연산자 '{expr.operator.lexeme}'", expr.operator)


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
    TokenType.GREATER_EQUAL: operator.ge,
    TokenType.LESS_EQUAL: operator.le,
    # EQUAL_GREATER("=>")/EQUAL_LESS("=<")는 GREATER_EQUAL/LESS_EQUAL과 의미가 같은 별칭 토큰이다.
    TokenType.EQUAL_GREATER: operator.ge,
    TokenType.EQUAL_LESS: operator.le,
    TokenType.EQUAL_EQUAL: operator.eq,
    TokenType.BANG_EQUAL: operator.ne,
}


def _evaluate_binary(expr: BinaryExpr, storage: Storage) -> Any:
    left = evaluate(expr.left, storage)
    right = evaluate(expr.right, storage)
    op = expr.operator.type

    if op == TokenType.SLASH:
        _check_number_operands(left, right, expr.operator)
        if right == 0:
            raise DivideByZeroError("0으로 나눌 수 없습니다.", expr.operator)
        return left / right

    if op == TokenType.PLUS and _is_string(left) and _is_string(right):
        return left + right

    numeric_op = _NUMERIC_BINARY_OPS.get(op)
    if numeric_op is None:
        raise TypeMismatchError(f"지원하지 않는 이항 연산자 '{expr.operator.lexeme}'", expr.operator)
    _check_number_operands(left, right, expr.operator)
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
