from enum import Enum, auto


class TokenType(Enum):
    # 그룹핑 / 블록 / 구분자 (PDF p.27)
    LEFT_PAREN = auto()
    RIGHT_PAREN = auto()
    LEFT_BRACE = auto()
    RIGHT_BRACE = auto()
    SEMICOLON = auto()

    # 산술 연산자 (PDF p.27)
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()

    # 할당 / 비교 연산자 (PDF p.27)
    EQUAL = auto()
    GREATER = auto()
    LESS = auto()

    # 단항 연산자 (PDF p.36 - Unary Expression: !, +, -)
    BANG = auto()

    # 리터럴 / 식별자 (PDF p.28)
    IDENTIFIER = auto()
    STRING = auto()
    NUMBER = auto()

    # 키워드 (PDF p.28)
    VAR = auto()
    IF = auto()
    ELSE = auto()
    FOR = auto()
    TRUE = auto()
    FALSE = auto()
    AND = auto()
    OR = auto()
    PRINT = auto()

    # 토큰 스트림 끝 (PDF p.28)
    EOF = auto()
