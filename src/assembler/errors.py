from source_error import SourceError


class AssemblerError(SourceError):
    """Assembler Unit(토큰화 + 파싱) 중 발생하는 오류의 최상위 타입. (PDF p.66)"""

    UNIT = "Assembler"


class TokenizerError(AssemblerError):
    """소스 코드를 Token으로 분해하는 중, 어떤 Token 규칙에도 맞지 않는 문자를 만났을 때."""


class MissingTokenError(AssemblerError):
    """문법 규칙상 반드시 있어야 할 토큰이 없을 때. 예: var a = 3 + ; (우항/세미콜론 누락) (PDF p.66)"""


class UnexpectedTokenError(AssemblerError):
    """어떤 문법 규칙(표현식 시작 등)으로도 해석할 수 없는 토큰을 만났을 때."""


class InvalidAssignmentTargetError(AssemblerError):
    """대입 연산자(=)의 좌변이 변수(VariableExpr)가 아닐 때. 예: 3 = 5;"""


class ExpressionTooDeeplyNestedError(AssemblerError):
    """문장/표현식이 재귀 하강 파서가 감당할 수 없을 만큼 깊게 중첩되었을 때.
    예: 괄호를 극단적으로 깊게 중첩한 식(`((((...1...))))`), 블록을 극단적으로
    깊게 중첩한 코드(`{{{...}}}`).

    ExpressionParser/StatementParser는 중첩 한 단계마다 파이썬 함수 호출을
    여러 겹 소비하므로, 파이썬 기본 재귀 한도(1000)보다 훨씬 얕은 중첩
    수준(중첩 100단계 안팎)에서도 RecursionError로 죽을 수 있다. 그대로
    두면 AssemblerError 계층에 속하지 않아 Pipeline/CLI가 못 잡고 그대로
    크래시하므로, AstBuilder.build()에서 이를 잡아 여기로 감싼다
    (Executor의 StackOverflowError와 같은 목적, 다른 Unit).
    """

    def __init__(self, token=None):
        super().__init__("Expression or block nested too deeply.", token)
