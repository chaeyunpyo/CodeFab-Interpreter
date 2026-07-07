from nodes.token_type import TokenType
from nodes.tokens import Token


def tok(token_type: TokenType, lexeme: str) -> Token:
    """이름/연산자 토큰을 짧게 만들기 위한 헬퍼. literal/line은 테스트에 불필요."""
    return Token(token_type, lexeme)
