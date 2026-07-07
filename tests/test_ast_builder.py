import pytest

from src.nodes.tokens import Token
from src.nodes.token_type import TokenType
from src.nodes import *
from src.ast_builder import AstBuilder


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


# --- 8단계: 예외 처리 검증 (세미콜론 누락) ---

def test_step8_syntax_error_missing_semicolon():
    """소스코드: var a = 3  (세미콜론 없음)"""
    tokens = [
        Token(TokenType.VAR, "var"),
        Token(TokenType.IDENTIFIER, "a"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.NUMBER, "3", literal=3.0),
        Token(TokenType.EOF, ""),  # SEMICOLON 누락
    ]
    builder = AstBuilder(tokens)

    with pytest.raises(SyntaxError) as excinfo:
        builder.build()

    assert "Expected ';' after variable declaration" in str(excinfo.value)
