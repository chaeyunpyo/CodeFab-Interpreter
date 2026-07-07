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
