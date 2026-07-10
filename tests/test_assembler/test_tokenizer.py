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


# --- 문자열 리터럴 미종료/줄바꿈 처리 ---


def test_unterminated_string_raises_tokenizer_error():
    """닫는 "를 못 찾고 EOF에 도달하면, 잘못된 값을 조용히 만들지 말고 오류를 내야 한다."""
    tokenizer = Tokenizer('"abc')

    with pytest.raises(TokenizerError):
        tokenizer.tokenize()


def test_string_spanning_multiple_lines_advances_line_counter():
    """문자열 안에 있는 개행도 메인 루프와 동일하게 line을 증가시켜야 한다."""
    tokenizer = Tokenizer('"line1\nline2"\nvar a = 1;')
    tokens = tokenizer.tokenize()

    assert tokens == [
        Token(TokenType.STRING, '"line1\nline2"', literal="line1\nline2", line=1),
        Token(TokenType.VAR, "var", line=3),
        Token(TokenType.IDENTIFIER, "a", line=3),
        Token(TokenType.EQUAL, "=", line=3),
        Token(TokenType.NUMBER, "1", literal=1.0, line=3),
        Token(TokenType.SEMICOLON, ";", line=3),
        Token(TokenType.EOF, "", line=3),
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


# --- 22단계: 추가 - 콤마 (함수 파라미터/인자 구분, function.md 참고) ---

def test_step22_comma_token():
    """Func add(a, b) { ... }, add(1, 2) 처럼 파라미터/인자를 구분하는 ',' 토큰."""
    tokenizer = Tokenizer(",")
    tokens = tokenizer.tokenize()

    assert tokens == [
        Token(TokenType.COMMA, ","),
        Token(TokenType.EOF, ""),
    ]


def test_step22_function_call_argument_list_tokenizes_with_commas():
    """add(1, 2)처럼 콤마로 구분된 인자 목록이 올바르게 토큰화되어야 한다."""
    tokenizer = Tokenizer("add(1, 2);")
    tokens = tokenizer.tokenize()

    assert tokens == [
        Token(TokenType.IDENTIFIER, "add"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.NUMBER, "1", literal=1.0),
        Token(TokenType.COMMA, ","),
        Token(TokenType.NUMBER, "2", literal=2.0),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]

# --- 23단계: 추가 - 점/콜론 (필드·메서드 접근, 클래스 상속 선언, class.md 참고) ---

def test_step23_dot_token():
    """r.speed, this.position, super.move() 처럼 필드/메서드 접근에 쓰이는 '.' 토큰."""
    tokenizer = Tokenizer(".")
    tokens = tokenizer.tokenize()

    assert tokens == [
        Token(TokenType.DOT, "."),
        Token(TokenType.EOF, ""),
    ]


def test_step23_colon_token():
    """Class SpeedRobot : Robot { ... } 처럼 상속 선언에 쓰이는 ':' 토큰."""
    tokenizer = Tokenizer(":")
    tokens = tokenizer.tokenize()

    assert tokens == [
        Token(TokenType.COLON, ":"),
        Token(TokenType.EOF, ""),
    ]


def test_step23_field_access_tokenizes_with_dot():
    """r.speed = 10; 처럼 점으로 이어진 필드 접근이 올바르게 토큰화되어야 한다."""
    tokenizer = Tokenizer("r.speed = 10;")
    tokens = tokenizer.tokenize()

    assert tokens == [
        Token(TokenType.IDENTIFIER, "r"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "speed"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.NUMBER, "10", literal=10.0),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]

# --- 24단계: 추가 - import 문법 (import.md 참고, 새 토큰 없이 기존 토큰만으로 구성됨) ---

def test_step24_import_statement_tokenizes_with_existing_tokens():
    """import "sum.txt" alias sum; 은 새 토큰 없이 IMPORT/STRING/ALIAS/IDENTIFIER/SEMICOLON
    조합만으로 이미 올바르게 토큰화되어야 한다."""
    tokenizer = Tokenizer('import "sum.txt" alias sum;')
    tokens = tokenizer.tokenize()

    assert tokens == [
        Token(TokenType.IMPORT, "import"),
        Token(TokenType.STRING, '"sum.txt"', literal="sum.txt"),
        Token(TokenType.ALIAS, "alias"),
        Token(TokenType.IDENTIFIER, "sum"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]

# --- 25단계: 추가 - 정적 배열 문법 (정적배열.md 참고, 새 토큰 없이 기존 토큰만으로 구성됨) ---
# 문서상 필요한 Token은 LEFT_BRACKET/RIGHT_BRACKET 2개뿐이며 이미 20단계에서 추가됨.
# Array는 예약어가 아니라 IDENTIFIER를 함수처럼 호출하는 형태(Command Pattern)라 별도 토큰 불필요.

@pytest.mark.parametrize(
    "source, expected",
    [
        (
            "var arr = Array(3);",
            [
                Token(TokenType.VAR, "var"),
                Token(TokenType.IDENTIFIER, "arr"),
                Token(TokenType.EQUAL, "="),
                Token(TokenType.IDENTIFIER, "Array"),
                Token(TokenType.LEFT_PAREN, "("),
                Token(TokenType.NUMBER, "3", literal=3.0),
                Token(TokenType.RIGHT_PAREN, ")"),
                Token(TokenType.SEMICOLON, ";"),
                Token(TokenType.EOF, ""),
            ],
        ),
        (
            "arr[0] = 10;",
            [
                Token(TokenType.IDENTIFIER, "arr"),
                Token(TokenType.LEFT_BRACKET, "["),
                Token(TokenType.NUMBER, "0", literal=0.0),
                Token(TokenType.RIGHT_BRACKET, "]"),
                Token(TokenType.EQUAL, "="),
                Token(TokenType.NUMBER, "10", literal=10.0),
                Token(TokenType.SEMICOLON, ";"),
                Token(TokenType.EOF, ""),
            ],
        ),
    ],
)
def test_step25_static_array_syntax_tokenizes_with_existing_tokens(source, expected):
    """Array(n) 생성과 arr[i] 인덱스 읽기/쓰기가 기존 토큰 조합만으로 올바르게 토큰화되어야 한다."""
    tokenizer = Tokenizer(source)
    tokens = tokenizer.tokenize()

    assert tokens == expected


# --- 26단계: 예약어는 대소문자를 구분한다 (요구사항_정리/TokenType.md 참고) ---

@pytest.mark.parametrize(
    "source",
    [
        "this",   # This만 유효, this는 예약어가 아니다
        "super",  # Super만 유효, super는 예약어가 아니다
        "True",   # true만 유효, True는 예약어가 아니다
        "False",  # false만 유효, False는 예약어가 아니다
    ],
)
def test_step26_keywords_are_case_sensitive(source):
    """요구사항_정리/TokenType.md에 나열된 표기(This/Super/true/false)만
    예약어로 인식하고, 대소문자가 다른 변형은 IDENTIFIER로 취급해야 한다.
    """
    tokenizer = Tokenizer(source)
    tokens = tokenizer.tokenize()

    assert tokens == [
        Token(TokenType.IDENTIFIER, source),
        Token(TokenType.EOF, ""),
    ]


# --- 27단계: 추가 - 나머지(모듈로) 연산자 ---

def test_step27_percent_operator():
    """a % b 처럼 나머지를 구하는 데 쓰이는 '%' 단일 문자 토큰."""
    tokenizer = Tokenizer("%")
    tokens = tokenizer.tokenize()

    assert tokens == [
        Token(TokenType.PERCENT, "%"),
        Token(TokenType.EOF, ""),
    ]


# --- 28단계: 추가 - print_line / print_val (print처럼 괄호 없이 쓰는 문장 키워드) ---

@pytest.mark.parametrize(
    "source, expected_type",
    [
        ("print_line", TokenType.PRINT_LINE),
        ("print_val", TokenType.PRINT_VAL),
    ],
)
def test_step28_print_line_and_print_val_keywords(source, expected_type):
    """print_line/print_val은 IDENTIFIER가 아니라 전용 키워드 타입이어야 한다."""
    tokenizer = Tokenizer(source)
    tokens = tokenizer.tokenize()

    assert tokens == [
        Token(expected_type, source),
        Token(TokenType.EOF, ""),
    ]
