import pytest
import nodes

from assembler import Assembler
from nodes.tokens import Token
from nodes.token_type import TokenType


# --- 산술 연산자 우선순위 (곱셈/나눗셈이 덧셈/뺄셈보다 먼저) ---

@pytest.mark.parametrize(
    "source, expected",
    [
        (
            "print 1 + 2 * 3;",
            [
                nodes.PrintStmt(
                    expression=nodes.BinaryExpr(
                        left=nodes.LiteralExpr(1.0),
                        operator=Token(TokenType.PLUS, "+"),
                        right=nodes.BinaryExpr(
                            left=nodes.LiteralExpr(2.0),
                            operator=Token(TokenType.STAR, "*"),
                            right=nodes.LiteralExpr(3.0),
                        ),
                    )
                )
            ],
        ),
        (
            "print (1 + 2) * 3;",
            [
                nodes.PrintStmt(
                    expression=nodes.BinaryExpr(
                        left=nodes.GroupingExpr(
                            expression=nodes.BinaryExpr(
                                left=nodes.LiteralExpr(1.0),
                                operator=Token(TokenType.PLUS, "+"),
                                right=nodes.LiteralExpr(2.0),
                            )
                        ),
                        operator=Token(TokenType.STAR, "*"),
                        right=nodes.LiteralExpr(3.0),
                    )
                )
            ],
        ),
        (
            "print 10 - 4 - 3;",
            [
                nodes.PrintStmt(
                    expression=nodes.BinaryExpr(
                        left=nodes.BinaryExpr(
                            left=nodes.LiteralExpr(10.0),
                            operator=Token(TokenType.MINUS, "-"),
                            right=nodes.LiteralExpr(4.0),
                        ),
                        operator=Token(TokenType.MINUS, "-"),
                        right=nodes.LiteralExpr(3.0),
                    )
                )
            ],
        ),
        (
            "print 8 / 2 / 2;",
            [
                nodes.PrintStmt(
                    expression=nodes.BinaryExpr(
                        left=nodes.BinaryExpr(
                            left=nodes.LiteralExpr(8.0),
                            operator=Token(TokenType.SLASH, "/"),
                            right=nodes.LiteralExpr(2.0),
                        ),
                        operator=Token(TokenType.SLASH, "/"),
                        right=nodes.LiteralExpr(2.0),
                    )
                )
            ],
        ),
        (
            "print -3 + 2;",
            [
                nodes.PrintStmt(
                    expression=nodes.BinaryExpr(
                        left=nodes.UnaryExpr(
                            operator=Token(TokenType.MINUS, "-"),
                            right=nodes.LiteralExpr(3.0),
                        ),
                        operator=Token(TokenType.PLUS, "+"),
                        right=nodes.LiteralExpr(2.0),
                    )
                )
            ],
        ),
    ],
)
def test_assembler_arithmetic_precedence(source, expected):
    sut = Assembler(source)

    sut.execute()

    assert sut.ast == expected


# --- 비교 / 동등성 ---

@pytest.mark.parametrize(
    "source, operator_type, operator_lexeme, left, right",
    [
        ("print 1 < 2;", TokenType.LESS, "<", 1.0, 2.0),
        ("print 3 > 5;", TokenType.GREATER, ">", 3.0, 5.0),
    ],
)
def test_assembler_comparison(source, operator_type, operator_lexeme, left, right):
    sut = Assembler(source)

    sut.execute()

    assert sut.ast == [
        nodes.PrintStmt(
            expression=nodes.BinaryExpr(
                left=nodes.LiteralExpr(left),
                operator=Token(operator_type, operator_lexeme),
                right=nodes.LiteralExpr(right),
            )
        )
    ]


# --- 문자열 연결 (+) ---

def test_assembler_string_concatenation():
    source = 'print "Hello, " + "CodeFab!";'
    sut = Assembler(source)

    sut.execute()

    assert sut.ast == [
        nodes.PrintStmt(
            expression=nodes.BinaryExpr(
                left=nodes.LiteralExpr("Hello, "),
                operator=Token(TokenType.PLUS, "+"),
                right=nodes.LiteralExpr("CodeFab!"),
            )
        )
    ]


# --- 숫자 출력 포맷 (정수는 .0 없이 출력되어야 함) ---

@pytest.mark.parametrize(
    "source, literal",
    [
        ("print 5;", 5.0),
        ("print 5.0;", 5.0),
        ("print 3.14;", 3.14),
    ],
)
def test_assembler_number_output_format(source, literal):
    sut = Assembler(source)

    sut.execute()

    assert sut.ast == [nodes.PrintStmt(expression=nodes.LiteralExpr(literal))]


# --- boolean 리터럴 출력 ---

@pytest.mark.parametrize(
    "source, literal",
    [
        ("print true;", True),
        ("print false;", False),
    ],
)
def test_assembler_boolean_literal_output(source, literal):
    sut = Assembler(source)

    sut.execute()

    assert sut.ast == [nodes.PrintStmt(expression=nodes.LiteralExpr(literal))]
