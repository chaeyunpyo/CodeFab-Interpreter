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


