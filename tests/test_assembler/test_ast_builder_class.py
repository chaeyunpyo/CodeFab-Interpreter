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




# --- 22단계: instanceof 연산자 파싱 (요구사항_정리/class.md) ---
#
# instanceof는 비교 연산자와 같은 우선순위 단계에 있지만, 우변이 climb된
# 표현식이 아니라 클래스 이름 하나(IDENTIFIER)라는 점이 다르다. 그래서
# _climb()의 기본 처리 대신 _infix_factories에 등록된 전용 조립 방법
# (_finish_instanceof)을 거친다.

def test_step22_instanceof_basic():
    """소스코드: w instanceof Robot;"""
    tokens = [
        Token(TokenType.IDENTIFIER, "w"),
        Token(TokenType.INSTANCEOF, "instanceof"),
        Token(TokenType.IDENTIFIER, "Robot"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        ExpressionStmt(
            expression=InstanceOfExpr(
                object=VariableExpr(Token(TokenType.IDENTIFIER, "w")),
                keyword=Token(TokenType.INSTANCEOF, "instanceof"),
                class_name=VariableExpr(Token(TokenType.IDENTIFIER, "Robot")),
            )
        )
    ]


def test_step22_instanceof_used_as_if_condition():
    """소스코드: if (w instanceof Robot) { print w; }"""
    tokens = [
        Token(TokenType.IF, "if"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.IDENTIFIER, "w"),
        Token(TokenType.INSTANCEOF, "instanceof"),
        Token(TokenType.IDENTIFIER, "Robot"),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.PRINT, "print"),
        Token(TokenType.IDENTIFIER, "w"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        IfStmt(
            condition=InstanceOfExpr(
                object=VariableExpr(Token(TokenType.IDENTIFIER, "w")),
                keyword=Token(TokenType.INSTANCEOF, "instanceof"),
                class_name=VariableExpr(Token(TokenType.IDENTIFIER, "Robot")),
            ),
            then_branch=BlockStmt(
                statements=[PrintStmt(expression=VariableExpr(Token(TokenType.IDENTIFIER, "w")))]
            ),
            else_branch=None,
        )
    ]


def test_step22_instanceof_binds_tighter_than_and():
    """소스코드: w instanceof Robot and w.speed > 0;

    instanceof는 비교 연산자와 같은 단계(and보다 우선순위가 높음)라
    LogicalExpr의 left/right 각각이 InstanceOfExpr/BinaryExpr로 먼저
    묶이고, 그 다음에 and가 둘을 묶어야 한다.
    """
    tokens = [
        Token(TokenType.IDENTIFIER, "w"),
        Token(TokenType.INSTANCEOF, "instanceof"),
        Token(TokenType.IDENTIFIER, "Robot"),
        Token(TokenType.AND, "and"),
        Token(TokenType.IDENTIFIER, "w"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "speed"),
        Token(TokenType.GREATER, ">"),
        Token(TokenType.NUMBER, "0", literal=0.0),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        ExpressionStmt(
            expression=LogicalExpr(
                left=InstanceOfExpr(
                    object=VariableExpr(Token(TokenType.IDENTIFIER, "w")),
                    keyword=Token(TokenType.INSTANCEOF, "instanceof"),
                    class_name=VariableExpr(Token(TokenType.IDENTIFIER, "Robot")),
                ),
                operator=Token(TokenType.AND, "and"),
                right=BinaryExpr(
                    left=FieldGetExpr(
                        object=VariableExpr(Token(TokenType.IDENTIFIER, "w")),
                        name=Token(TokenType.IDENTIFIER, "speed"),
                    ),
                    operator=Token(TokenType.GREATER, ">"),
                    right=LiteralExpr(0.0),
                ),
            )
        )
    ]


def test_step22_instanceof_negated_with_grouping_and_unary_bang():
    """소스코드: !(w instanceof Robot);"""
    tokens = [
        Token(TokenType.BANG, "!"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.IDENTIFIER, "w"),
        Token(TokenType.INSTANCEOF, "instanceof"),
        Token(TokenType.IDENTIFIER, "Robot"),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        ExpressionStmt(
            expression=UnaryExpr(
                operator=Token(TokenType.BANG, "!"),
                right=GroupingExpr(
                    expression=InstanceOfExpr(
                        object=VariableExpr(Token(TokenType.IDENTIFIER, "w")),
                        keyword=Token(TokenType.INSTANCEOF, "instanceof"),
                        class_name=VariableExpr(Token(TokenType.IDENTIFIER, "Robot")),
                    )
                ),
            )
        )
    ]


def test_step22_instanceof_missing_class_name_raises_missing_token_error():
    """소스코드: w instanceof;  (클래스 이름 누락)"""
    tokens = [
        Token(TokenType.IDENTIFIER, "w"),
        Token(TokenType.INSTANCEOF, "instanceof"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    with pytest.raises(MissingTokenError) as excinfo:
        builder.build()

    assert "Expected class name after 'instanceof'" in str(excinfo.value)
    assert excinfo.value.token == Token(TokenType.SEMICOLON, ";")


def test_step22_instanceof_class_name_not_identifier_raises_missing_token_error():
    """소스코드: w instanceof 5;  (클래스 이름 자리에 식별자가 아닌 값)"""
    tokens = [
        Token(TokenType.IDENTIFIER, "w"),
        Token(TokenType.INSTANCEOF, "instanceof"),
        Token(TokenType.NUMBER, "5", literal=5.0),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    with pytest.raises(MissingTokenError) as excinfo:
        builder.build()

    assert "Expected class name after 'instanceof'" in str(excinfo.value)
    assert excinfo.value.token == Token(TokenType.NUMBER, "5", literal=5.0)


def test_step22_instanceof_truncated_raises_missing_token_error():
    """소스코드: w instanceof  (클래스 이름 없이 곧바로 끝남)"""
    tokens = [
        Token(TokenType.IDENTIFIER, "w"),
        Token(TokenType.INSTANCEOF, "instanceof"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    with pytest.raises(MissingTokenError) as excinfo:
        builder.build()

    assert "Expected class name after 'instanceof'" in str(excinfo.value)
    assert excinfo.value.token == Token(TokenType.EOF, "")


def test_step22_instanceof_with_literal_left_operand_still_parses():
    """소스코드: 5 instanceof SpeedRobot;

    좌변이 인스턴스가 아닌 값(숫자 리터럴)이어도 AstBuilder는 문법
    구조만 보고 그대로 InstanceOfExpr로 조립해야 한다. 좌변이 실제
    인스턴스인지, 어떤 클래스와 비교되는지는 실행 시점에만 확정되는
    값 검사라 Checker/Executor 몫이지 AstBuilder가 거를 대상이 아니다.
    """
    tokens = [
        Token(TokenType.NUMBER, "5", literal=5.0),
        Token(TokenType.INSTANCEOF, "instanceof"),
        Token(TokenType.IDENTIFIER, "SpeedRobot"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        ExpressionStmt(
            expression=InstanceOfExpr(
                object=LiteralExpr(5.0),
                keyword=Token(TokenType.INSTANCEOF, "instanceof"),
                class_name=VariableExpr(Token(TokenType.IDENTIFIER, "SpeedRobot")),
            )
        )
    ]


def test_step22_instanceof_reserved_keyword_as_class_name_raises_missing_token_error():
    """소스코드: w instanceof var;  (클래스 이름 자리에 예약어를 사용)

    'var'는 키워드 토큰(VAR)으로 토큰화되어 IDENTIFIER가 아니므로,
    변수/별칭 이름 자리와 마찬가지로 클래스 이름 자리에도 쓸 수 없다.
    """
    tokens = [
        Token(TokenType.IDENTIFIER, "w"),
        Token(TokenType.INSTANCEOF, "instanceof"),
        Token(TokenType.VAR, "var"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    with pytest.raises(MissingTokenError) as excinfo:
        builder.build()

    assert "Expected class name after 'instanceof'" in str(excinfo.value)
    assert excinfo.value.token == Token(TokenType.VAR, "var")


def test_step22_instanceof_qualified_class_name_raises_missing_token_error():
    """소스코드: w instanceof Robot.Sub;  (점으로 이어진 이름은 지원하지 않음)

    클래스 이름 자리는 IDENTIFIER 하나만 소비하므로, `Robot`까지만
    class_name으로 먹고 뒤에 남은 `.Sub`는 instanceof 파싱이 끝난
    뒤에도 그대로 남는다. 그 뒤 문장이 세미콜론을 기대하는 자리에서
    `.`을 만나 실패해야 한다.
    """
    tokens = [
        Token(TokenType.IDENTIFIER, "w"),
        Token(TokenType.INSTANCEOF, "instanceof"),
        Token(TokenType.IDENTIFIER, "Robot"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "Sub"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    with pytest.raises(MissingTokenError) as excinfo:
        builder.build()

    assert "Expected ';' after expression" in str(excinfo.value)
    assert excinfo.value.token == Token(TokenType.DOT, ".")


def test_step22_instanceof_without_left_operand_raises_unexpected_token_error():
    """소스코드: instanceof Robot;  (좌변 없이 instanceof로 문장이 시작됨)

    instanceof는 primary()가 인식하는 시작 토큰이 아니므로, 표현식을
    시작할 수 없는 토큰으로 처리되어 UnexpectedTokenError가 나야 한다.
    """
    tokens = [
        Token(TokenType.INSTANCEOF, "instanceof"),
        Token(TokenType.IDENTIFIER, "Robot"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    with pytest.raises(UnexpectedTokenError) as excinfo:
        builder.build()

    assert "Unexpected token" in str(excinfo.value)


# --- 23단계: instanceof 통합 시나리오 ---
#
# instanceof를 실제로 쓸 법한 맥락(함수 파라미터 타입 분기, 배열 순회
# 중 필터링, 다단계 상속, 메서드 안의 this, 함수 인자로 바로 전달)에
# 끼워 넣었을 때도 지금까지 만든 다른 문법들과 자연스럽게 조립되는지
# 확인한다.

def test_step23_function_dispatches_by_instanceof_chain():
    """소스코드:
    Func describe(w) {
        if (w instanceof SpeedRobot) { return "fast"; }
        if (w instanceof Robot) { return "normal"; }
        return "unknown";
    }
    """
    tokens = [
        Token(TokenType.FUNC, "Func"),
        Token(TokenType.IDENTIFIER, "describe"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.IDENTIFIER, "w"),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.IF, "if"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.IDENTIFIER, "w"),
        Token(TokenType.INSTANCEOF, "instanceof"),
        Token(TokenType.IDENTIFIER, "SpeedRobot"),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.RETURN, "return"),
        Token(TokenType.STRING, '"fast"', literal="fast"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.IF, "if"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.IDENTIFIER, "w"),
        Token(TokenType.INSTANCEOF, "instanceof"),
        Token(TokenType.IDENTIFIER, "Robot"),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.RETURN, "return"),
        Token(TokenType.STRING, '"normal"', literal="normal"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.RETURN, "return"),
        Token(TokenType.STRING, '"unknown"', literal="unknown"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    def instanceof_check(class_name):
        return InstanceOfExpr(
            object=VariableExpr(Token(TokenType.IDENTIFIER, "w")),
            keyword=Token(TokenType.INSTANCEOF, "instanceof"),
            class_name=VariableExpr(Token(TokenType.IDENTIFIER, class_name)),
        )

    assert builder.build() == [
        FunctionStmt(
            name=Token(TokenType.IDENTIFIER, "describe"),
            params=[Token(TokenType.IDENTIFIER, "w")],
            body=[
                IfStmt(
                    condition=instanceof_check("SpeedRobot"),
                    then_branch=BlockStmt(
                        statements=[
                            ReturnStmt(keyword=Token(TokenType.RETURN, "return"), value=LiteralExpr("fast"))
                        ]
                    ),
                    else_branch=None,
                ),
                IfStmt(
                    condition=instanceof_check("Robot"),
                    then_branch=BlockStmt(
                        statements=[
                            ReturnStmt(keyword=Token(TokenType.RETURN, "return"), value=LiteralExpr("normal"))
                        ]
                    ),
                    else_branch=None,
                ),
                ReturnStmt(keyword=Token(TokenType.RETURN, "return"), value=LiteralExpr("unknown")),
            ],
        )
    ]


def test_step23_function_counts_array_elements_matching_instanceof():
    """소스코드:
    Func countRobots(items) {
        var count = 0;
        var i = 0;
        for (i = 0; i < 3; i = i + 1) {
            if (items[i] instanceof Robot) {
                count = count + 1;
            }
        }
        return count;
    }
    """
    tokens = [
        Token(TokenType.FUNC, "Func"),
        Token(TokenType.IDENTIFIER, "countRobots"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.IDENTIFIER, "items"),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.VAR, "var"),
        Token(TokenType.IDENTIFIER, "count"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.NUMBER, "0", literal=0.0),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.VAR, "var"),
        Token(TokenType.IDENTIFIER, "i"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.NUMBER, "0", literal=0.0),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.FOR, "for"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.IDENTIFIER, "i"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.NUMBER, "0", literal=0.0),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.IDENTIFIER, "i"),
        Token(TokenType.LESS, "<"),
        Token(TokenType.NUMBER, "3", literal=3.0),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.IDENTIFIER, "i"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.IDENTIFIER, "i"),
        Token(TokenType.PLUS, "+"),
        Token(TokenType.NUMBER, "1", literal=1.0),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.IF, "if"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.IDENTIFIER, "items"),
        Token(TokenType.LEFT_BRACKET, "["),
        Token(TokenType.IDENTIFIER, "i"),
        Token(TokenType.RIGHT_BRACKET, "]"),
        Token(TokenType.INSTANCEOF, "instanceof"),
        Token(TokenType.IDENTIFIER, "Robot"),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.IDENTIFIER, "count"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.IDENTIFIER, "count"),
        Token(TokenType.PLUS, "+"),
        Token(TokenType.NUMBER, "1", literal=1.0),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.RETURN, "return"),
        Token(TokenType.IDENTIFIER, "count"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        FunctionStmt(
            name=Token(TokenType.IDENTIFIER, "countRobots"),
            params=[Token(TokenType.IDENTIFIER, "items")],
            body=[
                VarDeclStmt(name=Token(TokenType.IDENTIFIER, "count"), initializer=LiteralExpr(0.0)),
                VarDeclStmt(name=Token(TokenType.IDENTIFIER, "i"), initializer=LiteralExpr(0.0)),
                ForStmt(
                    initializer=ExpressionStmt(
                        expression=AssignExpr(name=Token(TokenType.IDENTIFIER, "i"), value=LiteralExpr(0.0))
                    ),
                    condition=BinaryExpr(
                        left=VariableExpr(Token(TokenType.IDENTIFIER, "i")),
                        operator=Token(TokenType.LESS, "<"),
                        right=LiteralExpr(3.0),
                    ),
                    increment=AssignExpr(
                        name=Token(TokenType.IDENTIFIER, "i"),
                        value=BinaryExpr(
                            left=VariableExpr(Token(TokenType.IDENTIFIER, "i")),
                            operator=Token(TokenType.PLUS, "+"),
                            right=LiteralExpr(1.0),
                        ),
                    ),
                    body=BlockStmt(
                        statements=[
                            IfStmt(
                                condition=InstanceOfExpr(
                                    object=IndexGetExpr(
                                        object=VariableExpr(Token(TokenType.IDENTIFIER, "items")),
                                        bracket=Token(TokenType.LEFT_BRACKET, "["),
                                        index=VariableExpr(Token(TokenType.IDENTIFIER, "i")),
                                    ),
                                    keyword=Token(TokenType.INSTANCEOF, "instanceof"),
                                    class_name=VariableExpr(Token(TokenType.IDENTIFIER, "Robot")),
                                ),
                                then_branch=BlockStmt(
                                    statements=[
                                        ExpressionStmt(
                                            expression=AssignExpr(
                                                name=Token(TokenType.IDENTIFIER, "count"),
                                                value=BinaryExpr(
                                                    left=VariableExpr(Token(TokenType.IDENTIFIER, "count")),
                                                    operator=Token(TokenType.PLUS, "+"),
                                                    right=LiteralExpr(1.0),
                                                ),
                                            )
                                        )
                                    ]
                                ),
                                else_branch=None,
                            )
                        ]
                    ),
                ),
                ReturnStmt(
                    keyword=Token(TokenType.RETURN, "return"),
                    value=VariableExpr(Token(TokenType.IDENTIFIER, "count")),
                ),
            ],
        )
    ]


def test_step23_instanceof_checks_ancestor_across_three_level_inheritance():
    """소스코드:
    Class Animal { }
    Class Dog : Animal { }
    Class Puppy : Dog { }

    var p = Puppy();
    print p instanceof Animal;

    직계 부모가 아니라 조상(Animal)과의 instanceof도 AstBuilder
    입장에서는 동일한 문법이라 상속 단계 수와 무관하게 그대로
    파싱되어야 한다 (실제 조상 판정은 Executor의 상속 체인 탐색 몫).
    """
    tokens = [
        Token(TokenType.CLASS, "Class"),
        Token(TokenType.IDENTIFIER, "Animal"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.CLASS, "Class"),
        Token(TokenType.IDENTIFIER, "Dog"),
        Token(TokenType.COLON, ":"),
        Token(TokenType.IDENTIFIER, "Animal"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.CLASS, "Class"),
        Token(TokenType.IDENTIFIER, "Puppy"),
        Token(TokenType.COLON, ":"),
        Token(TokenType.IDENTIFIER, "Dog"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.VAR, "var"),
        Token(TokenType.IDENTIFIER, "p"),
        Token(TokenType.EQUAL, "="),
        Token(TokenType.IDENTIFIER, "Puppy"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.PRINT, "print"),
        Token(TokenType.IDENTIFIER, "p"),
        Token(TokenType.INSTANCEOF, "instanceof"),
        Token(TokenType.IDENTIFIER, "Animal"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        ClassStmt(name=Token(TokenType.IDENTIFIER, "Animal"), superclass=None, methods=[]),
        ClassStmt(
            name=Token(TokenType.IDENTIFIER, "Dog"),
            superclass=VariableExpr(Token(TokenType.IDENTIFIER, "Animal")),
            methods=[],
        ),
        ClassStmt(
            name=Token(TokenType.IDENTIFIER, "Puppy"),
            superclass=VariableExpr(Token(TokenType.IDENTIFIER, "Dog")),
            methods=[],
        ),
        VarDeclStmt(
            name=Token(TokenType.IDENTIFIER, "p"),
            initializer=CallExpr(
                callee=VariableExpr(Token(TokenType.IDENTIFIER, "Puppy")),
                paren=Token(TokenType.LEFT_PAREN, "("),
                arguments=[],
            ),
        ),
        PrintStmt(
            expression=InstanceOfExpr(
                object=VariableExpr(Token(TokenType.IDENTIFIER, "p")),
                keyword=Token(TokenType.INSTANCEOF, "instanceof"),
                class_name=VariableExpr(Token(TokenType.IDENTIFIER, "Animal")),
            )
        ),
    ]


def test_step23_class_method_checks_this_instanceof():
    """소스코드: Class Shape { isCircle() { return this instanceof Circle; } }"""
    tokens = [
        Token(TokenType.CLASS, "Class"),
        Token(TokenType.IDENTIFIER, "Shape"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.IDENTIFIER, "isCircle"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.RETURN, "return"),
        Token(TokenType.THIS, "this"),
        Token(TokenType.INSTANCEOF, "instanceof"),
        Token(TokenType.IDENTIFIER, "Circle"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        ClassStmt(
            name=Token(TokenType.IDENTIFIER, "Shape"),
            superclass=None,
            methods=[
                FunctionStmt(
                    name=Token(TokenType.IDENTIFIER, "isCircle"),
                    params=[],
                    body=[
                        ReturnStmt(
                            keyword=Token(TokenType.RETURN, "return"),
                            value=InstanceOfExpr(
                                object=ThisExpr(keyword=Token(TokenType.THIS, "this")),
                                keyword=Token(TokenType.INSTANCEOF, "instanceof"),
                                class_name=VariableExpr(Token(TokenType.IDENTIFIER, "Circle")),
                            ),
                        )
                    ],
                )
            ],
        )
    ]


def test_step23_instanceof_result_passed_as_call_argument():
    """소스코드: print report(w instanceof Robot);"""
    tokens = [
        Token(TokenType.PRINT, "print"),
        Token(TokenType.IDENTIFIER, "report"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.IDENTIFIER, "w"),
        Token(TokenType.INSTANCEOF, "instanceof"),
        Token(TokenType.IDENTIFIER, "Robot"),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        PrintStmt(
            expression=CallExpr(
                callee=VariableExpr(Token(TokenType.IDENTIFIER, "report")),
                paren=Token(TokenType.LEFT_PAREN, "("),
                arguments=[
                    InstanceOfExpr(
                        object=VariableExpr(Token(TokenType.IDENTIFIER, "w")),
                        keyword=Token(TokenType.INSTANCEOF, "instanceof"),
                        class_name=VariableExpr(Token(TokenType.IDENTIFIER, "Robot")),
                    )
                ],
            )
        )
    ]
