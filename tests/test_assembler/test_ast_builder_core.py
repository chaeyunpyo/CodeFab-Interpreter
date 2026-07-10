import pytest

from nodes.tokens import Token
from nodes.token_type import TokenType
from nodes import *
from assembler import (
    AstBuilder,
    InvalidAssignmentTargetError,
    MissingTokenError,
    UnexpectedTokenError,
)


# --- 0단계: 빈 토큰 스트림 (EOF만 있는 경우) ---

def test_step0_only_eof_returns_no_statements():
    """EOF 토큰만 주어지면 statement가 하나도 만들어지지 않아야 한다."""
    tokens = [Token(TokenType.EOF, "")]
    builder = AstBuilder(tokens)

    assert builder.build() == []


# --- 1단계: 리터럴 표현식 하나짜리 문장 ---

def test_step1_single_number_expression_statement():
    """소스코드: 3;"""
    tokens = [
        Token(TokenType.NUMBER, "3", literal=3.0),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        ExpressionStmt(expression=LiteralExpr(3.0))
    ]


# --- 2단계: 변수 선언문 ---

def test_step2_variable_declaration():
    """소스코드: var a = 3;"""
    tokens = [
        Token(TokenType.VAR, "var"),
        Token(TokenType.IDENTIFIER, "a"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.NUMBER, "3", literal=3.0),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        VarDeclStmt(
            name=Token(TokenType.IDENTIFIER, "a"),
            initializer=LiteralExpr(3.0),
        )
    ]


# --- 3단계: 연산자 우선순위 (곱셈이 덧셈보다 먼저 결합) ---

def test_step3_operator_precedence():
    """소스코드: a + b * 3;"""
    tokens = [
        Token(TokenType.IDENTIFIER, "a"),
        Token(TokenType.PLUS, "+"),
        Token(TokenType.IDENTIFIER, "b"),
        Token(TokenType.STAR, "*"),
        Token(TokenType.NUMBER, "3", literal=3.0),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    # a + (b * 3) 형태로 중첩되어야 함
    assert builder.build() == [
        ExpressionStmt(
            expression=BinaryExpr(
                left=VariableExpr(Token(TokenType.IDENTIFIER, "a")),
                operator=Token(TokenType.PLUS, "+"),
                right=BinaryExpr(
                    left=VariableExpr(Token(TokenType.IDENTIFIER, "b")),
                    operator=Token(TokenType.STAR, "*"),
                    right=LiteralExpr(3.0),
                ),
            )
        )
    ]


# --- 3-2단계: 나머지(%) 연산자도 *,/와 같은 우선순위로 파싱된다 (추가) ---

def test_step3_2_percent_operator_has_same_precedence_as_star_and_slash():
    """소스코드: a + b % 3;"""
    tokens = [
        Token(TokenType.IDENTIFIER, "a"),
        Token(TokenType.PLUS, "+"),
        Token(TokenType.IDENTIFIER, "b"),
        Token(TokenType.PERCENT, "%"),
        Token(TokenType.NUMBER, "3", literal=3.0),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    # a + (b % 3) 형태로 중첩되어야 함 (곱셈/나눗셈과 동일한 우선순위)
    assert builder.build() == [
        ExpressionStmt(
            expression=BinaryExpr(
                left=VariableExpr(Token(TokenType.IDENTIFIER, "a")),
                operator=Token(TokenType.PLUS, "+"),
                right=BinaryExpr(
                    left=VariableExpr(Token(TokenType.IDENTIFIER, "b")),
                    operator=Token(TokenType.PERCENT, "%"),
                    right=LiteralExpr(3.0),
                ),
            )
        )
    ]


# --- 3-1단계: 단항 연산자 (PDF p.36: !, +, -) ---

@pytest.mark.parametrize(
    "token_type, lexeme",
    [
        (TokenType.BANG, "!"),
        (TokenType.MINUS, "-"),
        (TokenType.PLUS, "+"),
    ],
)
def test_step3_1_unary_operators_build_unary_expr(token_type, lexeme):
    """소스코드: !3;  /  -3;  /  +3;"""
    tokens = [
        Token(token_type, lexeme),
        Token(TokenType.NUMBER, "3", literal=3.0),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        ExpressionStmt(
            expression=UnaryExpr(
                operator=Token(token_type, lexeme),
                right=LiteralExpr(3.0),
            )
        )
    ]


# --- 4단계: 괄호로 묶인 표현식은 GroupingExpr로 감싸야 한다 ---

def test_step4_parenthesized_expression_is_wrapped_in_grouping():
    """소스코드: (a);"""
    tokens = [
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.IDENTIFIER, "a"),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        ExpressionStmt(
            expression=GroupingExpr(
                expression=VariableExpr(Token(TokenType.IDENTIFIER, "a"))
            )
        )
    ]


# --- 5단계: and / or는 BinaryExpr가 아니라 LogicalExpr로 만들어야 한다 ---

@pytest.mark.parametrize(
    "token_type, lexeme",
    [
        (TokenType.AND, "and"),
        (TokenType.OR, "or"),
    ],
)
def test_step5_logical_operators_build_logical_expr(token_type, lexeme):
    """소스코드: a and b;  /  a or b;"""
    tokens = [
        Token(TokenType.IDENTIFIER, "a"),
        Token(token_type, lexeme),
        Token(TokenType.IDENTIFIER, "b"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        ExpressionStmt(
            expression=LogicalExpr(
                left=VariableExpr(Token(TokenType.IDENTIFIER, "a")),
                operator=Token(token_type, lexeme),
                right=VariableExpr(Token(TokenType.IDENTIFIER, "b")),
            )
        )
    ]


# --- 6단계: print 문 ---

def test_step6_print_statement():
    """소스코드: print a;"""
    tokens = [
        Token(TokenType.PRINT, "print"),
        Token(TokenType.IDENTIFIER, "a"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        PrintStmt(expression=VariableExpr(Token(TokenType.IDENTIFIER, "a")))
    ]


# --- 6-1단계: print_line / print_val 문 (print처럼 괄호 없이 쓰는 문장, 추가) ---

def test_step6_1_print_line_statement():
    """소스코드: print_line;"""
    tokens = [
        Token(TokenType.PRINT_LINE, "print_line"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [PrintLineStmt()]


def test_step6_1_print_val_statement():
    """소스코드: print_val;"""
    tokens = [
        Token(TokenType.PRINT_VAL, "print_val"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [PrintValStmt()]


# --- 7단계: 조건문 및 블록 ---

def test_step7_conditional_and_block():
    """소스코드: if (x > 10) { print x; }"""
    tokens = [
        Token(TokenType.IF, "if"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.IDENTIFIER, "x"),
        Token(TokenType.GREATER, ">"),
        Token(TokenType.NUMBER, "10", literal=10.0),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.PRINT, "print"),
        Token(TokenType.IDENTIFIER, "x"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        IfStmt(
            condition=BinaryExpr(
                left=VariableExpr(Token(TokenType.IDENTIFIER, "x")),
                operator=Token(TokenType.GREATER, ">"),
                right=LiteralExpr(10.0),
            ),
            then_branch=BlockStmt(
                statements=[
                    PrintStmt(expression=VariableExpr(Token(TokenType.IDENTIFIER, "x")))
                ]
            ),
            else_branch=None,
        )
    ]


# --- 7-1단계: 추가 비교 연산자 (==, !=, >=, <=, =<, =>) ---

@pytest.mark.parametrize(
    "token_type, lexeme",
    [
        (TokenType.EQUAL_EQUAL, "=="),
        (TokenType.BANG_EQUAL, "!="),
        (TokenType.GREATER_EQUAL, ">="),
        (TokenType.LESS_EQUAL, "<="),
        (TokenType.EQUAL_LESS, "=<"),
        (TokenType.EQUAL_GREATER, "=>"),
    ],
)
def test_step7_1_extended_comparison_operators_build_binary_expr(token_type, lexeme):
    """소스코드: a == b;  /  a != b;  /  a >= b;  /  a <= b;  /  a =< b;  /  a => b;"""
    tokens = [
        Token(TokenType.IDENTIFIER, "a"),
        Token(token_type, lexeme),
        Token(TokenType.IDENTIFIER, "b"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        ExpressionStmt(
            expression=BinaryExpr(
                left=VariableExpr(Token(TokenType.IDENTIFIER, "a")),
                operator=Token(token_type, lexeme),
                right=VariableExpr(Token(TokenType.IDENTIFIER, "b")),
            )
        )
    ]


# --- 8단계: 예외 처리 검증 (세미콜론 누락, 잘못된 대입 대상, 해석 불가 토큰) ---

def test_step8_missing_token_error_missing_semicolon():
    """소스코드: var a = 3  (세미콜론 없음)"""
    tokens = [
        Token(TokenType.VAR, "var"),
        Token(TokenType.IDENTIFIER, "a"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.NUMBER, "3", literal=3.0),
        Token(TokenType.EOF, ""),  # SEMICOLON 누락
    ]
    builder = AstBuilder(tokens)

    with pytest.raises(MissingTokenError) as excinfo:
        builder.build()

    assert "Expected ';' after variable declaration" in str(excinfo.value)
    assert excinfo.value.token == Token(TokenType.EOF, "")


def test_step8_invalid_assignment_target_error():
    """소스코드: 3 = 5;"""
    tokens = [
        Token(TokenType.NUMBER, "3", literal=3.0),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.NUMBER, "5", literal=5.0),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    with pytest.raises(InvalidAssignmentTargetError) as excinfo:
        builder.build()

    assert "Invalid assignment target" in str(excinfo.value)


def test_step8_unexpected_token_error():
    """소스코드: *3; (이항 연산자 *로는 표현식을 시작할 수 없음)

    SEMICOLON은 향후 빈 문장(empty statement)으로 허용될 수도 있어
    "해석 불가 토큰"의 예시로 부적합하다. STAR는 어떤 문법 규칙으로도
    표현식의 시작이 될 수 없으므로 이 값을 사용한다.
    """
    tokens = [
        Token(TokenType.STAR, "*"),
        Token(TokenType.NUMBER, "3", literal=3.0),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    with pytest.raises(UnexpectedTokenError) as excinfo:
        builder.build()

    assert "Unexpected token" in str(excinfo.value)


