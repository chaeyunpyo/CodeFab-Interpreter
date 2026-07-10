import pytest

from assembler import Assembler, ExpressionTooDeeplyNestedError
from nodes.tokens import Token
from nodes.token_type import TokenType
from nodes import *


# --- ast 속성은 읽기 전용 (execute()를 통해서만 채워져야 함) ---

def test_assembler_ast_property_cannot_be_set_directly():
    sut = Assembler("print 1;")

    with pytest.raises(Exception):
        sut.ast = []


# --- 산술 연산자 우선순위 (곱셈/나눗셈이 덧셈/뺄셈보다 먼저) ---

@pytest.mark.parametrize(
    "source, expected",
    [
        (
            "print 1 + 2 * 3;",
            [
                PrintStmt(
                    expression=BinaryExpr(
                        left=LiteralExpr(1.0),
                        operator=Token(TokenType.PLUS, "+"),
                        right=BinaryExpr(
                            left=LiteralExpr(2.0),
                            operator=Token(TokenType.STAR, "*"),
                            right=LiteralExpr(3.0),
                        ),
                    )
                )
            ],
        ),
        (
            "print (1 + 2) * 3;",
            [
                PrintStmt(
                    expression=BinaryExpr(
                        left=GroupingExpr(
                            expression=BinaryExpr(
                                left=LiteralExpr(1.0),
                                operator=Token(TokenType.PLUS, "+"),
                                right=LiteralExpr(2.0),
                            )
                        ),
                        operator=Token(TokenType.STAR, "*"),
                        right=LiteralExpr(3.0),
                    )
                )
            ],
        ),
        (
            "print 10 - 4 - 3;",
            [
                PrintStmt(
                    expression=BinaryExpr(
                        left=BinaryExpr(
                            left=LiteralExpr(10.0),
                            operator=Token(TokenType.MINUS, "-"),
                            right=LiteralExpr(4.0),
                        ),
                        operator=Token(TokenType.MINUS, "-"),
                        right=LiteralExpr(3.0),
                    )
                )
            ],
        ),
        (
            "print 8 / 2 / 2;",
            [
                PrintStmt(
                    expression=BinaryExpr(
                        left=BinaryExpr(
                            left=LiteralExpr(8.0),
                            operator=Token(TokenType.SLASH, "/"),
                            right=LiteralExpr(2.0),
                        ),
                        operator=Token(TokenType.SLASH, "/"),
                        right=LiteralExpr(2.0),
                    )
                )
            ],
        ),
        (
            "print -3 + 2;",
            [
                PrintStmt(
                    expression=BinaryExpr(
                        left=UnaryExpr(
                            operator=Token(TokenType.MINUS, "-"),
                            right=LiteralExpr(3.0),
                        ),
                        operator=Token(TokenType.PLUS, "+"),
                        right=LiteralExpr(2.0),
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


# --- 단항 연산자 (PDF p.36: !, +, -) ---

@pytest.mark.parametrize(
    "source, operator_type, operator_lexeme",
    [
        ("print +3;", TokenType.PLUS, "+"),
        ("print -3;", TokenType.MINUS, "-"),
        ("print !true;", TokenType.BANG, "!"),
    ],
)
def test_assembler_unary_operators(source, operator_type, operator_lexeme):
    sut = Assembler(source)

    sut.execute()

    literal = True if operator_type == TokenType.BANG else 3.0
    assert sut.ast == [
        PrintStmt(
            expression=UnaryExpr(
                operator=Token(operator_type, operator_lexeme),
                right=LiteralExpr(literal),
            )
        )
    ]


def test_assembler_unary_plus_does_not_change_precedence():
    """소스코드: print 1 + +2;"""
    sut = Assembler("print 1 + +2;")

    sut.execute()

    assert sut.ast == [
        PrintStmt(
            expression=BinaryExpr(
                left=LiteralExpr(1.0),
                operator=Token(TokenType.PLUS, "+"),
                right=UnaryExpr(
                    operator=Token(TokenType.PLUS, "+"),
                    right=LiteralExpr(2.0),
                ),
            )
        )
    ]


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
        PrintStmt(
            expression=BinaryExpr(
                left=LiteralExpr(left),
                operator=Token(operator_type, operator_lexeme),
                right=LiteralExpr(right),
            )
        )
    ]


# --- 문자열 연결 (+) ---

def test_assembler_string_concatenation():
    source = 'print "Hello, " + "CodeFab!";'
    sut = Assembler(source)

    sut.execute()

    assert sut.ast == [
        PrintStmt(
            expression=BinaryExpr(
                left=LiteralExpr("Hello, "),
                operator=Token(TokenType.PLUS, "+"),
                right=LiteralExpr("CodeFab!"),
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

    assert sut.ast == [PrintStmt(expression=LiteralExpr(literal))]


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

    assert sut.ast == [PrintStmt(expression=LiteralExpr(literal))]


# --- 변수 선언 / 재할당 / 블록 스코프 / shadowing ---

def test_assembler_variable_declaration_and_usage():
    source = """
    var a = 10;
    var b = 20;
    print a + b;
    """
    sut = Assembler(source)

    sut.execute()

    assert sut.ast == [
        VarDeclStmt(name=Token(TokenType.IDENTIFIER, "a", line=2), initializer=LiteralExpr(10.0)),
        VarDeclStmt(name=Token(TokenType.IDENTIFIER, "b", line=3), initializer=LiteralExpr(20.0)),
        PrintStmt(
            expression=BinaryExpr(
                left=VariableExpr(Token(TokenType.IDENTIFIER, "a", line=4)),
                operator=Token(TokenType.PLUS, "+", line=4),
                right=VariableExpr(Token(TokenType.IDENTIFIER, "b", line=4)),
            )
        ),
    ]


def test_assembler_variable_reassignment():
    source = """
    var a = 10;
    a = a + 5;
    print a;
    """
    sut = Assembler(source)

    sut.execute()

    assert sut.ast == [
        VarDeclStmt(name=Token(TokenType.IDENTIFIER, "a", line=2), initializer=LiteralExpr(10.0)),
        ExpressionStmt(
            expression=AssignExpr(
                name=Token(TokenType.IDENTIFIER, "a", line=3),
                value=BinaryExpr(
                    left=VariableExpr(Token(TokenType.IDENTIFIER, "a", line=3)),
                    operator=Token(TokenType.PLUS, "+", line=3),
                    right=LiteralExpr(5.0),
                ),
            )
        ),
        PrintStmt(expression=VariableExpr(Token(TokenType.IDENTIFIER, "a", line=4))),
    ]


def test_assembler_block_scope_and_shadowing():
    source = """
    var x = "global";
    {
      var x = "inner";
      print x;
    }
    print x;
    """
    sut = Assembler(source)

    sut.execute()

    assert sut.ast == [
        VarDeclStmt(name=Token(TokenType.IDENTIFIER, "x", line=2), initializer=LiteralExpr("global")),
        BlockStmt(
            statements=[
                VarDeclStmt(name=Token(TokenType.IDENTIFIER, "x", line=4), initializer=LiteralExpr("inner")),
                PrintStmt(expression=VariableExpr(Token(TokenType.IDENTIFIER, "x", line=5))),
            ]
        ),
        PrintStmt(expression=VariableExpr(Token(TokenType.IDENTIFIER, "x", line=7))),
    ]


def test_assembler_inner_block_modifies_outer_variable():
    source = """
    var count = 0;
    {
      count = count + 1;
    }
    print count;
    """
    sut = Assembler(source)

    sut.execute()

    assert sut.ast == [
        VarDeclStmt(name=Token(TokenType.IDENTIFIER, "count", line=2), initializer=LiteralExpr(0.0)),
        BlockStmt(
            statements=[
                ExpressionStmt(
                    expression=AssignExpr(
                        name=Token(TokenType.IDENTIFIER, "count", line=4),
                        value=BinaryExpr(
                            left=VariableExpr(Token(TokenType.IDENTIFIER, "count", line=4)),
                            operator=Token(TokenType.PLUS, "+", line=4),
                            right=LiteralExpr(1.0),
                        ),
                    )
                )
            ]
        ),
        PrintStmt(expression=VariableExpr(Token(TokenType.IDENTIFIER, "count", line=6))),
    ]


def test_assembler_nested_scope_resolution():
    source = """
    var outer = "A";
    {
      var inner = "B";
      {
        print outer + inner;
      }
    }
    """
    sut = Assembler(source)

    sut.execute()

    assert sut.ast == [
        VarDeclStmt(name=Token(TokenType.IDENTIFIER, "outer", line=2), initializer=LiteralExpr("A")),
        BlockStmt(
            statements=[
                VarDeclStmt(name=Token(TokenType.IDENTIFIER, "inner", line=4), initializer=LiteralExpr("B")),
                BlockStmt(
                    statements=[
                        PrintStmt(
                            expression=BinaryExpr(
                                left=VariableExpr(Token(TokenType.IDENTIFIER, "outer", line=6)),
                                operator=Token(TokenType.PLUS, "+", line=6),
                                right=VariableExpr(Token(TokenType.IDENTIFIER, "inner", line=6)),
                            )
                        )
                    ]
                ),
            ]
        ),
    ]


# --- 제어 흐름: if / else, for ---

def test_assembler_if_without_else():
    source = 'if (true) print "bbq";'
    sut = Assembler(source)

    sut.execute()

    assert sut.ast == [
        IfStmt(
            condition=LiteralExpr(True),
            then_branch=PrintStmt(expression=LiteralExpr("bbq")),
            else_branch=None,
        )
    ]


def test_assembler_if_else():
    source = 'if (false) print "no"; else print "kfc";'
    sut = Assembler(source)

    sut.execute()

    assert sut.ast == [
        IfStmt(
            condition=LiteralExpr(False),
            then_branch=PrintStmt(expression=LiteralExpr("no")),
            else_branch=PrintStmt(expression=LiteralExpr("kfc")),
        )
    ]


def test_assembler_dangling_else_binds_to_nearest_if():
    source = """
    if (true)
    {
      if (false) print "kfc";
      else print "bbq";
    }
    """
    sut = Assembler(source)

    sut.execute()

    assert sut.ast == [
        IfStmt(
            condition=LiteralExpr(True),
            then_branch=BlockStmt(
                statements=[
                    IfStmt(
                        condition=LiteralExpr(False),
                        then_branch=PrintStmt(expression=LiteralExpr("kfc")),
                        else_branch=PrintStmt(expression=LiteralExpr("bbq")),
                    )
                ]
            ),
            else_branch=None,
        )
    ]


def test_assembler_if_else_nested_block():
    source = """
    if (true)
    {
      print 10 + 20;
    }
    else
    {
      print 30 + 40;
    }
    """
    sut = Assembler(source)

    sut.execute()

    assert sut.ast == [
        IfStmt(
            condition=LiteralExpr(True),
            then_branch=BlockStmt(
                statements=[
                    PrintStmt(
                        expression=BinaryExpr(
                            left=LiteralExpr(10.0),
                            operator=Token(TokenType.PLUS, "+", line=4),
                            right=LiteralExpr(20.0),
                        )
                    )
                ]
            ),
            else_branch=BlockStmt(
                statements=[
                    PrintStmt(
                        expression=BinaryExpr(
                            left=LiteralExpr(30.0),
                            operator=Token(TokenType.PLUS, "+", line=8),
                            right=LiteralExpr(40.0),
                        )
                    )
                ]
            ),
        )
    ]


def test_assembler_for_loop():
    source = "for (var j = 0; j < 3; j = j + 1) { print j; }"
    sut = Assembler(source)

    sut.execute()

    assert sut.ast == [
        ForStmt(
            initializer=VarDeclStmt(name=Token(TokenType.IDENTIFIER, "j"), initializer=LiteralExpr(0.0)),
            condition=BinaryExpr(
                left=VariableExpr(Token(TokenType.IDENTIFIER, "j")),
                operator=Token(TokenType.LESS, "<"),
                right=LiteralExpr(3.0),
            ),
            increment=AssignExpr(
                name=Token(TokenType.IDENTIFIER, "j"),
                value=BinaryExpr(
                    left=VariableExpr(Token(TokenType.IDENTIFIER, "j")),
                    operator=Token(TokenType.PLUS, "+"),
                    right=LiteralExpr(1.0),
                ),
            ),
            body=BlockStmt(
                statements=[PrintStmt(expression=VariableExpr(Token(TokenType.IDENTIFIER, "j")))]
            ),
        )
    ]


# --- 재귀 하강 파싱 한도 (파이썬 RecursionError가 새어나오면 안 됨) ---

def test_assembler_deeply_nested_expression_raises_expression_too_deeply_nested_error():
    """재귀 하강 파서는 그룹핑 표현식을 한 단계 내려갈 때마다 파이썬 함수
    호출을 여러 겹 소비하므로, 괄호를 극단적으로 깊게 중첩하면(100단계
    안팎) 파이썬 기본 재귀 한도를 넘어 RecursionError가 난다.
    AstBuilder.build()가 이를 잡아 ExpressionTooDeeplyNestedError로 감싸야
    한다 - 파이썬 RecursionError가 그대로 새어나오면 안 된다.
    """
    depth = 100
    source = f"print {'(' * depth}1{')' * depth};"
    sut = Assembler(source)

    with pytest.raises(ExpressionTooDeeplyNestedError):
        sut.execute()


def test_assembler_for_loop_without_initialization():
    source = "for (; j < 3; j = j + 1) { print j; }"
    sut = Assembler(source)

    sut.execute()

    assert sut.ast == [
        ForStmt(
            initializer=None,
            condition=BinaryExpr(
                left=VariableExpr(Token(TokenType.IDENTIFIER, "j")),
                operator=Token(TokenType.LESS, "<"),
                right=LiteralExpr(3.0),
            ),
            increment=AssignExpr(
                name=Token(TokenType.IDENTIFIER, "j"),
                value=BinaryExpr(
                    left=VariableExpr(Token(TokenType.IDENTIFIER, "j")),
                    operator=Token(TokenType.PLUS, "+"),
                    right=LiteralExpr(1.0),
                ),
            ),
            body=BlockStmt(
                statements=[PrintStmt(expression=VariableExpr(Token(TokenType.IDENTIFIER, "j")))]
            ),
        )
    ]
