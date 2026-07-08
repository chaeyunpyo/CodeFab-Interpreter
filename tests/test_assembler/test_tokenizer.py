import pytest
from nodes.tokens import Token
from nodes.token_type import TokenType
from assembler import Tokenizer, TokenizerError


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

# --- 6단계: 식별자 ---

def test_step6_single_identifier():
    tokenizer = Tokenizer("num")
    tokens = tokenizer.tokenize()

    assert tokens == [
        Token(TokenType.IDENTIFIER, "num"),
        Token(TokenType.EOF, ""),
    ]

# --- 7단계: 키워드 (예약어는 IDENTIFIER가 아니라 전용 타입이어야 한다) ---

def test_step7_keyword_var():
    tokenizer = Tokenizer("var")
    tokens = tokenizer.tokenize()

    assert tokens == [
        Token(TokenType.VAR, "var"),
        Token(TokenType.EOF, ""),
    ]

# --- 8단계: 문자열 리터럴 ---

def test_step8_string_literal():
    tokenizer = Tokenizer('"hi"')
    tokens = tokenizer.tokenize()

    assert tokens == [
        Token(TokenType.STRING, '"hi"', literal="hi"),
        Token(TokenType.EOF, ""),
    ]

# --- 9단계: 여러 종류를 합친 최소 문장 ---

def test_step9_minimal_statement():
    """var a = 3; 정도의 조합"""
    tokenizer = Tokenizer("var a = 3;")
    tokens = tokenizer.tokenize()

    assert tokens == [
        Token(TokenType.VAR, "var"),
        Token(TokenType.IDENTIFIER, "a"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.NUMBER, "3", literal=3.0),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]

# --- 10단계: 강사님 git page 참고

@pytest.mark.parametrize(
    "source, expected_type",
    [
        ("-", TokenType.MINUS),   # -3 + 2, a - b
        ("*", TokenType.STAR),    # 2 * 3
        ("/", TokenType.SLASH),   # 8 / 2
        ("<", TokenType.LESS),    # 1 < 2
        (">", TokenType.GREATER),  # 3 > 5
    ],
)
def test_step10_extra_single_char_operators(source, expected_type):
    """산술/비교 연산자 문서 예시에 등장하는 단일 문자 기호들."""
    tokenizer = Tokenizer(source)
    tokens = tokenizer.tokenize()

    assert tokens == [
        Token(expected_type, source),
        Token(TokenType.EOF, ""),
    ]

# --- 11단계: 강사님 git page 참고

@pytest.mark.parametrize(
    "source, expected_type",
    [
        ("print", TokenType.PRINT),  # print 1 + 2 * 3;
        ("if", TokenType.IF),        # if (true) print "bbq";
        ("else", TokenType.ELSE),    # if (false) print "no"; else print "kfc";
        ("for", TokenType.FOR),      # for (var j = 0; j < 3; j = j + 1) { ... }
        ("true", TokenType.TRUE),    # print true;
        ("false", TokenType.FALSE),  # print false;
    ],
)
def test_step11_extra_keywords(source, expected_type):
    """문서 예시 스크립트에서 쓰이는 예약어들 (IDENTIFIER가 아닌 전용 타입이어야 한다)."""
    tokenizer = Tokenizer(source)
    tokens = tokenizer.tokenize()

    assert tokens == [
        Token(expected_type, source),
        Token(TokenType.EOF, ""),
    ]

# --- 12단계: 강사님 git page 참고
def test_step12_line_comment_is_ignored():
    """문서의 모든 예시가 `// ...` 한 줄 주석을 사용하므로, 주석은 토큰을 만들지 않고 무시되어야 한다."""
    tokenizer = Tokenizer('// expect: 7\nprint 1;')
    tokens = tokenizer.tokenize()

    assert tokens == [
        Token(TokenType.PRINT, "print", line=2),
        Token(TokenType.NUMBER, "1", literal=1.0, line=2),
        Token(TokenType.SEMICOLON, ";", line=2),
        Token(TokenType.EOF, "", line=2),
    ]

# --- 13단계: 2문자 비교 연산자 (추가분: ==, >=, <=) ---

@pytest.mark.parametrize(
    "source, expected_type",
    [
        ("==", TokenType.EQUAL_EQUAL),   # a == b
        (">=", TokenType.GREATER_EQUAL),  # a >= b
        ("<=", TokenType.LESS_EQUAL),    # a <= b
    ],
)
def test_step13_two_char_comparison_operators(source, expected_type):
    """=, >, < 뒤에 =가 붙으면 단일 문자가 아니라 2문자 비교 연산자여야 한다."""
    tokenizer = Tokenizer(source)
    tokens = tokenizer.tokenize()

    assert tokens == [
        Token(expected_type, source),
        Token(TokenType.EOF, ""),
    ]

# --- 14단계: 2문자 비교 연산자 (추가분: =<, => — TokenType.md에는 아직 미반영) ---

@pytest.mark.parametrize(
    "source, expected_type",
    [
        ("=<", TokenType.EQUAL_LESS),     # a =< b
        ("=>", TokenType.EQUAL_GREATER),  # a => b
    ],
)
def test_step14_equal_prefixed_comparison_operators(source, expected_type):
    """= 뒤에 <, >가 붙으면 단일 문자가 아니라 2문자 비교 연산자여야 한다."""
    tokenizer = Tokenizer(source)
    tokens = tokenizer.tokenize()

    assert tokens == [
        Token(expected_type, source),
        Token(TokenType.EOF, ""),
    ]

# --- 15단계: 논리 연산자 키워드 (and, or) ---

@pytest.mark.parametrize(
    "source, expected_type",
    [
        ("and", TokenType.AND),  # true and false
        ("or", TokenType.OR),    # true or false
    ],
)
def test_step15_logical_keywords(source, expected_type):
    """and/or는 IDENTIFIER가 아니라 전용 타입이어야 한다."""
    tokenizer = Tokenizer(source)
    tokens = tokenizer.tokenize()

    assert tokens == [
        Token(expected_type, source),
        Token(TokenType.EOF, ""),
    ]

# --- 16단계: 단항 부정 연산자 (!) ---

def test_step16_single_bang():
    """!true 처럼 논리 부정(NOT)에 쓰이는 '!' 하나."""
    tokenizer = Tokenizer("!")
    tokens = tokenizer.tokenize()

    assert tokens == [
        Token(TokenType.BANG, "!"),
        Token(TokenType.EOF, ""),
    ]

# --- 17단계: 부정 비교 연산자 (!=) ---

def test_step17_bang_equal():
    """! 뒤에 =가 붙으면 단일 문자가 아니라 2문자 비교 연산자(같지 않음)여야 한다."""
    tokenizer = Tokenizer("!=")
    tokens = tokenizer.tokenize()

    assert tokens == [
        Token(TokenType.BANG_EQUAL, "!="),
        Token(TokenType.EOF, ""),
    ]

# --- 18단계: 등록되지 않은 문자 (KeyError가 아니라 명확한 에러여야 한다) ---

def test_step18_unexpected_character_raises_tokenizer_error():
    """@ 같이 어떤 토큰에도 매핑되지 않는 문자는 KeyError가 아니라 TokenizerError를 내야 한다."""
    tokenizer = Tokenizer("@")

    with pytest.raises(TokenizerError):
        tokenizer.tokenize()

# --- 19단계: 줄 번호 추적 (Checker/Executor 에러 메시지가 줄 번호를 필요로 함) ---

def test_step19_tracks_line_numbers_across_newlines():
    """개행(\\n)을 지날 때마다 이후 토큰들의 line이 증가해야 한다."""
    tokenizer = Tokenizer("var a = 1;\nvar b = 2;")
    tokens = tokenizer.tokenize()

    assert tokens == [
        Token(TokenType.VAR, "var", line=1),
        Token(TokenType.IDENTIFIER, "a", line=1),
        Token(TokenType.EQUAL, "=", line=1),
        Token(TokenType.NUMBER, "1", literal=1.0, line=1),
        Token(TokenType.SEMICOLON, ";", line=1),
        Token(TokenType.VAR, "var", line=2),
        Token(TokenType.IDENTIFIER, "b", line=2),
        Token(TokenType.EQUAL, "=", line=2),
        Token(TokenType.NUMBER, "2", literal=2.0, line=2),
        Token(TokenType.SEMICOLON, ";", line=2),
        Token(TokenType.EOF, "", line=2),
    ]

# --- 20단계: 추가 - 대괄호 (정적 배열 인덱싱) ---

@pytest.mark.parametrize(
    "source, expected_type",
    [
        ("[", TokenType.LEFT_BRACKET),   # arr[0]
        ("]", TokenType.RIGHT_BRACKET),  # arr[0]
    ],
)
def test_step20_array_bracket_tokens(source, expected_type):
    """arr[i] 인덱싱 문법에 쓰일 [ / ] 단일 문자 토큰."""
    tokenizer = Tokenizer(source)
    tokens = tokenizer.tokenize()

    assert tokens == [
        Token(expected_type, source),
        Token(TokenType.EOF, ""),
    ]

# --- 21단계: 추가 - 함수/클래스/import 키워드 ---

@pytest.mark.parametrize(
    "source, expected_type",
    [
        ("Func", TokenType.FUNC),              # Func add(a, b) { ... }
        ("Class", TokenType.CLASS),            # Class Robot { ... }
        ("return", TokenType.RETURN),          # return a + b;
        ("This", TokenType.THIS),              # This.position = ...
        ("Super", TokenType.SUPER),            # Super.move(dist);
        ("instanceof", TokenType.INSTANCEOF),  # w instanceof SpeedRobot
        ("import", TokenType.IMPORT),          # import "sum.txt" alias sum;
        ("alias", TokenType.ALIAS),            # import "sum.txt" alias sum;
    ],
)
def test_step21_added_keywords(source, expected_type):
    """추가되는 함수/클래스/import 관련 예약어들 (IDENTIFIER가 아닌 전용 타입이어야 한다)."""
    tokenizer = Tokenizer(source)
    tokens = tokenizer.tokenize()

    assert tokens == [
        Token(expected_type, source),
        Token(TokenType.EOF, ""),
    ]
