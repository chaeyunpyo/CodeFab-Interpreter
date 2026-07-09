"""상수 연산 최적화 (요구사항_정리/실행전_최적화.md).

리터럴로만 구성된 Binary/Unary/Grouping을 AST에서 직접 LiteralExpr로
치환한다. 폴딩 가능 여부 판단 규칙은 Executor의 _evaluate_binary/
_evaluate_unary(src/executor/_expr.py)와 동일하게 맞춰서, 접었을 때
런타임 오류가 나는 조합(0으로 나누기 등)은 접지 않고 원본을 보존한다.
"""

import dataclasses
import operator

from nodes.expr import BinaryExpr, Expr, GroupingExpr, LiteralExpr, UnaryExpr
from nodes.token_type import TokenType

_NOT_FOLDABLE = object()

_NUMERIC_BINARY_OPS = {
    TokenType.MINUS: operator.sub,
    TokenType.STAR: operator.mul,
    TokenType.GREATER: operator.gt,
    TokenType.LESS: operator.lt,
    TokenType.GREATER_EQUAL: operator.ge,
    TokenType.LESS_EQUAL: operator.le,
    TokenType.EQUAL_GREATER: operator.ge,
    TokenType.EQUAL_LESS: operator.le,
    TokenType.EQUAL_EQUAL: operator.eq,
    TokenType.BANG_EQUAL: operator.ne,
}


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_string(value):
    return isinstance(value, str)


def _fold_binary_value(operator_token, left, right):
    """Executor의 _evaluate_binary와 같은 규칙으로 계산하되, 접을 수 없으면 _NOT_FOLDABLE."""
    op = operator_token.type

    if op == TokenType.SLASH:
        if _is_number(left) and _is_number(right) and right != 0:
            return left / right
        return _NOT_FOLDABLE

    if op == TokenType.PLUS:
        if _is_string(left) and _is_string(right):
            return left + right
        if _is_number(left) and _is_number(right):
            return left + right
        return _NOT_FOLDABLE

    numeric_op = _NUMERIC_BINARY_OPS.get(op)
    if numeric_op is not None and _is_number(left) and _is_number(right):
        return numeric_op(left, right)

    return _NOT_FOLDABLE


def _fold_unary_value(operator_token, value):
    """Executor의 _evaluate_unary와 같은 규칙으로 계산하되, 접을 수 없으면 _NOT_FOLDABLE."""
    op = operator_token.type

    if op == TokenType.MINUS:
        return -value if _is_number(value) else _NOT_FOLDABLE
    if op == TokenType.PLUS:
        return value if _is_number(value) else _NOT_FOLDABLE
    if op == TokenType.BANG:
        return not value

    return _NOT_FOLDABLE


class ConstantFolder:
    """리터럴로만 구성된 Binary/Unary/Grouping을 접어서 LiteralExpr로 치환한다.

    변수가 섞여 있거나, 접었을 때 런타임 오류가 나는 조합(0으로 나누기
    등)은 원본 그대로 둔다.
    """

    def fold(self, expr):
        if not isinstance(expr, Expr):
            return expr

        if isinstance(expr, GroupingExpr):
            expr.expression = self.fold(expr.expression)
            if isinstance(expr.expression, LiteralExpr):
                return LiteralExpr(expr.expression.value)
            return expr

        if isinstance(expr, UnaryExpr):
            expr.right = self.fold(expr.right)
            if isinstance(expr.right, LiteralExpr):
                folded = _fold_unary_value(expr.operator, expr.right.value)
                if folded is not _NOT_FOLDABLE:
                    return LiteralExpr(folded)
            return expr

        if isinstance(expr, BinaryExpr):
            expr.left = self.fold(expr.left)
            expr.right = self.fold(expr.right)
            if isinstance(expr.left, LiteralExpr) and isinstance(expr.right, LiteralExpr):
                folded = _fold_binary_value(expr.operator, expr.left.value, expr.right.value)
                if folded is not _NOT_FOLDABLE:
                    return LiteralExpr(folded)
            return expr

        for field in dataclasses.fields(expr):
            value = getattr(expr, field.name)
            if isinstance(value, Expr):
                setattr(expr, field.name, self.fold(value))
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, Expr):
                        value[i] = self.fold(item)

        return expr
