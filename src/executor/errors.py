from typing import Optional

from nodes.tokens import Token


class ExecutionError(Exception):
    """Executor 실행 중 발생하는 오류의 최상위 타입."""

    def __init__(self, message: str, token: Optional[Token] = None):
        super().__init__(message)
        self.token = token


class TypeMismatchError(ExecutionError):
    """피연산자 타입이 연산자와 맞지 않을 때. 예: 3 - "hello" (PDF p.86)"""


class DivideByZeroError(ExecutionError):
    """나눗셈의 제수(divisor)가 0일 때. 예: 3 / 0 (PDF p.88)"""


class UndefinedVariableError(ExecutionError):
    """정의되지 않은 변수를 참조하거나 대입할 때. 예: print x; (PDF p.87)"""

    def __init__(self, name: str, token: Optional[Token] = None):
        super().__init__(f"Undefined variable '{name}'", token)
        self.name = name
