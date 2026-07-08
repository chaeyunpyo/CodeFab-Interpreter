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


# --- 13단계: 정적 배열 인덱스 읽기/쓰기 (요구사항_정리/정적배열.md) ---

def test_step13_array_creation_via_call_expression():
    """소스코드: var arr = Array(3);

    Array(3)은 새 Expr 없이 기존 CallExpr로 파싱된다(요구사항_정리/function.md의
    Command Pattern처럼 "이름을 호출하면 값을 만들어낸다"는 처리를 재사용).
    """
    tokens = [
        Token(TokenType.VAR, "var"),
        Token(TokenType.IDENTIFIER, "arr"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.IDENTIFIER, "Array"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.NUMBER, "3", literal=3.0),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        VarDeclStmt(
            name=Token(TokenType.IDENTIFIER, "arr"),
            initializer=CallExpr(
                callee=VariableExpr(Token(TokenType.IDENTIFIER, "Array")),
                paren=Token(TokenType.LEFT_PAREN, "("),
                arguments=[LiteralExpr(3.0)],
            ),
        )
    ]


def test_step13_index_read():
    """소스코드: print arr[0];"""
    tokens = [
        Token(TokenType.PRINT, "print"),
        Token(TokenType.IDENTIFIER, "arr"),
        Token(TokenType.LEFT_BRACKET, "["),
        Token(TokenType.NUMBER, "0", literal=0.0),
        Token(TokenType.RIGHT_BRACKET, "]"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        PrintStmt(
            expression=IndexGetExpr(
                object=VariableExpr(Token(TokenType.IDENTIFIER, "arr")),
                bracket=Token(TokenType.LEFT_BRACKET, "["),
                index=LiteralExpr(0.0),
            )
        )
    ]


def test_step13_index_write():
    """소스코드: arr[0] = 10;"""
    tokens = [
        Token(TokenType.IDENTIFIER, "arr"),
        Token(TokenType.LEFT_BRACKET, "["),
        Token(TokenType.NUMBER, "0", literal=0.0),
        Token(TokenType.RIGHT_BRACKET, "]"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.NUMBER, "10", literal=10.0),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        ExpressionStmt(
            expression=IndexSetExpr(
                object=VariableExpr(Token(TokenType.IDENTIFIER, "arr")),
                bracket=Token(TokenType.LEFT_BRACKET, "["),
                index=LiteralExpr(0.0),
                value=LiteralExpr(10.0),
            )
        )
    ]


def test_step13_index_with_variable_index_and_nested_access():
    """소스코드: arr[i][j] = arr[i][j] + 1;"""
    tokens = [
        Token(TokenType.IDENTIFIER, "arr"),
        Token(TokenType.LEFT_BRACKET, "["),
        Token(TokenType.IDENTIFIER, "i"),
        Token(TokenType.RIGHT_BRACKET, "]"),
        Token(TokenType.LEFT_BRACKET, "["),
        Token(TokenType.IDENTIFIER, "j"),
        Token(TokenType.RIGHT_BRACKET, "]"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.IDENTIFIER, "arr"),
        Token(TokenType.LEFT_BRACKET, "["),
        Token(TokenType.IDENTIFIER, "i"),
        Token(TokenType.RIGHT_BRACKET, "]"),
        Token(TokenType.LEFT_BRACKET, "["),
        Token(TokenType.IDENTIFIER, "j"),
        Token(TokenType.RIGHT_BRACKET, "]"),
        Token(TokenType.PLUS, "+"),
        Token(TokenType.NUMBER, "1", literal=1.0),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    inner_arr_i = IndexGetExpr(
        object=VariableExpr(Token(TokenType.IDENTIFIER, "arr")),
        bracket=Token(TokenType.LEFT_BRACKET, "["),
        index=VariableExpr(Token(TokenType.IDENTIFIER, "i")),
    )

    assert builder.build() == [
        ExpressionStmt(
            expression=IndexSetExpr(
                object=inner_arr_i,
                bracket=Token(TokenType.LEFT_BRACKET, "["),
                index=VariableExpr(Token(TokenType.IDENTIFIER, "j")),
                value=BinaryExpr(
                    left=IndexGetExpr(
                        object=inner_arr_i,
                        bracket=Token(TokenType.LEFT_BRACKET, "["),
                        index=VariableExpr(Token(TokenType.IDENTIFIER, "j")),
                    ),
                    operator=Token(TokenType.PLUS, "+"),
                    right=LiteralExpr(1.0),
                ),
            )
        )
    ]


def test_step13_call_expression_target_still_raises_invalid_assignment_target_error():
    """소스코드: foo(1) = 5; (IndexGetExpr 대입 허용 추가 후에도 CallExpr은 여전히 대입 불가)"""
    tokens = [
        Token(TokenType.IDENTIFIER, "foo"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.NUMBER, "1", literal=1.0),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.NUMBER, "5", literal=5.0),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    with pytest.raises(InvalidAssignmentTargetError) as excinfo:
        builder.build()

    assert "Invalid assignment target" in str(excinfo.value)


# --- 14단계: 정적 배열 인덱스 파싱 실패 케이스 ---

def test_step14_index_missing_closing_bracket_raises_missing_token_error():
    """소스코드: arr[0  (닫는 ']' 누락)"""
    tokens = [
        Token(TokenType.IDENTIFIER, "arr"),
        Token(TokenType.LEFT_BRACKET, "["),
        Token(TokenType.NUMBER, "0", literal=0.0),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    with pytest.raises(MissingTokenError) as excinfo:
        builder.build()

    assert "Expected ']' after index" in str(excinfo.value)
    assert excinfo.value.token == Token(TokenType.EOF, "")


def test_step14_index_empty_brackets_raises_unexpected_token_error():
    """소스코드: arr[];  (대괄호 안에 인덱스 표현식이 없음)"""
    tokens = [
        Token(TokenType.IDENTIFIER, "arr"),
        Token(TokenType.LEFT_BRACKET, "["),
        Token(TokenType.RIGHT_BRACKET, "]"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    with pytest.raises(UnexpectedTokenError) as excinfo:
        builder.build()

    assert "Unexpected token" in str(excinfo.value)


def test_step14_bracket_cannot_start_a_statement():
    """소스코드: [0];  (대괄호는 primary()로 시작할 수 없어, 색인 대상 없이는 표현식을 시작할 수 없음)"""
    tokens = [
        Token(TokenType.LEFT_BRACKET, "["),
        Token(TokenType.NUMBER, "0", literal=0.0),
        Token(TokenType.RIGHT_BRACKET, "]"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    with pytest.raises(UnexpectedTokenError) as excinfo:
        builder.build()

    assert "Unexpected token" in str(excinfo.value)


def test_step14_index_write_missing_value_raises_unexpected_token_error():
    """소스코드: arr[0] = ;  ('=' 뒤에 대입할 값이 없음)"""
    tokens = [
        Token(TokenType.IDENTIFIER, "arr"),
        Token(TokenType.LEFT_BRACKET, "["),
        Token(TokenType.NUMBER, "0", literal=0.0),
        Token(TokenType.RIGHT_BRACKET, "]"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    with pytest.raises(UnexpectedTokenError) as excinfo:
        builder.build()

    assert "Unexpected token" in str(excinfo.value)


def test_step14_index_write_missing_semicolon_raises_missing_token_error():
    """소스코드: arr[0] = 10  (세미콜론 누락)"""
    tokens = [
        Token(TokenType.IDENTIFIER, "arr"),
        Token(TokenType.LEFT_BRACKET, "["),
        Token(TokenType.NUMBER, "0", literal=0.0),
        Token(TokenType.RIGHT_BRACKET, "]"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.NUMBER, "10", literal=10.0),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    with pytest.raises(MissingTokenError) as excinfo:
        builder.build()

    assert "Expected ';' after expression" in str(excinfo.value)
    assert excinfo.value.token == Token(TokenType.EOF, "")


def test_step14_nested_index_missing_second_closing_bracket_raises_missing_token_error():
    """소스코드: arr[i][j  (두 번째 닫는 ']' 누락)"""
    tokens = [
        Token(TokenType.IDENTIFIER, "arr"),
        Token(TokenType.LEFT_BRACKET, "["),
        Token(TokenType.IDENTIFIER, "i"),
        Token(TokenType.RIGHT_BRACKET, "]"),
        Token(TokenType.LEFT_BRACKET, "["),
        Token(TokenType.IDENTIFIER, "j"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    with pytest.raises(MissingTokenError) as excinfo:
        builder.build()

    assert "Expected ']' after index" in str(excinfo.value)
    assert excinfo.value.token == Token(TokenType.EOF, "")


