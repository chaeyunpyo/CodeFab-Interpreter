from typing import Optional

from nodes.tokens import Token
from source_error import SourceError


class ExecutionError(SourceError):
    """Executor 실행 중 발생하는 오류의 최상위 타입."""

    UNIT = "Executor"


class TypeMismatchError(ExecutionError):
    """피연산자 타입이 연산자와 맞지 않을 때. 예: 3 - "hello" (PDF p.86)"""


class DivideByZeroError(ExecutionError):
    """나눗셈의 제수(divisor)가 0일 때. 예: 3 / 0 (PDF p.88)"""


class UndefinedVariableError(ExecutionError):
    """정의되지 않은 변수를 참조하거나 대입할 때. 예: print x; (PDF p.87)"""

    def __init__(self, name: str, token: Optional[Token] = None):
        super().__init__(f"Undefined variable '{name}'", token)
        self.name = name


class NotCallableError(ExecutionError):
    """함수가 아닌 값을 호출하려고 할 때. 예: var x = "hello"; x(); (요구사항_정리/function.md)"""

    def __init__(self, token: Optional[Token] = None):
        super().__init__("Can only call functions.", token)


class ArityMismatchError(ExecutionError):
    """선언된 파라미터 수와 호출 인자 수가 다를 때. (요구사항_정리/function.md)"""

    def __init__(self, expected: int, got: int, token: Optional[Token] = None):
        super().__init__(f"Expected {expected} arguments but got {got}.", token)
        self.expected = expected
        self.got = got
