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
from storage import Storage


class ExecutionError(Exception):
    """Executor 실행 중 발생하는 오류의 최상위 타입."""


class TypeMismatchError(ExecutionError):
    """피연산자 타입이 연산자와 맞지 않을 때. 예: 3 - "hello" (PDF p.86)"""


class DivideByZeroError(ExecutionError):
    """나눗셈의 제수(divisor)가 0일 때. 예: 3 / 0 (PDF p.88)"""


def evaluate(expr: Expr, storage: Storage) -> Any:
    """Expr 트리를 재귀적으로 평가해 값 하나를 반환한다."""
    raise NotImplementedError("evaluate() 를 구현해주세요.")


def execute(stmt: Stmt, storage: Storage) -> None:
    """Stmt 하나를 실행한다."""
    raise NotImplementedError("execute() 를 구현해주세요.")


def stringify(value: Any) -> str:
    """print 출력 / 오류 메시지에 쓸 문자열 표현을 만든다.

    정수 값을 갖는 float(예: 5.0)은 "5.0"이 아닌 "5"로 표시한다.
    (PDF p.77 실행 예시 "print(5) 출력" 참고)
    """
    raise NotImplementedError("stringify() 를 구현해주세요.")
