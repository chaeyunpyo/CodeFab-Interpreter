# tests/test_tokenizer_steps.py
"""
TDD 연습용 단계별 테스트.
아래로 내려갈수록 난이도가 올라간다.
한 단계씩 Red -> Green을 만들고 나서 다음 단계로 넘어갈 것.

아직 tokenizer.py(=Tokenizer 클래스)가 없으므로 지금은 전부 Red 상태가 정상이다.
src/tokenizer.py 에 Tokenizer를 만들어가면서 하나씩 Green으로 바꾸면 된다.
"""
import pytest
from src.nodes.tokens import Token
from src.nodes.token_type import TokenType
from src.tokenizer import Tokenizer  # 아직 존재하지 않음 (다음 단계에서 구현)


# --- 0단계: Token 객체 자체 (Tokenizer 없이도 통과되어야 하는 기준선) ---

def test_step0_token_equality():
    """Token은 type, lexeme, literal이 같으면 동일한 것으로 취급되어야 한다."""
    a = Token(TokenType.PLUS, "+")
    b = Token(TokenType.PLUS, "+")
    assert a == b


