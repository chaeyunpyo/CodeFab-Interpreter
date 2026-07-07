"""Executor: Expression 평가와 Statement 실행을 함께 처리한다.

Public API:
    evaluate(expr, storage) -> Any   - Expr 트리를 평가해 값 하나를 반환
    execute(stmt, storage) -> None   - Stmt 하나를 실행 (부수효과만 발생)
    stringify(value) -> str          - print 출력 / 오류 메시지용 문자열 변환
"""

from .errors import DivideByZeroError, ExecutionError, TypeMismatchError, UndefinedVariableError
from ._storage import Storage
from ._expr import evaluate, stringify
from ._stmt import execute

__all__ = [
    "ExecutionError",
    "TypeMismatchError",
    "DivideByZeroError",
    "UndefinedVariableError",
    "Storage",
    "evaluate",
    "execute",
    "stringify",
]
