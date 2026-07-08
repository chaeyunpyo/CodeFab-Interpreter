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


# --- 15단계: 필드 접근(get/set) / this / super 파싱 (요구사항_정리/class.md) ---
#
# Class 선언문(ClassStmt)/상속(:)/instanceof 파싱은 이 담당 범위가 아니므로
# 여기서는 필드 접근(.), this, super 파싱만 다룬다. object에는 아직
# ClassStmt가 없어도 파싱을 검증할 수 있는 임의의 VariableExpr을 사용한다.

def test_step15_field_read():
    """소스코드: print r.speed;"""
    tokens = [
        Token(TokenType.PRINT, "print"),
        Token(TokenType.IDENTIFIER, "r"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "speed"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        PrintStmt(
            expression=FieldGetExpr(
                object=VariableExpr(Token(TokenType.IDENTIFIER, "r")),
                name=Token(TokenType.IDENTIFIER, "speed"),
            )
        )
    ]


def test_step15_field_write():
    """소스코드: r.speed = 10;"""
    tokens = [
        Token(TokenType.IDENTIFIER, "r"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "speed"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.NUMBER, "10", literal=10.0),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        ExpressionStmt(
            expression=FieldSetExpr(
                object=VariableExpr(Token(TokenType.IDENTIFIER, "r")),
                name=Token(TokenType.IDENTIFIER, "speed"),
                value=LiteralExpr(10.0),
            )
        )
    ]


def test_step15_field_update_reads_and_writes_same_field():
    """소스코드: r.speed = r.speed + 5;"""
    tokens = [
        Token(TokenType.IDENTIFIER, "r"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "speed"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.IDENTIFIER, "r"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "speed"),
        Token(TokenType.PLUS, "+"),
        Token(TokenType.NUMBER, "5", literal=5.0),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        ExpressionStmt(
            expression=FieldSetExpr(
                object=VariableExpr(Token(TokenType.IDENTIFIER, "r")),
                name=Token(TokenType.IDENTIFIER, "speed"),
                value=BinaryExpr(
                    left=FieldGetExpr(
                        object=VariableExpr(Token(TokenType.IDENTIFIER, "r")),
                        name=Token(TokenType.IDENTIFIER, "speed"),
                    ),
                    operator=Token(TokenType.PLUS, "+"),
                    right=LiteralExpr(5.0),
                ),
            )
        )
    ]


def test_step15_method_call_on_field():
    """소스코드: r.move(5);"""
    tokens = [
        Token(TokenType.IDENTIFIER, "r"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "move"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.NUMBER, "5", literal=5.0),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        ExpressionStmt(
            expression=CallExpr(
                callee=FieldGetExpr(
                    object=VariableExpr(Token(TokenType.IDENTIFIER, "r")),
                    name=Token(TokenType.IDENTIFIER, "move"),
                ),
                paren=Token(TokenType.LEFT_PAREN, "("),
                arguments=[LiteralExpr(5.0)],
            )
        )
    ]


def test_step15_this_field_access_and_assignment():
    """소스코드: this.position = this.position + dist;"""
    tokens = [
        Token(TokenType.THIS, "this"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "position"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.THIS, "this"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "position"),
        Token(TokenType.PLUS, "+"),
        Token(TokenType.IDENTIFIER, "dist"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        ExpressionStmt(
            expression=FieldSetExpr(
                object=ThisExpr(keyword=Token(TokenType.THIS, "this")),
                name=Token(TokenType.IDENTIFIER, "position"),
                value=BinaryExpr(
                    left=FieldGetExpr(
                        object=ThisExpr(keyword=Token(TokenType.THIS, "this")),
                        name=Token(TokenType.IDENTIFIER, "position"),
                    ),
                    operator=Token(TokenType.PLUS, "+"),
                    right=VariableExpr(Token(TokenType.IDENTIFIER, "dist")),
                ),
            )
        )
    ]


def test_step15_this_method_call():
    """소스코드: this.report();"""
    tokens = [
        Token(TokenType.THIS, "this"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "report"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        ExpressionStmt(
            expression=CallExpr(
                callee=FieldGetExpr(
                    object=ThisExpr(keyword=Token(TokenType.THIS, "this")),
                    name=Token(TokenType.IDENTIFIER, "report"),
                ),
                paren=Token(TokenType.LEFT_PAREN, "("),
                arguments=[],
            )
        )
    ]


def test_step15_super_method_call():
    """소스코드: super.move(dist);"""
    tokens = [
        Token(TokenType.SUPER, "super"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "move"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.IDENTIFIER, "dist"),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        ExpressionStmt(
            expression=CallExpr(
                callee=SuperExpr(
                    keyword=Token(TokenType.SUPER, "super"),
                    method=Token(TokenType.IDENTIFIER, "move"),
                ),
                paren=Token(TokenType.LEFT_PAREN, "("),
                arguments=[VariableExpr(Token(TokenType.IDENTIFIER, "dist"))],
            )
        )
    ]


def test_step15_field_read_missing_property_name_raises_missing_token_error():
    """소스코드: r.;  ('.' 뒤에 필드 이름이 없음)"""
    tokens = [
        Token(TokenType.IDENTIFIER, "r"),
        Token(TokenType.DOT, "."),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    with pytest.raises(MissingTokenError) as excinfo:
        builder.build()

    assert "Expected property name after '.'" in str(excinfo.value)
    assert excinfo.value.token == Token(TokenType.SEMICOLON, ";")


def test_step15_super_without_dot_raises_missing_token_error():
    """소스코드: super move(); ('.' 없이 super 뒤에 바로 식별자가 옴)"""
    tokens = [
        Token(TokenType.SUPER, "super"),
        Token(TokenType.IDENTIFIER, "move"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    with pytest.raises(MissingTokenError) as excinfo:
        builder.build()

    assert "Expected '.' after 'super'" in str(excinfo.value)


def test_step15_super_without_method_name_raises_missing_token_error():
    """소스코드: super.();  ('.' 뒤에 메서드 이름이 없음)"""
    tokens = [
        Token(TokenType.SUPER, "super"),
        Token(TokenType.DOT, "."),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    with pytest.raises(MissingTokenError) as excinfo:
        builder.build()

    assert "Expected superclass method name" in str(excinfo.value)


def test_step15_call_target_still_invalid_assignment_target_with_this_present():
    """소스코드: this.report() = 5; (메서드 호출 결과에는 여전히 대입 불가)"""
    tokens = [
        Token(TokenType.THIS, "this"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "report"),
        Token(TokenType.LEFT_PAREN, "("),
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


# --- 16단계: 필드 접근 / this / super 연쇄 및 추가 실패 케이스 ---

def test_step16_nested_field_read():
    """소스코드: print a.b.c;"""
    tokens = [
        Token(TokenType.PRINT, "print"),
        Token(TokenType.IDENTIFIER, "a"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "b"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "c"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        PrintStmt(
            expression=FieldGetExpr(
                object=FieldGetExpr(
                    object=VariableExpr(Token(TokenType.IDENTIFIER, "a")),
                    name=Token(TokenType.IDENTIFIER, "b"),
                ),
                name=Token(TokenType.IDENTIFIER, "c"),
            )
        )
    ]


def test_step16_nested_field_write():
    """소스코드: a.b.c = 5;"""
    tokens = [
        Token(TokenType.IDENTIFIER, "a"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "b"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "c"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.NUMBER, "5", literal=5.0),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        ExpressionStmt(
            expression=FieldSetExpr(
                object=FieldGetExpr(
                    object=VariableExpr(Token(TokenType.IDENTIFIER, "a")),
                    name=Token(TokenType.IDENTIFIER, "b"),
                ),
                name=Token(TokenType.IDENTIFIER, "c"),
                value=LiteralExpr(5.0),
            )
        )
    ]


def test_step16_call_result_then_field_access():
    """소스코드: print a().b;  (호출 결과에 바로 필드 접근)"""
    tokens = [
        Token(TokenType.PRINT, "print"),
        Token(TokenType.IDENTIFIER, "a"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "b"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        PrintStmt(
            expression=FieldGetExpr(
                object=CallExpr(
                    callee=VariableExpr(Token(TokenType.IDENTIFIER, "a")),
                    paren=Token(TokenType.LEFT_PAREN, "("),
                    arguments=[],
                ),
                name=Token(TokenType.IDENTIFIER, "b"),
            )
        )
    ]


def test_step16_index_result_then_field_access():
    """소스코드: print arr[0].speed;  (인덱스 접근 결과에 필드 접근)"""
    tokens = [
        Token(TokenType.PRINT, "print"),
        Token(TokenType.IDENTIFIER, "arr"),
        Token(TokenType.LEFT_BRACKET, "["),
        Token(TokenType.NUMBER, "0", literal=0.0),
        Token(TokenType.RIGHT_BRACKET, "]"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "speed"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        PrintStmt(
            expression=FieldGetExpr(
                object=IndexGetExpr(
                    object=VariableExpr(Token(TokenType.IDENTIFIER, "arr")),
                    bracket=Token(TokenType.LEFT_BRACKET, "["),
                    index=LiteralExpr(0.0),
                ),
                name=Token(TokenType.IDENTIFIER, "speed"),
            )
        )
    ]


def test_step16_field_result_then_index_access():
    """소스코드: print obj.arr[0];  (필드 접근 결과에 인덱스 접근)"""
    tokens = [
        Token(TokenType.PRINT, "print"),
        Token(TokenType.IDENTIFIER, "obj"),
        Token(TokenType.DOT, "."),
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
                object=FieldGetExpr(
                    object=VariableExpr(Token(TokenType.IDENTIFIER, "obj")),
                    name=Token(TokenType.IDENTIFIER, "arr"),
                ),
                bracket=Token(TokenType.LEFT_BRACKET, "["),
                index=LiteralExpr(0.0),
            )
        )
    ]


def test_step16_this_as_standalone_expression():
    """소스코드: this;  (필드 접근 없이 this 자체를 값으로 사용)

    클래스 외부 this 사용은 Checker의 정적 오류 검사 몫이라 AstBuilder는
    구조만 보고 그대로 ThisExpr로 파싱해야 한다.
    """
    tokens = [
        Token(TokenType.THIS, "this"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        ExpressionStmt(expression=ThisExpr(keyword=Token(TokenType.THIS, "this")))
    ]


def test_step16_assignment_target_with_call_in_the_middle_is_still_valid():
    """소스코드: a.b().c = 5;  (대입 대상 체인 중간에 호출이 있어도 마지막이 필드면 유효)"""
    tokens = [
        Token(TokenType.IDENTIFIER, "a"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "b"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "c"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.NUMBER, "5", literal=5.0),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        ExpressionStmt(
            expression=FieldSetExpr(
                object=CallExpr(
                    callee=FieldGetExpr(
                        object=VariableExpr(Token(TokenType.IDENTIFIER, "a")),
                        name=Token(TokenType.IDENTIFIER, "b"),
                    ),
                    paren=Token(TokenType.LEFT_PAREN, "("),
                    arguments=[],
                ),
                name=Token(TokenType.IDENTIFIER, "c"),
                value=LiteralExpr(5.0),
            )
        )
    ]


def test_step16_assignment_target_ending_in_call_raises_invalid_assignment_target_error():
    """소스코드: a.b().c() = 5;  (대입 대상의 마지막 단계가 호출이면 여전히 불가)"""
    tokens = [
        Token(TokenType.IDENTIFIER, "a"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "b"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "c"),
        Token(TokenType.LEFT_PAREN, "("),
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


def test_step16_this_reassignment_raises_invalid_assignment_target_error():
    """소스코드: this = 5;  (this 자체는 대입 대상이 될 수 없음)"""
    tokens = [
        Token(TokenType.THIS, "this"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.NUMBER, "5", literal=5.0),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    with pytest.raises(InvalidAssignmentTargetError) as excinfo:
        builder.build()

    assert "Invalid assignment target" in str(excinfo.value)


def test_step16_super_field_reassignment_raises_invalid_assignment_target_error():
    """소스코드: super.move = 5;  (SuperExpr 자체도 대입 대상이 될 수 없음)"""
    tokens = [
        Token(TokenType.SUPER, "super"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "move"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.NUMBER, "5", literal=5.0),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    with pytest.raises(InvalidAssignmentTargetError) as excinfo:
        builder.build()

    assert "Invalid assignment target" in str(excinfo.value)


def test_step16_dot_followed_by_keyword_raises_missing_token_error():
    """소스코드: r.this;  ('.' 뒤에 식별자가 아닌 키워드 토큰(this)이 옴)"""
    tokens = [
        Token(TokenType.IDENTIFIER, "r"),
        Token(TokenType.DOT, "."),
        Token(TokenType.THIS, "this"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    with pytest.raises(MissingTokenError) as excinfo:
        builder.build()

    assert "Expected property name after '.'" in str(excinfo.value)
    assert excinfo.value.token == Token(TokenType.THIS, "this")


def test_step16_dot_followed_by_number_raises_missing_token_error():
    """소스코드: r.5;  ('.' 뒤에 식별자가 아닌 숫자 리터럴이 옴)"""
    tokens = [
        Token(TokenType.IDENTIFIER, "r"),
        Token(TokenType.DOT, "."),
        Token(TokenType.NUMBER, "5", literal=5.0),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    with pytest.raises(MissingTokenError) as excinfo:
        builder.build()

    assert "Expected property name after '.'" in str(excinfo.value)


def test_step16_nested_dot_missing_final_property_name_raises_missing_token_error():
    """소스코드: a.b.;  (연쇄 접근 중 마지막 '.' 뒤에 필드 이름이 없음)"""
    tokens = [
        Token(TokenType.IDENTIFIER, "a"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "b"),
        Token(TokenType.DOT, "."),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    with pytest.raises(MissingTokenError) as excinfo:
        builder.build()

    assert "Expected property name after '.'" in str(excinfo.value)
    assert excinfo.value.token == Token(TokenType.SEMICOLON, ";")


def test_step16_field_write_missing_value_raises_unexpected_token_error():
    """소스코드: r.speed = ;  ('=' 뒤에 대입할 값이 없음)"""
    tokens = [
        Token(TokenType.IDENTIFIER, "r"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "speed"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    with pytest.raises(UnexpectedTokenError) as excinfo:
        builder.build()

    assert "Unexpected token" in str(excinfo.value)


def test_step16_field_write_missing_semicolon_raises_missing_token_error():
    """소스코드: r.speed = 10  (세미콜론 누락)"""
    tokens = [
        Token(TokenType.IDENTIFIER, "r"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "speed"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.NUMBER, "10", literal=10.0),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    with pytest.raises(MissingTokenError) as excinfo:
        builder.build()

    assert "Expected ';' after expression" in str(excinfo.value)
    assert excinfo.value.token == Token(TokenType.EOF, "")


# --- 17단계: function + class(필드/this/super) 통합 시나리오 ---
#
# ClassStmt(선언/상속/instanceof)는 이 담당 범위가 아니므로, 아직 파싱되지
# 않는다. 대신 이미 구현된 FunctionStmt로 "메서드 본문"에 해당하는 코드를
# 감싸 function과 필드 접근/this/super/호출 체인이 실제로 함께 쓰일 때도
# 정확히 조립되는지 검증한다.

def test_step17_function_updates_this_field_and_returns_it():
    """소스코드: Func move(dist) { this.position = this.position + dist; return this.position; }"""
    tokens = [
        Token(TokenType.FUNC, "Func"),
        Token(TokenType.IDENTIFIER, "move"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.IDENTIFIER, "dist"),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.THIS, "this"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "position"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.THIS, "this"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "position"),
        Token(TokenType.PLUS, "+"),
        Token(TokenType.IDENTIFIER, "dist"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RETURN, "return"),
        Token(TokenType.THIS, "this"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "position"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    this_position = FieldGetExpr(
        object=ThisExpr(keyword=Token(TokenType.THIS, "this")),
        name=Token(TokenType.IDENTIFIER, "position"),
    )

    assert builder.build() == [
        FunctionStmt(
            name=Token(TokenType.IDENTIFIER, "move"),
            params=[Token(TokenType.IDENTIFIER, "dist")],
            body=[
                ExpressionStmt(
                    expression=FieldSetExpr(
                        object=ThisExpr(keyword=Token(TokenType.THIS, "this")),
                        name=Token(TokenType.IDENTIFIER, "position"),
                        value=BinaryExpr(
                            left=this_position,
                            operator=Token(TokenType.PLUS, "+"),
                            right=VariableExpr(Token(TokenType.IDENTIFIER, "dist")),
                        ),
                    )
                ),
                ReturnStmt(keyword=Token(TokenType.RETURN, "return"), value=this_position),
            ],
        )
    ]


def test_step17_init_style_function_initializes_fields_from_params():
    """소스코드: Func init(name, speed) { this.name = name; this.speed = speed; }
    (요구사항_정리/class.md의 "생성자에서 필드 초기화" 예시를 함수 이름 init으로 재현)
    """
    tokens = [
        Token(TokenType.FUNC, "Func"),
        Token(TokenType.IDENTIFIER, "init"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.IDENTIFIER, "name"),
        Token(TokenType.COMMA, ","),
        Token(TokenType.IDENTIFIER, "speed"),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.THIS, "this"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "name"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.IDENTIFIER, "name"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.THIS, "this"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "speed"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.IDENTIFIER, "speed"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        FunctionStmt(
            name=Token(TokenType.IDENTIFIER, "init"),
            params=[Token(TokenType.IDENTIFIER, "name"), Token(TokenType.IDENTIFIER, "speed")],
            body=[
                ExpressionStmt(
                    expression=FieldSetExpr(
                        object=ThisExpr(keyword=Token(TokenType.THIS, "this")),
                        name=Token(TokenType.IDENTIFIER, "name"),
                        value=VariableExpr(Token(TokenType.IDENTIFIER, "name")),
                    )
                ),
                ExpressionStmt(
                    expression=FieldSetExpr(
                        object=ThisExpr(keyword=Token(TokenType.THIS, "this")),
                        name=Token(TokenType.IDENTIFIER, "speed"),
                        value=VariableExpr(Token(TokenType.IDENTIFIER, "speed")),
                    )
                ),
            ],
        )
    ]


def test_step17_function_calls_super_before_updating_this_field():
    """소스코드: Func move(dist) { super.move(dist); this.position = this.position + dist; }"""
    tokens = [
        Token(TokenType.FUNC, "Func"),
        Token(TokenType.IDENTIFIER, "move"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.IDENTIFIER, "dist"),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.SUPER, "super"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "move"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.IDENTIFIER, "dist"),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.THIS, "this"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "position"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.THIS, "this"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "position"),
        Token(TokenType.PLUS, "+"),
        Token(TokenType.IDENTIFIER, "dist"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        FunctionStmt(
            name=Token(TokenType.IDENTIFIER, "move"),
            params=[Token(TokenType.IDENTIFIER, "dist")],
            body=[
                ExpressionStmt(
                    expression=CallExpr(
                        callee=SuperExpr(
                            keyword=Token(TokenType.SUPER, "super"),
                            method=Token(TokenType.IDENTIFIER, "move"),
                        ),
                        paren=Token(TokenType.LEFT_PAREN, "("),
                        arguments=[VariableExpr(Token(TokenType.IDENTIFIER, "dist"))],
                    )
                ),
                ExpressionStmt(
                    expression=FieldSetExpr(
                        object=ThisExpr(keyword=Token(TokenType.THIS, "this")),
                        name=Token(TokenType.IDENTIFIER, "position"),
                        value=BinaryExpr(
                            left=FieldGetExpr(
                                object=ThisExpr(keyword=Token(TokenType.THIS, "this")),
                                name=Token(TokenType.IDENTIFIER, "position"),
                            ),
                            operator=Token(TokenType.PLUS, "+"),
                            right=VariableExpr(Token(TokenType.IDENTIFIER, "dist")),
                        ),
                    )
                ),
            ],
        )
    ]


def test_step17_recursive_function_branches_on_field_and_calls_method():
    """소스코드:
    Func report(r) {
        if (r.count > 0) {
            r.report();
            return report(r.next);
        }
        return r.count;
    }
    """
    tokens = [
        Token(TokenType.FUNC, "Func"),
        Token(TokenType.IDENTIFIER, "report"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.IDENTIFIER, "r"),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.IF, "if"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.IDENTIFIER, "r"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "count"),
        Token(TokenType.GREATER, ">"),
        Token(TokenType.NUMBER, "0", literal=0.0),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.IDENTIFIER, "r"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "report"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RETURN, "return"),
        Token(TokenType.IDENTIFIER, "report"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.IDENTIFIER, "r"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "next"),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.RETURN, "return"),
        Token(TokenType.IDENTIFIER, "r"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "count"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        FunctionStmt(
            name=Token(TokenType.IDENTIFIER, "report"),
            params=[Token(TokenType.IDENTIFIER, "r")],
            body=[
                IfStmt(
                    condition=BinaryExpr(
                        left=FieldGetExpr(
                            object=VariableExpr(Token(TokenType.IDENTIFIER, "r")),
                            name=Token(TokenType.IDENTIFIER, "count"),
                        ),
                        operator=Token(TokenType.GREATER, ">"),
                        right=LiteralExpr(0.0),
                    ),
                    then_branch=BlockStmt(
                        statements=[
                            ExpressionStmt(
                                expression=CallExpr(
                                    callee=FieldGetExpr(
                                        object=VariableExpr(Token(TokenType.IDENTIFIER, "r")),
                                        name=Token(TokenType.IDENTIFIER, "report"),
                                    ),
                                    paren=Token(TokenType.LEFT_PAREN, "("),
                                    arguments=[],
                                )
                            ),
                            ReturnStmt(
                                keyword=Token(TokenType.RETURN, "return"),
                                value=CallExpr(
                                    callee=VariableExpr(Token(TokenType.IDENTIFIER, "report")),
                                    paren=Token(TokenType.LEFT_PAREN, "("),
                                    arguments=[
                                        FieldGetExpr(
                                            object=VariableExpr(Token(TokenType.IDENTIFIER, "r")),
                                            name=Token(TokenType.IDENTIFIER, "next"),
                                        )
                                    ],
                                ),
                            ),
                        ]
                    ),
                    else_branch=None,
                ),
                ReturnStmt(
                    keyword=Token(TokenType.RETURN, "return"),
                    value=FieldGetExpr(
                        object=VariableExpr(Token(TokenType.IDENTIFIER, "r")),
                        name=Token(TokenType.IDENTIFIER, "count"),
                    ),
                ),
            ],
        )
    ]


def test_step17_function_returns_method_call_chained_on_instance_creation():
    """소스코드: Func makeAndMove(name, speed, dist) { return Robot(name, speed).move(dist); }

    Robot(name, speed)는 별도 Expr 없이 CallExpr로 파싱된다(요구사항_정리/class.md의
    Command Pattern처럼 인스턴스 생성도 함수 호출과 같은 callable로 다룬다).
    """
    tokens = [
        Token(TokenType.FUNC, "Func"),
        Token(TokenType.IDENTIFIER, "makeAndMove"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.IDENTIFIER, "name"),
        Token(TokenType.COMMA, ","),
        Token(TokenType.IDENTIFIER, "speed"),
        Token(TokenType.COMMA, ","),
        Token(TokenType.IDENTIFIER, "dist"),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.RETURN, "return"),
        Token(TokenType.IDENTIFIER, "Robot"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.IDENTIFIER, "name"),
        Token(TokenType.COMMA, ","),
        Token(TokenType.IDENTIFIER, "speed"),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "move"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.IDENTIFIER, "dist"),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        FunctionStmt(
            name=Token(TokenType.IDENTIFIER, "makeAndMove"),
            params=[
                Token(TokenType.IDENTIFIER, "name"),
                Token(TokenType.IDENTIFIER, "speed"),
                Token(TokenType.IDENTIFIER, "dist"),
            ],
            body=[
                ReturnStmt(
                    keyword=Token(TokenType.RETURN, "return"),
                    value=CallExpr(
                        callee=FieldGetExpr(
                            object=CallExpr(
                                callee=VariableExpr(Token(TokenType.IDENTIFIER, "Robot")),
                                paren=Token(TokenType.LEFT_PAREN, "("),
                                arguments=[
                                    VariableExpr(Token(TokenType.IDENTIFIER, "name")),
                                    VariableExpr(Token(TokenType.IDENTIFIER, "speed")),
                                ],
                            ),
                            name=Token(TokenType.IDENTIFIER, "move"),
                        ),
                        paren=Token(TokenType.LEFT_PAREN, "("),
                        arguments=[VariableExpr(Token(TokenType.IDENTIFIER, "dist"))],
                    ),
                )
            ],
        )
    ]


# --- 18단계: class 선언 파싱 (요구사항_정리/class.md) ---
#
# 메서드(생성자 init 포함)는 function.md의 FunctionStmt와 달리 `Func`
# 키워드 없이 `이름(params) { body }` 형태로 클래스 본문 안에 곧장
# 나열된다는 점이 핵심 문법 차이다.

def test_step18_empty_class_declaration():
    """소스코드: Class Robot { }"""
    tokens = [
        Token(TokenType.CLASS, "Class"),
        Token(TokenType.IDENTIFIER, "Robot"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        ClassStmt(name=Token(TokenType.IDENTIFIER, "Robot"), superclass=None, methods=[])
    ]


def test_step18_class_declaration_with_single_method():
    """소스코드: Class Robot { move(dist) { this.position = this.position + dist; } }"""
    tokens = [
        Token(TokenType.CLASS, "Class"),
        Token(TokenType.IDENTIFIER, "Robot"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.IDENTIFIER, "move"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.IDENTIFIER, "dist"),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.THIS, "this"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "position"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.THIS, "this"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "position"),
        Token(TokenType.PLUS, "+"),
        Token(TokenType.IDENTIFIER, "dist"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        ClassStmt(
            name=Token(TokenType.IDENTIFIER, "Robot"),
            superclass=None,
            methods=[
                FunctionStmt(
                    name=Token(TokenType.IDENTIFIER, "move"),
                    params=[Token(TokenType.IDENTIFIER, "dist")],
                    body=[
                        ExpressionStmt(
                            expression=FieldSetExpr(
                                object=ThisExpr(keyword=Token(TokenType.THIS, "this")),
                                name=Token(TokenType.IDENTIFIER, "position"),
                                value=BinaryExpr(
                                    left=FieldGetExpr(
                                        object=ThisExpr(keyword=Token(TokenType.THIS, "this")),
                                        name=Token(TokenType.IDENTIFIER, "position"),
                                    ),
                                    operator=Token(TokenType.PLUS, "+"),
                                    right=VariableExpr(Token(TokenType.IDENTIFIER, "dist")),
                                ),
                            )
                        )
                    ],
                )
            ],
        )
    ]


def test_step18_class_declaration_with_init_and_move_methods():
    """소스코드:
    Class Robot {
        init(name, speed) { this.name = name; this.speed = speed; }
        move(dist) { this.position = this.position + dist; }
    }
    """
    tokens = [
        Token(TokenType.CLASS, "Class"),
        Token(TokenType.IDENTIFIER, "Robot"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.IDENTIFIER, "init"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.IDENTIFIER, "name"),
        Token(TokenType.COMMA, ","),
        Token(TokenType.IDENTIFIER, "speed"),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.THIS, "this"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "name"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.IDENTIFIER, "name"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.THIS, "this"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "speed"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.IDENTIFIER, "speed"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.IDENTIFIER, "move"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.IDENTIFIER, "dist"),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.THIS, "this"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "position"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.THIS, "this"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "position"),
        Token(TokenType.PLUS, "+"),
        Token(TokenType.IDENTIFIER, "dist"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    result = builder.build()
    assert len(result) == 1
    class_stmt = result[0]
    assert isinstance(class_stmt, ClassStmt)
    assert class_stmt.name == Token(TokenType.IDENTIFIER, "Robot")
    assert class_stmt.superclass is None
    assert [m.name for m in class_stmt.methods] == [
        Token(TokenType.IDENTIFIER, "init"),
        Token(TokenType.IDENTIFIER, "move"),
    ]
    assert class_stmt.methods[0] == FunctionStmt(
        name=Token(TokenType.IDENTIFIER, "init"),
        params=[Token(TokenType.IDENTIFIER, "name"), Token(TokenType.IDENTIFIER, "speed")],
        body=[
            ExpressionStmt(
                expression=FieldSetExpr(
                    object=ThisExpr(keyword=Token(TokenType.THIS, "this")),
                    name=Token(TokenType.IDENTIFIER, "name"),
                    value=VariableExpr(Token(TokenType.IDENTIFIER, "name")),
                )
            ),
            ExpressionStmt(
                expression=FieldSetExpr(
                    object=ThisExpr(keyword=Token(TokenType.THIS, "this")),
                    name=Token(TokenType.IDENTIFIER, "speed"),
                    value=VariableExpr(Token(TokenType.IDENTIFIER, "speed")),
                )
            ),
        ],
    )


def test_step18_class_declaration_with_inheritance_and_super_call():
    """소스코드: Class SpeedRobot : Robot { move(dist) { super.move(dist); } }"""
    tokens = [
        Token(TokenType.CLASS, "Class"),
        Token(TokenType.IDENTIFIER, "SpeedRobot"),
        Token(TokenType.COLON, ":"),
        Token(TokenType.IDENTIFIER, "Robot"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.IDENTIFIER, "move"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.IDENTIFIER, "dist"),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.SUPER, "super"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "move"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.IDENTIFIER, "dist"),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        ClassStmt(
            name=Token(TokenType.IDENTIFIER, "SpeedRobot"),
            superclass=VariableExpr(Token(TokenType.IDENTIFIER, "Robot")),
            methods=[
                FunctionStmt(
                    name=Token(TokenType.IDENTIFIER, "move"),
                    params=[Token(TokenType.IDENTIFIER, "dist")],
                    body=[
                        ExpressionStmt(
                            expression=CallExpr(
                                callee=SuperExpr(
                                    keyword=Token(TokenType.SUPER, "super"),
                                    method=Token(TokenType.IDENTIFIER, "move"),
                                ),
                                paren=Token(TokenType.LEFT_PAREN, "("),
                                arguments=[VariableExpr(Token(TokenType.IDENTIFIER, "dist"))],
                            )
                        )
                    ],
                )
            ],
        )
    ]


def test_step18_instance_creation_without_arguments_is_call_expr():
    """소스코드: var r = Robot();  (인스턴스 생성도 별도 Expr 없이 CallExpr로 파싱된다)"""
    tokens = [
        Token(TokenType.VAR, "var"),
        Token(TokenType.IDENTIFIER, "r"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.IDENTIFIER, "Robot"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        VarDeclStmt(
            name=Token(TokenType.IDENTIFIER, "r"),
            initializer=CallExpr(
                callee=VariableExpr(Token(TokenType.IDENTIFIER, "Robot")),
                paren=Token(TokenType.LEFT_PAREN, "("),
                arguments=[],
            ),
        )
    ]


def test_step18_instance_creation_with_constructor_arguments():
    """소스코드: var r = Robot("AndOr", 10);"""
    tokens = [
        Token(TokenType.VAR, "var"),
        Token(TokenType.IDENTIFIER, "r"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.IDENTIFIER, "Robot"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.STRING, '"AndOr"', literal="AndOr"),
        Token(TokenType.COMMA, ","),
        Token(TokenType.NUMBER, "10", literal=10.0),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        VarDeclStmt(
            name=Token(TokenType.IDENTIFIER, "r"),
            initializer=CallExpr(
                callee=VariableExpr(Token(TokenType.IDENTIFIER, "Robot")),
                paren=Token(TokenType.LEFT_PAREN, "("),
                arguments=[LiteralExpr("AndOr"), LiteralExpr(10.0)],
            ),
        )
    ]


def test_step18_class_missing_name_raises_missing_token_error():
    """소스코드: Class { }  (클래스 이름 누락)"""
    tokens = [
        Token(TokenType.CLASS, "Class"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    with pytest.raises(MissingTokenError) as excinfo:
        builder.build()

    assert "Expected class name" in str(excinfo.value)
    assert excinfo.value.token == Token(TokenType.LEFT_BRACE, "{")


def test_step18_class_missing_superclass_name_raises_missing_token_error():
    """소스코드: Class SpeedRobot : { }  (':' 뒤에 부모 클래스 이름 누락)"""
    tokens = [
        Token(TokenType.CLASS, "Class"),
        Token(TokenType.IDENTIFIER, "SpeedRobot"),
        Token(TokenType.COLON, ":"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    with pytest.raises(MissingTokenError) as excinfo:
        builder.build()

    assert "Expected superclass name" in str(excinfo.value)
    assert excinfo.value.token == Token(TokenType.LEFT_BRACE, "{")


def test_step18_class_missing_body_left_brace_raises_missing_token_error():
    """소스코드: Class Robot  (본문 자체가 없음)"""
    tokens = [
        Token(TokenType.CLASS, "Class"),
        Token(TokenType.IDENTIFIER, "Robot"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    with pytest.raises(MissingTokenError) as excinfo:
        builder.build()

    assert "Expected '{' before class body" in str(excinfo.value)
    assert excinfo.value.token == Token(TokenType.EOF, "")


def test_step18_unterminated_class_body_raises_missing_token_error():
    """소스코드: Class Robot {  (닫는 '}' 없이 끝남)"""
    tokens = [
        Token(TokenType.CLASS, "Class"),
        Token(TokenType.IDENTIFIER, "Robot"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    with pytest.raises(MissingTokenError) as excinfo:
        builder.build()

    assert "Expected '}' after class body" in str(excinfo.value)
    assert excinfo.value.token == Token(TokenType.EOF, "")


def test_step18_method_missing_name_raises_missing_token_error():
    """소스코드: Class Robot { () { } }  (메서드 이름 누락)"""
    tokens = [
        Token(TokenType.CLASS, "Class"),
        Token(TokenType.IDENTIFIER, "Robot"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    with pytest.raises(MissingTokenError) as excinfo:
        builder.build()

    assert "Expected method name" in str(excinfo.value)
    assert excinfo.value.token == Token(TokenType.LEFT_PAREN, "(")


def test_step18_method_missing_left_paren_raises_missing_token_error():
    """소스코드: Class Robot { move { } }  (메서드 이름 뒤 '(' 누락)"""
    tokens = [
        Token(TokenType.CLASS, "Class"),
        Token(TokenType.IDENTIFIER, "Robot"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.IDENTIFIER, "move"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    with pytest.raises(MissingTokenError) as excinfo:
        builder.build()

    assert "Expected '(' after method name" in str(excinfo.value)


def test_step18_method_missing_body_left_brace_raises_missing_token_error():
    """소스코드: Class Robot { move(dist) ; }  (메서드 본문 '{' 누락)"""
    tokens = [
        Token(TokenType.CLASS, "Class"),
        Token(TokenType.IDENTIFIER, "Robot"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.IDENTIFIER, "move"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.IDENTIFIER, "dist"),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    with pytest.raises(MissingTokenError) as excinfo:
        builder.build()

    assert "Expected '{' before method body" in str(excinfo.value)


def test_step18_func_keyword_inside_class_body_is_rejected():
    """소스코드: Class Robot { Func move() { } }

    메서드 선언은 function.md의 FunctionStmt와 달리 `Func` 키워드 없이
    시작해야 하므로, 클래스 본문 안에서 `Func`를 쓰면 메서드 이름 자리에
    엉뚱한 키워드 토큰이 온 것으로 처리되어 실패해야 한다.
    """
    tokens = [
        Token(TokenType.CLASS, "Class"),
        Token(TokenType.IDENTIFIER, "Robot"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.FUNC, "Func"),
        Token(TokenType.IDENTIFIER, "move"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    with pytest.raises(MissingTokenError) as excinfo:
        builder.build()

    assert "Expected method name" in str(excinfo.value)
    assert excinfo.value.token == Token(TokenType.FUNC, "Func")


# --- 19단계: function + class 통합 시나리오 (ClassStmt 구현 후 재검증) ---
#
# 17단계는 ClassStmt가 아직 없어 FunctionStmt로 메서드 본문만 흉내 냈다.
# 이제 실제 ClassStmt(선언/상속/메서드 목록)가 구현됐으니, 최상위에서
# FunctionStmt와 ClassStmt가 함께 등장하는 프로그램도 정확히 조립되는지,
# 그리고 클래스 메서드 내부에서 재귀/배열 인덱싱/다중 super 호출처럼 더
# 복잡한 조합도 무리없이 파싱되는지 검증한다.

def test_step19_program_mixes_function_and_class_declarations():
    """소스코드:
    Func makeRobot(name, speed) {
        var r = Robot(name, speed);
        return r;
    }

    Class Robot {
        init(name, speed) { this.name = name; this.speed = speed; }
        move(dist) { this.position = this.position + dist; return this.position; }
    }
    """
    tokens = [
        Token(TokenType.FUNC, "Func"),
        Token(TokenType.IDENTIFIER, "makeRobot"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.IDENTIFIER, "name"),
        Token(TokenType.COMMA, ","),
        Token(TokenType.IDENTIFIER, "speed"),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.VAR, "var"),
        Token(TokenType.IDENTIFIER, "r"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.IDENTIFIER, "Robot"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.IDENTIFIER, "name"),
        Token(TokenType.COMMA, ","),
        Token(TokenType.IDENTIFIER, "speed"),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RETURN, "return"),
        Token(TokenType.IDENTIFIER, "r"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.CLASS, "Class"),
        Token(TokenType.IDENTIFIER, "Robot"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.IDENTIFIER, "init"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.IDENTIFIER, "name"),
        Token(TokenType.COMMA, ","),
        Token(TokenType.IDENTIFIER, "speed"),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.THIS, "this"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "name"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.IDENTIFIER, "name"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.THIS, "this"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "speed"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.IDENTIFIER, "speed"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.IDENTIFIER, "move"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.IDENTIFIER, "dist"),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.THIS, "this"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "position"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.THIS, "this"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "position"),
        Token(TokenType.PLUS, "+"),
        Token(TokenType.IDENTIFIER, "dist"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RETURN, "return"),
        Token(TokenType.THIS, "this"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "position"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    this_position = FieldGetExpr(
        object=ThisExpr(keyword=Token(TokenType.THIS, "this")),
        name=Token(TokenType.IDENTIFIER, "position"),
    )

    assert builder.build() == [
        FunctionStmt(
            name=Token(TokenType.IDENTIFIER, "makeRobot"),
            params=[Token(TokenType.IDENTIFIER, "name"), Token(TokenType.IDENTIFIER, "speed")],
            body=[
                VarDeclStmt(
                    name=Token(TokenType.IDENTIFIER, "r"),
                    initializer=CallExpr(
                        callee=VariableExpr(Token(TokenType.IDENTIFIER, "Robot")),
                        paren=Token(TokenType.LEFT_PAREN, "("),
                        arguments=[
                            VariableExpr(Token(TokenType.IDENTIFIER, "name")),
                            VariableExpr(Token(TokenType.IDENTIFIER, "speed")),
                        ],
                    ),
                ),
                ReturnStmt(
                    keyword=Token(TokenType.RETURN, "return"),
                    value=VariableExpr(Token(TokenType.IDENTIFIER, "r")),
                ),
            ],
        ),
        ClassStmt(
            name=Token(TokenType.IDENTIFIER, "Robot"),
            superclass=None,
            methods=[
                FunctionStmt(
                    name=Token(TokenType.IDENTIFIER, "init"),
                    params=[Token(TokenType.IDENTIFIER, "name"), Token(TokenType.IDENTIFIER, "speed")],
                    body=[
                        ExpressionStmt(
                            expression=FieldSetExpr(
                                object=ThisExpr(keyword=Token(TokenType.THIS, "this")),
                                name=Token(TokenType.IDENTIFIER, "name"),
                                value=VariableExpr(Token(TokenType.IDENTIFIER, "name")),
                            )
                        ),
                        ExpressionStmt(
                            expression=FieldSetExpr(
                                object=ThisExpr(keyword=Token(TokenType.THIS, "this")),
                                name=Token(TokenType.IDENTIFIER, "speed"),
                                value=VariableExpr(Token(TokenType.IDENTIFIER, "speed")),
                            )
                        ),
                    ],
                ),
                FunctionStmt(
                    name=Token(TokenType.IDENTIFIER, "move"),
                    params=[Token(TokenType.IDENTIFIER, "dist")],
                    body=[
                        ExpressionStmt(
                            expression=FieldSetExpr(
                                object=ThisExpr(keyword=Token(TokenType.THIS, "this")),
                                name=Token(TokenType.IDENTIFIER, "position"),
                                value=BinaryExpr(
                                    left=this_position,
                                    operator=Token(TokenType.PLUS, "+"),
                                    right=VariableExpr(Token(TokenType.IDENTIFIER, "dist")),
                                ),
                            )
                        ),
                        ReturnStmt(keyword=Token(TokenType.RETURN, "return"), value=this_position),
                    ],
                ),
            ],
        ),
    ]


def test_step19_class_method_recurses_through_this_call():
    """소스코드:
    Class Counter {
        init(n) { this.n = n; }
        countdown() {
            if (this.n <= 0) { return 0; }
            this.n = this.n - 1;
            return this.countdown();
        }
    }
    """
    tokens = [
        Token(TokenType.CLASS, "Class"),
        Token(TokenType.IDENTIFIER, "Counter"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.IDENTIFIER, "init"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.IDENTIFIER, "n"),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.THIS, "this"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "n"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.IDENTIFIER, "n"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.IDENTIFIER, "countdown"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.IF, "if"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.THIS, "this"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "n"),
        Token(TokenType.LESS_EQUAL, "<="),
        Token(TokenType.NUMBER, "0", literal=0.0),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.RETURN, "return"),
        Token(TokenType.NUMBER, "0", literal=0.0),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.THIS, "this"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "n"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.THIS, "this"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "n"),
        Token(TokenType.MINUS, "-"),
        Token(TokenType.NUMBER, "1", literal=1.0),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RETURN, "return"),
        Token(TokenType.THIS, "this"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "countdown"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    this_n = FieldGetExpr(
        object=ThisExpr(keyword=Token(TokenType.THIS, "this")),
        name=Token(TokenType.IDENTIFIER, "n"),
    )

    assert builder.build() == [
        ClassStmt(
            name=Token(TokenType.IDENTIFIER, "Counter"),
            superclass=None,
            methods=[
                FunctionStmt(
                    name=Token(TokenType.IDENTIFIER, "init"),
                    params=[Token(TokenType.IDENTIFIER, "n")],
                    body=[
                        ExpressionStmt(
                            expression=FieldSetExpr(
                                object=ThisExpr(keyword=Token(TokenType.THIS, "this")),
                                name=Token(TokenType.IDENTIFIER, "n"),
                                value=VariableExpr(Token(TokenType.IDENTIFIER, "n")),
                            )
                        )
                    ],
                ),
                FunctionStmt(
                    name=Token(TokenType.IDENTIFIER, "countdown"),
                    params=[],
                    body=[
                        IfStmt(
                            condition=BinaryExpr(
                                left=this_n,
                                operator=Token(TokenType.LESS_EQUAL, "<="),
                                right=LiteralExpr(0.0),
                            ),
                            then_branch=BlockStmt(
                                statements=[
                                    ReturnStmt(
                                        keyword=Token(TokenType.RETURN, "return"),
                                        value=LiteralExpr(0.0),
                                    )
                                ]
                            ),
                            else_branch=None,
                        ),
                        ExpressionStmt(
                            expression=FieldSetExpr(
                                object=ThisExpr(keyword=Token(TokenType.THIS, "this")),
                                name=Token(TokenType.IDENTIFIER, "n"),
                                value=BinaryExpr(
                                    left=this_n,
                                    operator=Token(TokenType.MINUS, "-"),
                                    right=LiteralExpr(1.0),
                                ),
                            )
                        ),
                        ReturnStmt(
                            keyword=Token(TokenType.RETURN, "return"),
                            value=CallExpr(
                                callee=FieldGetExpr(
                                    object=ThisExpr(keyword=Token(TokenType.THIS, "this")),
                                    name=Token(TokenType.IDENTIFIER, "countdown"),
                                ),
                                paren=Token(TokenType.LEFT_PAREN, "("),
                                arguments=[],
                            ),
                        ),
                    ],
                ),
            ],
        )
    ]


def test_step19_class_method_indexes_into_array_field():
    """소스코드:
    Class Team {
        init(members) { this.members = members; }
        first() { return this.members[0]; }
    }
    """
    tokens = [
        Token(TokenType.CLASS, "Class"),
        Token(TokenType.IDENTIFIER, "Team"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.IDENTIFIER, "init"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.IDENTIFIER, "members"),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.THIS, "this"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "members"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.IDENTIFIER, "members"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.IDENTIFIER, "first"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.RETURN, "return"),
        Token(TokenType.THIS, "this"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "members"),
        Token(TokenType.LEFT_BRACKET, "["),
        Token(TokenType.NUMBER, "0", literal=0.0),
        Token(TokenType.RIGHT_BRACKET, "]"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        ClassStmt(
            name=Token(TokenType.IDENTIFIER, "Team"),
            superclass=None,
            methods=[
                FunctionStmt(
                    name=Token(TokenType.IDENTIFIER, "init"),
                    params=[Token(TokenType.IDENTIFIER, "members")],
                    body=[
                        ExpressionStmt(
                            expression=FieldSetExpr(
                                object=ThisExpr(keyword=Token(TokenType.THIS, "this")),
                                name=Token(TokenType.IDENTIFIER, "members"),
                                value=VariableExpr(Token(TokenType.IDENTIFIER, "members")),
                            )
                        )
                    ],
                ),
                FunctionStmt(
                    name=Token(TokenType.IDENTIFIER, "first"),
                    params=[],
                    body=[
                        ReturnStmt(
                            keyword=Token(TokenType.RETURN, "return"),
                            value=IndexGetExpr(
                                object=FieldGetExpr(
                                    object=ThisExpr(keyword=Token(TokenType.THIS, "this")),
                                    name=Token(TokenType.IDENTIFIER, "members"),
                                ),
                                bracket=Token(TokenType.LEFT_BRACKET, "["),
                                index=LiteralExpr(0.0),
                            ),
                        )
                    ],
                ),
            ],
        )
    ]


def test_step19_subclass_method_calls_super_twice():
    """소스코드:
    Class SpeedRobot : Robot {
        move(dist) {
            super.move(dist);
            return super.move(dist);
        }
    }
    """
    tokens = [
        Token(TokenType.CLASS, "Class"),
        Token(TokenType.IDENTIFIER, "SpeedRobot"),
        Token(TokenType.COLON, ":"),
        Token(TokenType.IDENTIFIER, "Robot"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.IDENTIFIER, "move"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.IDENTIFIER, "dist"),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.SUPER, "super"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "move"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.IDENTIFIER, "dist"),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RETURN, "return"),
        Token(TokenType.SUPER, "super"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "move"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.IDENTIFIER, "dist"),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    super_move_call = CallExpr(
        callee=SuperExpr(keyword=Token(TokenType.SUPER, "super"), method=Token(TokenType.IDENTIFIER, "move")),
        paren=Token(TokenType.LEFT_PAREN, "("),
        arguments=[VariableExpr(Token(TokenType.IDENTIFIER, "dist"))],
    )

    assert builder.build() == [
        ClassStmt(
            name=Token(TokenType.IDENTIFIER, "SpeedRobot"),
            superclass=VariableExpr(Token(TokenType.IDENTIFIER, "Robot")),
            methods=[
                FunctionStmt(
                    name=Token(TokenType.IDENTIFIER, "move"),
                    params=[Token(TokenType.IDENTIFIER, "dist")],
                    body=[
                        ExpressionStmt(expression=super_move_call),
                        ReturnStmt(keyword=Token(TokenType.RETURN, "return"), value=super_move_call),
                    ],
                )
            ],
        )
    ]


def test_step19_full_program_with_class_function_var_and_print():
    """소스코드:
    Class Robot {
        init(name, speed) { this.name = name; this.speed = speed; }
        move(dist) { this.position = this.position + dist; return this.position; }
    }

    Func report(r) {
        print r.name;
        return r.move(5);
    }

    var r = Robot("AndOr", 10);
    print report(r);

    최상위에 ClassStmt/FunctionStmt/VarDeclStmt/PrintStmt 네 종류가 순서대로
    섞여 나오는 실제 프로그램 형태를 그대로 재현한다.
    """
    tokens = [
        Token(TokenType.CLASS, "Class"),
        Token(TokenType.IDENTIFIER, "Robot"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.IDENTIFIER, "init"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.IDENTIFIER, "name"),
        Token(TokenType.COMMA, ","),
        Token(TokenType.IDENTIFIER, "speed"),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.THIS, "this"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "name"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.IDENTIFIER, "name"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.THIS, "this"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "speed"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.IDENTIFIER, "speed"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.IDENTIFIER, "move"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.IDENTIFIER, "dist"),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.THIS, "this"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "position"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.THIS, "this"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "position"),
        Token(TokenType.PLUS, "+"),
        Token(TokenType.IDENTIFIER, "dist"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RETURN, "return"),
        Token(TokenType.THIS, "this"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "position"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.FUNC, "Func"),
        Token(TokenType.IDENTIFIER, "report"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.IDENTIFIER, "r"),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.PRINT, "print"),
        Token(TokenType.IDENTIFIER, "r"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "name"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RETURN, "return"),
        Token(TokenType.IDENTIFIER, "r"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "move"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.NUMBER, "5", literal=5.0),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.VAR, "var"),
        Token(TokenType.IDENTIFIER, "r"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.IDENTIFIER, "Robot"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.STRING, '"AndOr"', literal="AndOr"),
        Token(TokenType.COMMA, ","),
        Token(TokenType.NUMBER, "10", literal=10.0),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.PRINT, "print"),
        Token(TokenType.IDENTIFIER, "report"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.IDENTIFIER, "r"),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    this_position = FieldGetExpr(
        object=ThisExpr(keyword=Token(TokenType.THIS, "this")),
        name=Token(TokenType.IDENTIFIER, "position"),
    )

    result = builder.build()
    assert len(result) == 4

    assert result[0] == ClassStmt(
        name=Token(TokenType.IDENTIFIER, "Robot"),
        superclass=None,
        methods=[
            FunctionStmt(
                name=Token(TokenType.IDENTIFIER, "init"),
                params=[Token(TokenType.IDENTIFIER, "name"), Token(TokenType.IDENTIFIER, "speed")],
                body=[
                    ExpressionStmt(
                        expression=FieldSetExpr(
                            object=ThisExpr(keyword=Token(TokenType.THIS, "this")),
                            name=Token(TokenType.IDENTIFIER, "name"),
                            value=VariableExpr(Token(TokenType.IDENTIFIER, "name")),
                        )
                    ),
                    ExpressionStmt(
                        expression=FieldSetExpr(
                            object=ThisExpr(keyword=Token(TokenType.THIS, "this")),
                            name=Token(TokenType.IDENTIFIER, "speed"),
                            value=VariableExpr(Token(TokenType.IDENTIFIER, "speed")),
                        )
                    ),
                ],
            ),
            FunctionStmt(
                name=Token(TokenType.IDENTIFIER, "move"),
                params=[Token(TokenType.IDENTIFIER, "dist")],
                body=[
                    ExpressionStmt(
                        expression=FieldSetExpr(
                            object=ThisExpr(keyword=Token(TokenType.THIS, "this")),
                            name=Token(TokenType.IDENTIFIER, "position"),
                            value=BinaryExpr(
                                left=this_position,
                                operator=Token(TokenType.PLUS, "+"),
                                right=VariableExpr(Token(TokenType.IDENTIFIER, "dist")),
                            ),
                        )
                    ),
                    ReturnStmt(keyword=Token(TokenType.RETURN, "return"), value=this_position),
                ],
            ),
        ],
    )

    assert result[1] == FunctionStmt(
        name=Token(TokenType.IDENTIFIER, "report"),
        params=[Token(TokenType.IDENTIFIER, "r")],
        body=[
            PrintStmt(
                expression=FieldGetExpr(
                    object=VariableExpr(Token(TokenType.IDENTIFIER, "r")),
                    name=Token(TokenType.IDENTIFIER, "name"),
                )
            ),
            ReturnStmt(
                keyword=Token(TokenType.RETURN, "return"),
                value=CallExpr(
                    callee=FieldGetExpr(
                        object=VariableExpr(Token(TokenType.IDENTIFIER, "r")),
                        name=Token(TokenType.IDENTIFIER, "move"),
                    ),
                    paren=Token(TokenType.LEFT_PAREN, "("),
                    arguments=[LiteralExpr(5.0)],
                ),
            ),
        ],
    )

    assert result[2] == VarDeclStmt(
        name=Token(TokenType.IDENTIFIER, "r"),
        initializer=CallExpr(
            callee=VariableExpr(Token(TokenType.IDENTIFIER, "Robot")),
            paren=Token(TokenType.LEFT_PAREN, "("),
            arguments=[LiteralExpr("AndOr"), LiteralExpr(10.0)],
        ),
    )

    assert result[3] == PrintStmt(
        expression=CallExpr(
            callee=VariableExpr(Token(TokenType.IDENTIFIER, "report")),
            paren=Token(TokenType.LEFT_PAREN, "("),
            arguments=[VariableExpr(Token(TokenType.IDENTIFIER, "r"))],
        )
    )


# --- 20단계: 인스턴스/상속 심화 시나리오 ---
#
# AstBuilder는 값을 평가하지 않으므로 "인스턴스가 서로 다르다"는 실제
# 런타임 의미는 검증 대상이 아니다. 대신 여기서 확인하는 것은: 같은
# 클래스를 여러 번 호출(인스턴스화)해도 각 호출이 완전히 독립된
# CallExpr/VariableExpr 트리로 조립되는지, 다단계 상속에서 각 클래스의
# super 호출 체인이 부모를 헷갈리지 않고 정확히 쌓이는지, 그리고 배열/
# 함수 인자처럼 인스턴스가 다른 값과 뒤섞여 오갈 때도 구조가 무너지지
# 않는지다.

def test_step20_three_level_inheritance_chain_of_super_calls():
    """소스코드:
    Class Animal { speak() { print "..."; } }
    Class Dog : Animal { speak() { super.speak(); print "Woof"; } }
    Class Puppy : Dog { speak() { super.speak(); print "Yip"; } }

    3단계 상속에서 각 super가 바로 위 부모(Animal/Dog)를 가리키도록
    ClassStmt.superclass가 매번 정확한 이름으로 구성되는지 확인한다.
    """
    tokens = [
        Token(TokenType.CLASS, "Class"),
        Token(TokenType.IDENTIFIER, "Animal"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.IDENTIFIER, "speak"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.PRINT, "print"),
        Token(TokenType.STRING, '"..."', literal="..."),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.CLASS, "Class"),
        Token(TokenType.IDENTIFIER, "Dog"),
        Token(TokenType.COLON, ":"),
        Token(TokenType.IDENTIFIER, "Animal"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.IDENTIFIER, "speak"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.SUPER, "super"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "speak"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.PRINT, "print"),
        Token(TokenType.STRING, '"Woof"', literal="Woof"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.CLASS, "Class"),
        Token(TokenType.IDENTIFIER, "Puppy"),
        Token(TokenType.COLON, ":"),
        Token(TokenType.IDENTIFIER, "Dog"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.IDENTIFIER, "speak"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.SUPER, "super"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "speak"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.PRINT, "print"),
        Token(TokenType.STRING, '"Yip"', literal="Yip"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    def speak_method(super_call_target, message):
        body = []
        if super_call_target is not None:
            body.append(
                ExpressionStmt(
                    expression=CallExpr(
                        callee=SuperExpr(
                            keyword=Token(TokenType.SUPER, "super"),
                            method=Token(TokenType.IDENTIFIER, "speak"),
                        ),
                        paren=Token(TokenType.LEFT_PAREN, "("),
                        arguments=[],
                    )
                )
            )
        body.append(PrintStmt(expression=LiteralExpr(message)))
        return FunctionStmt(name=Token(TokenType.IDENTIFIER, "speak"), params=[], body=body)

    assert builder.build() == [
        ClassStmt(
            name=Token(TokenType.IDENTIFIER, "Animal"),
            superclass=None,
            methods=[speak_method(None, "...")],
        ),
        ClassStmt(
            name=Token(TokenType.IDENTIFIER, "Dog"),
            superclass=VariableExpr(Token(TokenType.IDENTIFIER, "Animal")),
            methods=[speak_method("Animal", "Woof")],
        ),
        ClassStmt(
            name=Token(TokenType.IDENTIFIER, "Puppy"),
            superclass=VariableExpr(Token(TokenType.IDENTIFIER, "Dog")),
            methods=[speak_method("Dog", "Yip")],
        ),
    ]


def test_step20_two_instances_compared_and_updated_independently():
    """소스코드:
    var a = Robot("A", 5);
    var b = Robot("B", 10);
    print a == b;
    a.speed = a.speed + 1;
    b.speed = b.speed + 2;

    같은 클래스를 두 번 호출해 만든 두 인스턴스가 서로 다른 VariableExpr로
    남고, 각자의 필드 갱신도 서로 간섭하지 않고 독립적으로 조립되는지 확인한다.
    """
    tokens = [
        Token(TokenType.VAR, "var"),
        Token(TokenType.IDENTIFIER, "a"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.IDENTIFIER, "Robot"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.STRING, '"A"', literal="A"),
        Token(TokenType.COMMA, ","),
        Token(TokenType.NUMBER, "5", literal=5.0),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.VAR, "var"),
        Token(TokenType.IDENTIFIER, "b"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.IDENTIFIER, "Robot"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.STRING, '"B"', literal="B"),
        Token(TokenType.COMMA, ","),
        Token(TokenType.NUMBER, "10", literal=10.0),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.PRINT, "print"),
        Token(TokenType.IDENTIFIER, "a"),
        Token(TokenType.EQUAL_EQUAL, "=="),
        Token(TokenType.IDENTIFIER, "b"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.IDENTIFIER, "a"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "speed"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.IDENTIFIER, "a"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "speed"),
        Token(TokenType.PLUS, "+"),
        Token(TokenType.NUMBER, "1", literal=1.0),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.IDENTIFIER, "b"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "speed"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.IDENTIFIER, "b"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "speed"),
        Token(TokenType.PLUS, "+"),
        Token(TokenType.NUMBER, "2", literal=2.0),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    def robot_call(name, speed):
        return CallExpr(
            callee=VariableExpr(Token(TokenType.IDENTIFIER, "Robot")),
            paren=Token(TokenType.LEFT_PAREN, "("),
            arguments=[LiteralExpr(name), LiteralExpr(speed)],
        )

    def speed_increment(var_name, amount):
        return ExpressionStmt(
            expression=FieldSetExpr(
                object=VariableExpr(Token(TokenType.IDENTIFIER, var_name)),
                name=Token(TokenType.IDENTIFIER, "speed"),
                value=BinaryExpr(
                    left=FieldGetExpr(
                        object=VariableExpr(Token(TokenType.IDENTIFIER, var_name)),
                        name=Token(TokenType.IDENTIFIER, "speed"),
                    ),
                    operator=Token(TokenType.PLUS, "+"),
                    right=LiteralExpr(amount),
                ),
            )
        )

    assert builder.build() == [
        VarDeclStmt(name=Token(TokenType.IDENTIFIER, "a"), initializer=robot_call("A", 5.0)),
        VarDeclStmt(name=Token(TokenType.IDENTIFIER, "b"), initializer=robot_call("B", 10.0)),
        PrintStmt(
            expression=BinaryExpr(
                left=VariableExpr(Token(TokenType.IDENTIFIER, "a")),
                operator=Token(TokenType.EQUAL_EQUAL, "=="),
                right=VariableExpr(Token(TokenType.IDENTIFIER, "b")),
            )
        ),
        speed_increment("a", 1.0),
        speed_increment("b", 2.0),
    ]


def test_step20_function_compares_two_instance_parameters_and_returns_one():
    """소스코드:
    Func fasterOf(a, b) {
        if (a.speed > b.speed) {
            return a;
        }
        return b;
    }

    print fasterOf(r1, r2).name;

    함수 파라미터로 들어온 두 인스턴스의 같은 이름 필드(speed)를 비교해
    그 중 하나를 그대로 반환하고, 호출부에서 반환값에 바로 필드 접근을
    체이닝하는 형태를 검증한다.
    """
    tokens = [
        Token(TokenType.FUNC, "Func"),
        Token(TokenType.IDENTIFIER, "fasterOf"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.IDENTIFIER, "a"),
        Token(TokenType.COMMA, ","),
        Token(TokenType.IDENTIFIER, "b"),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.IF, "if"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.IDENTIFIER, "a"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "speed"),
        Token(TokenType.GREATER, ">"),
        Token(TokenType.IDENTIFIER, "b"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "speed"),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.RETURN, "return"),
        Token(TokenType.IDENTIFIER, "a"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.RETURN, "return"),
        Token(TokenType.IDENTIFIER, "b"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.PRINT, "print"),
        Token(TokenType.IDENTIFIER, "fasterOf"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.IDENTIFIER, "r1"),
        Token(TokenType.COMMA, ","),
        Token(TokenType.IDENTIFIER, "r2"),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "name"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        FunctionStmt(
            name=Token(TokenType.IDENTIFIER, "fasterOf"),
            params=[Token(TokenType.IDENTIFIER, "a"), Token(TokenType.IDENTIFIER, "b")],
            body=[
                IfStmt(
                    condition=BinaryExpr(
                        left=FieldGetExpr(
                            object=VariableExpr(Token(TokenType.IDENTIFIER, "a")),
                            name=Token(TokenType.IDENTIFIER, "speed"),
                        ),
                        operator=Token(TokenType.GREATER, ">"),
                        right=FieldGetExpr(
                            object=VariableExpr(Token(TokenType.IDENTIFIER, "b")),
                            name=Token(TokenType.IDENTIFIER, "speed"),
                        ),
                    ),
                    then_branch=BlockStmt(
                        statements=[
                            ReturnStmt(
                                keyword=Token(TokenType.RETURN, "return"),
                                value=VariableExpr(Token(TokenType.IDENTIFIER, "a")),
                            )
                        ]
                    ),
                    else_branch=None,
                ),
                ReturnStmt(
                    keyword=Token(TokenType.RETURN, "return"),
                    value=VariableExpr(Token(TokenType.IDENTIFIER, "b")),
                ),
            ],
        ),
        PrintStmt(
            expression=FieldGetExpr(
                object=CallExpr(
                    callee=VariableExpr(Token(TokenType.IDENTIFIER, "fasterOf")),
                    paren=Token(TokenType.LEFT_PAREN, "("),
                    arguments=[
                        VariableExpr(Token(TokenType.IDENTIFIER, "r1")),
                        VariableExpr(Token(TokenType.IDENTIFIER, "r2")),
                    ],
                ),
                name=Token(TokenType.IDENTIFIER, "name"),
            )
        ),
    ]


def test_step20_array_of_instances_indexed_and_field_accessed():
    """소스코드:
    var team = Array(2);
    team[0] = Robot("A", 5);
    team[1] = Robot("B", 10);
    print team[0].name;

    배열의 각 칸에 서로 다른 인스턴스를 저장한 뒤, 인덱스로 꺼낸 값에
    바로 필드 접근을 체이닝하는 조합(IndexGetExpr -> FieldGetExpr)을 검증한다.
    """
    tokens = [
        Token(TokenType.VAR, "var"),
        Token(TokenType.IDENTIFIER, "team"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.IDENTIFIER, "Array"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.NUMBER, "2", literal=2.0),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.IDENTIFIER, "team"),
        Token(TokenType.LEFT_BRACKET, "["),
        Token(TokenType.NUMBER, "0", literal=0.0),
        Token(TokenType.RIGHT_BRACKET, "]"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.IDENTIFIER, "Robot"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.STRING, '"A"', literal="A"),
        Token(TokenType.COMMA, ","),
        Token(TokenType.NUMBER, "5", literal=5.0),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.IDENTIFIER, "team"),
        Token(TokenType.LEFT_BRACKET, "["),
        Token(TokenType.NUMBER, "1", literal=1.0),
        Token(TokenType.RIGHT_BRACKET, "]"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.IDENTIFIER, "Robot"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.STRING, '"B"', literal="B"),
        Token(TokenType.COMMA, ","),
        Token(TokenType.NUMBER, "10", literal=10.0),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.PRINT, "print"),
        Token(TokenType.IDENTIFIER, "team"),
        Token(TokenType.LEFT_BRACKET, "["),
        Token(TokenType.NUMBER, "0", literal=0.0),
        Token(TokenType.RIGHT_BRACKET, "]"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "name"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    def robot_call(name, speed):
        return CallExpr(
            callee=VariableExpr(Token(TokenType.IDENTIFIER, "Robot")),
            paren=Token(TokenType.LEFT_PAREN, "("),
            arguments=[LiteralExpr(name), LiteralExpr(speed)],
        )

    def team_slot_write(index, value):
        return ExpressionStmt(
            expression=IndexSetExpr(
                object=VariableExpr(Token(TokenType.IDENTIFIER, "team")),
                bracket=Token(TokenType.LEFT_BRACKET, "["),
                index=LiteralExpr(index),
                value=value,
            )
        )

    assert builder.build() == [
        VarDeclStmt(
            name=Token(TokenType.IDENTIFIER, "team"),
            initializer=CallExpr(
                callee=VariableExpr(Token(TokenType.IDENTIFIER, "Array")),
                paren=Token(TokenType.LEFT_PAREN, "("),
                arguments=[LiteralExpr(2.0)],
            ),
        ),
        team_slot_write(0.0, robot_call("A", 5.0)),
        team_slot_write(1.0, robot_call("B", 10.0)),
        PrintStmt(
            expression=FieldGetExpr(
                object=IndexGetExpr(
                    object=VariableExpr(Token(TokenType.IDENTIFIER, "team")),
                    bracket=Token(TokenType.LEFT_BRACKET, "["),
                    index=LiteralExpr(0.0),
                ),
                name=Token(TokenType.IDENTIFIER, "name"),
            )
        ),
    ]


def test_step20_two_different_class_instances_call_overridden_method():
    """소스코드:
    Class Robot { speak() { print "beep"; } }
    Class SpeedRobot : Robot { speak() { super.speak(); print "zoom"; } }

    var r = Robot();
    var sr = SpeedRobot();
    r.speak();
    sr.speak();

    같은 이름의 메서드(speak)가 부모/자식 클래스에 각각 독립적으로
    선언되고, 서로 다른 클래스의 인스턴스가 각자 자기 클래스의 메서드
    호출로 파싱되는지 확인한다 (실제 어떤 speak가 실행될지는 Executor의
    상속 체인 탐색 몫이고, 여기서는 AST 구조만 검증한다).
    """
    tokens = [
        Token(TokenType.CLASS, "Class"),
        Token(TokenType.IDENTIFIER, "Robot"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.IDENTIFIER, "speak"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.PRINT, "print"),
        Token(TokenType.STRING, '"beep"', literal="beep"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.CLASS, "Class"),
        Token(TokenType.IDENTIFIER, "SpeedRobot"),
        Token(TokenType.COLON, ":"),
        Token(TokenType.IDENTIFIER, "Robot"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.IDENTIFIER, "speak"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.SUPER, "super"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "speak"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.PRINT, "print"),
        Token(TokenType.STRING, '"zoom"', literal="zoom"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.VAR, "var"),
        Token(TokenType.IDENTIFIER, "r"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.IDENTIFIER, "Robot"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.VAR, "var"),
        Token(TokenType.IDENTIFIER, "sr"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.IDENTIFIER, "SpeedRobot"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.IDENTIFIER, "r"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "speak"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.IDENTIFIER, "sr"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "speak"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    def instance_call(class_name):
        return CallExpr(
            callee=VariableExpr(Token(TokenType.IDENTIFIER, class_name)),
            paren=Token(TokenType.LEFT_PAREN, "("),
            arguments=[],
        )

    def speak_call(var_name):
        return ExpressionStmt(
            expression=CallExpr(
                callee=FieldGetExpr(
                    object=VariableExpr(Token(TokenType.IDENTIFIER, var_name)),
                    name=Token(TokenType.IDENTIFIER, "speak"),
                ),
                paren=Token(TokenType.LEFT_PAREN, "("),
                arguments=[],
            )
        )

    assert builder.build() == [
        ClassStmt(
            name=Token(TokenType.IDENTIFIER, "Robot"),
            superclass=None,
            methods=[
                FunctionStmt(
                    name=Token(TokenType.IDENTIFIER, "speak"),
                    params=[],
                    body=[PrintStmt(expression=LiteralExpr("beep"))],
                )
            ],
        ),
        ClassStmt(
            name=Token(TokenType.IDENTIFIER, "SpeedRobot"),
            superclass=VariableExpr(Token(TokenType.IDENTIFIER, "Robot")),
            methods=[
                FunctionStmt(
                    name=Token(TokenType.IDENTIFIER, "speak"),
                    params=[],
                    body=[
                        ExpressionStmt(
                            expression=CallExpr(
                                callee=SuperExpr(
                                    keyword=Token(TokenType.SUPER, "super"),
                                    method=Token(TokenType.IDENTIFIER, "speak"),
                                ),
                                paren=Token(TokenType.LEFT_PAREN, "("),
                                arguments=[],
                            )
                        ),
                        PrintStmt(expression=LiteralExpr("zoom")),
                    ],
                )
            ],
        ),
        VarDeclStmt(name=Token(TokenType.IDENTIFIER, "r"), initializer=instance_call("Robot")),
        VarDeclStmt(name=Token(TokenType.IDENTIFIER, "sr"), initializer=instance_call("SpeedRobot")),
        speak_call("r"),
        speak_call("sr"),
    ]
