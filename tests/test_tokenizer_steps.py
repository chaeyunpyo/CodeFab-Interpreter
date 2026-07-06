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

# --- 1단계: 아무것도 없는 입력 ---

def test_step1_empty_source_returns_only_eof():
    """빈 문자열을 넣으면 EOF 토큰 하나만 나와야 한다."""
    tokenizer = Tokenizer("")
    tokens = tokenizer.tokenize()

    assert tokens == [Token(TokenType.EOF, "")]

# --- 2단계: 단일 문자 기호 하나 ---

def test_step2_single_left_paren():
    """가장 단순한 토큰 하나: '(' """
    tokenizer = Tokenizer("(")
    tokens = tokenizer.tokenize()

    assert tokens == [
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.EOF, ""),
    ]

def test_step2_single_plus():
    tokenizer = Tokenizer("+")
    tokens = tokenizer.tokenize()

    assert tokens == [
        Token(TokenType.PLUS, "+"),
        Token(TokenType.EOF, ""),
    ]

# --- 3단계: 단일 문자 기호 여러 개 ---

def test_step3_multiple_single_char_tokens():
    tokenizer = Tokenizer("(){}")
    tokens = tokenizer.tokenize()

    assert tokens == [
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.EOF, ""),
    ]

# --- 4단계: 공백 무시 ---

def test_step4_whitespace_between_tokens_is_ignored():
    tokenizer = Tokenizer("( )")
    tokens = tokenizer.tokenize()

    assert tokens == [
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.EOF, ""),
    ]

# --- 5단계: 숫자 리터럴 (literal 필드에 float 값이 채워져야 한다) ---

def test_step5_single_digit_number():
    tokenizer = Tokenizer("7")
    tokens = tokenizer.tokenize()

    assert tokens == [
        Token(TokenType.NUMBER, "7", literal=7.0),
        Token(TokenType.EOF, ""),
    ]


def test_step5_decimal_number():
    tokenizer = Tokenizer("3.14")
    tokens = tokenizer.tokenize()

    assert tokens == [
        Token(TokenType.NUMBER, "3.14", literal=3.14),
        Token(TokenType.EOF, ""),
    ]
