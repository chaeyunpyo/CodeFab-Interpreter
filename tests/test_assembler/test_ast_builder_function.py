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


# --- 9단계: 함수 선언 (요구사항_정리/function.md) ---

def test_step9_function_declaration_no_params():
    """소스코드: Func greet() { print 1; }"""
    tokens = [
        Token(TokenType.FUNC, "Func"),
        Token(TokenType.IDENTIFIER, "greet"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.PRINT, "print"),
        Token(TokenType.NUMBER, "1", literal=1.0),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        FunctionStmt(
            name=Token(TokenType.IDENTIFIER, "greet"),
            params=[],
            body=[PrintStmt(expression=LiteralExpr(1.0))],
        )
    ]


def test_step9_function_declaration_with_params():
    """소스코드: Func add(a, b) { return a + b; }"""
    tokens = [
        Token(TokenType.FUNC, "Func"),
        Token(TokenType.IDENTIFIER, "add"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.IDENTIFIER, "a"),
        Token(TokenType.COMMA, ","),
        Token(TokenType.IDENTIFIER, "b"),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.RETURN, "return"),
        Token(TokenType.IDENTIFIER, "a"),
        Token(TokenType.PLUS, "+"),
        Token(TokenType.IDENTIFIER, "b"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        FunctionStmt(
            name=Token(TokenType.IDENTIFIER, "add"),
            params=[Token(TokenType.IDENTIFIER, "a"), Token(TokenType.IDENTIFIER, "b")],
            body=[
                ReturnStmt(
                    keyword=Token(TokenType.RETURN, "return"),
                    value=BinaryExpr(
                        left=VariableExpr(Token(TokenType.IDENTIFIER, "a")),
                        operator=Token(TokenType.PLUS, "+"),
                        right=VariableExpr(Token(TokenType.IDENTIFIER, "b")),
                    ),
                )
            ],
        )
    ]


# --- 10단계: return문 (값 없는 return) ---

def test_step10_return_without_value():
    """소스코드: return;"""
    tokens = [
        Token(TokenType.RETURN, "return"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        ReturnStmt(keyword=Token(TokenType.RETURN, "return"), value=None)
    ]


# --- 11단계: 함수 호출 표현식 (요구사항_정리/function.md) ---

def test_step11_call_expression_no_arguments():
    """소스코드: greet();"""
    tokens = [
        Token(TokenType.IDENTIFIER, "greet"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        ExpressionStmt(
            expression=CallExpr(
                callee=VariableExpr(Token(TokenType.IDENTIFIER, "greet")),
                paren=Token(TokenType.LEFT_PAREN, "("),
                arguments=[],
            )
        )
    ]


def test_step11_call_expression_with_arguments():
    """소스코드: ret = add(1, 2);"""
    tokens = [
        Token(TokenType.IDENTIFIER, "ret"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.IDENTIFIER, "add"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.NUMBER, "1", literal=1.0),
        Token(TokenType.COMMA, ","),
        Token(TokenType.NUMBER, "2", literal=2.0),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        ExpressionStmt(
            expression=AssignExpr(
                name=Token(TokenType.IDENTIFIER, "ret"),
                value=CallExpr(
                    callee=VariableExpr(Token(TokenType.IDENTIFIER, "add")),
                    paren=Token(TokenType.LEFT_PAREN, "("),
                    arguments=[LiteralExpr(1.0), LiteralExpr(2.0)],
                ),
            )
        )
    ]


def test_step11_recursive_call_in_condition():
    """소스코드: Func fact(n) { if (n <= 1) return 1; return n * fact(n - 1); }"""
    tokens = [
        Token(TokenType.FUNC, "Func"),
        Token(TokenType.IDENTIFIER, "fact"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.IDENTIFIER, "n"),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.IF, "if"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.IDENTIFIER, "n"),
        Token(TokenType.LESS_EQUAL, "<="),
        Token(TokenType.NUMBER, "1", literal=1.0),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.RETURN, "return"),
        Token(TokenType.NUMBER, "1", literal=1.0),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RETURN, "return"),
        Token(TokenType.IDENTIFIER, "n"),
        Token(TokenType.STAR, "*"),
        Token(TokenType.IDENTIFIER, "fact"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.IDENTIFIER, "n"),
        Token(TokenType.MINUS, "-"),
        Token(TokenType.NUMBER, "1", literal=1.0),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        FunctionStmt(
            name=Token(TokenType.IDENTIFIER, "fact"),
            params=[Token(TokenType.IDENTIFIER, "n")],
            body=[
                IfStmt(
                    condition=BinaryExpr(
                        left=VariableExpr(Token(TokenType.IDENTIFIER, "n")),
                        operator=Token(TokenType.LESS_EQUAL, "<="),
                        right=LiteralExpr(1.0),
                    ),
                    then_branch=ReturnStmt(
                        keyword=Token(TokenType.RETURN, "return"),
                        value=LiteralExpr(1.0),
                    ),
                    else_branch=None,
                ),
                ReturnStmt(
                    keyword=Token(TokenType.RETURN, "return"),
                    value=BinaryExpr(
                        left=VariableExpr(Token(TokenType.IDENTIFIER, "n")),
                        operator=Token(TokenType.STAR, "*"),
                        right=CallExpr(
                            callee=VariableExpr(Token(TokenType.IDENTIFIER, "fact")),
                            paren=Token(TokenType.LEFT_PAREN, "("),
                            arguments=[
                                BinaryExpr(
                                    left=VariableExpr(Token(TokenType.IDENTIFIER, "n")),
                                    operator=Token(TokenType.MINUS, "-"),
                                    right=LiteralExpr(1.0),
                                )
                            ],
                        ),
                    ),
                ),
            ],
        )
    ]


# --- 12단계: return문 뒤 세미콜론 누락 시 오류 ---

def test_step12_return_missing_semicolon_raises_missing_token_error():
    """소스코드: return 1  (세미콜론 없음)"""
    tokens = [
        Token(TokenType.RETURN, "return"),
        Token(TokenType.NUMBER, "1", literal=1.0),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    with pytest.raises(MissingTokenError) as excinfo:
        builder.build()

    assert "Expected ';' after return value" in str(excinfo.value)


