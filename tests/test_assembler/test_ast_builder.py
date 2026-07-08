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
