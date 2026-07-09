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


class IndexOutOfRangeError(ExecutionError):
    """배열 크기를 벗어난 인덱스에 접근할 때. 예: arr[5] (배열 크기 3)"""


class InvalidIndexTypeError(ExecutionError):
    """인덱스가 숫자가 아닐 때. 예: arr["hello"]"""


class NotAnArrayError(ExecutionError):
    """배열이 아닌 값에 [] 연산을 사용할 때. 예: var x = 10; x[0]"""


class InvalidArraySizeError(ExecutionError):
    """Array() 생성 시 크기가 숫자가 아니거나 유효하지 않을 때. 예: Array("hi")"""


class NotAnInstanceError(ExecutionError):
    """인스턴스가 아닌 값에 필드 접근(get/set)을 시도할 때. 예: var x = 10; x.field (요구사항_정리/class.md)"""

    def __init__(self, token: Optional[Token] = None):
        super().__init__("필드 접근은 인스턴스에만 사용할 수 있습니다.", token)


class UndefinedPropertyError(ExecutionError):
    """인스턴스에 존재하지 않는 필드/메서드를 읽으려 할 때. 예: print r.power; (요구사항_정리/class.md)"""

    def __init__(self, name: str, token: Optional[Token] = None):
        super().__init__(f"Undefined property '{name}'", token)
        self.name = name


class NotAClassError(ExecutionError):
    """상속 대상(superclass 자리)의 값이 클래스가 아닐 때. 예: var x = 10; Class Robot : x { ... } (요구사항_정리/class.md)"""

    def __init__(self, token: Optional[Token] = None):
        super().__init__("클래스만 상속할 수 있습니다.", token)


class StackOverflowError(ExecutionError):
    """재귀 호출이 파이썬 호출 스택 한도를 넘었을 때. 예: 종료 조건 없이(혹은 아주 깊게) 재귀하는 함수.

    Function.call()이 매 호출마다 파이썬 자체 스택을 소비하므로, 언어
    차원의 재귀 깊이가 파이썬 기본 재귀 한도보다 훨씬 얕은 수준에서도
    RecursionError로 죽을 수 있다. 그대로 두면 ExecutionError 계층에
    속하지 않아 Pipeline/CLI가 못 잡고 그대로 크래시하므로, 여기서
    깔끔한 런타임 오류로 감싼다.
    """

    def __init__(self, token: Optional[Token] = None):
        super().__init__("Recursion too deep.", token)
