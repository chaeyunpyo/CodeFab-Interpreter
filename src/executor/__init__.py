"""Executor: Expression 평가와 Statement 실행을 함께 처리한다.

Public API:
    evaluate(expr, storage) -> Any   - Expr 트리를 평가해 값 하나를 반환
    execute(stmt, storage) -> None   - Stmt 하나를 실행 (부수효과만 발생)
    stringify(value) -> str          - print 출력 / 오류 메시지용 문자열 변환
"""

from .errors import (
    ArityMismatchError,
    DivideByZeroError,
    ExecutionError,
    IndexOutOfRangeError,
    InvalidArraySizeError,
    InvalidIndexTypeError,
    NotAClassError,
    NotAnArrayError,
    NotAnInstanceError,
    NotCallableError,
    TypeMismatchError,
    UndefinedPropertyError,
    UndefinedVariableError,
)
from ._array import FabArray
from ._storage import Storage
from ._signals import ReturnSignal
from ._callable import LoxCallable
from ._function import Function
from ._class import LoxClass, LoxInstance
from ._namespace import LoxNamespace
from ._expr import evaluate, stringify
from ._stmt import execute

__all__ = [
    "ExecutionError",
    "TypeMismatchError",
    "DivideByZeroError",
    "UndefinedVariableError",
    "NotCallableError",
    "ArityMismatchError",
    "IndexOutOfRangeError",
    "InvalidIndexTypeError",
    "NotAnArrayError",
    "InvalidArraySizeError",
    "NotAnInstanceError",
    "UndefinedPropertyError",
    "NotAClassError",
    "FabArray",
    "ReturnSignal",
    "LoxCallable",
    "Function",
    "LoxClass",
    "LoxInstance",
    "LoxNamespace",
    "Storage",
    "evaluate",
    "execute",
    "stringify",
]
