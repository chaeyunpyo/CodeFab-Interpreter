from dataclasses import dataclass
from typing import Any, Optional

from .token_type import TokenType


@dataclass
class Token:
    """부품(Token) 하나를 표현한다. (PDF p.23)

    type: 토큰 종류 (TokenType)
    lexeme: 원본 문자열 그대로 (PDF의 "origin")
    literal: NUMBER/STRING 등에서 실제로 사용할 가공된 값 (예: "37" -> 37.0)
    line: 토큰이 등장한 줄 번호 (1부터 시작, 오류 메시지에 사용)
    """

    type: TokenType
    lexeme: str
    literal: Optional[Any] = None
    line: int = 1
