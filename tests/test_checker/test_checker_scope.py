from checker import CheckerUnit
from nodes.expr import AssignExpr, BinaryExpr, LiteralExpr, VariableExpr
from nodes.stmt import BlockStmt, ExpressionStmt, ForStmt, IfStmt, PrintStmt, VarDeclStmt
from nodes.tokens import Token
from nodes.token_type import TokenType

from checker_helpers import make_class, make_function, make_var_decl


def test_stores_empty_statements():
    checker = CheckerUnit([])

    assert checker.statements == []


def test_stores_given_statements_as_is():
    statements = [make_var_decl("a"), make_var_decl("b")]

    checker = CheckerUnit(statements)

    assert checker.statements == statements
    assert len(checker.statements) == 2


def test_accepts_mixed_statement_types():
    statements = [
        make_var_decl("a"),
        ExpressionStmt(expression=None),
    ]

    checker = CheckerUnit(statements)

    assert isinstance(checker.statements[0], VarDeclStmt)
    assert isinstance(checker.statements[1], ExpressionStmt)


def test_check_returns_no_errors_when_empty():
    checker = CheckerUnit([])

    assert checker.check() == []


def test_check_returns_no_errors_for_single_declaration():
    checker = CheckerUnit([make_var_decl("a")])

    assert checker.check() == []


def test_check_detects_duplicate_declaration_in_same_block():
    statements = [make_var_decl("a"), make_var_decl("a")]
    checker = CheckerUnit(statements)

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Already a variable with this name in this scope."


def test_check_error_str_includes_line_number():
    first = VarDeclStmt(name=Token(TokenType.IDENTIFIER, "a", line=3), initializer=None)
    second = VarDeclStmt(name=Token(TokenType.IDENTIFIER, "a", line=5), initializer=None)
    checker = CheckerUnit([first, second])

    errors = checker.check()

    assert str(errors[0]) == "[Checker] Line 5: Already a variable with this name in this scope."


# 변수 중복 선언 검사

def test_check_allows_same_name_in_nested_block():
    statements = [
        make_var_decl("a"),
        BlockStmt(statements=[make_var_decl("a")]),
    ]
    checker = CheckerUnit(statements)

    assert checker.check() == []


# built-in 이름(Array 등) 보호 — Storage._scopes[0]에 항상 등록되는 이름을
# 최상위에서 재선언하면 이후 Array(...) 호출이 전부 깨지므로 막아야 한다.

def test_check_detects_top_level_redeclaration_of_builtin_name():
    statements = [make_var_decl("Array")]
    checker = CheckerUnit(statements)

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Already a variable with this name in this scope."


def test_check_allows_shadowing_builtin_name_inside_nested_block():
    # 최상위 Array는 보호 대상이지만, 지역 블록에서 그림자를 만드는 건
    # 일반 변수 shadowing과 같은 규칙이라 허용된다 (최상위 Array 자체는
    # 그대로 남아있다).
    statements = [BlockStmt(statements=[make_var_decl("Array")])]
    checker = CheckerUnit(statements)

    assert checker.check() == []


def test_check_detects_plain_assignment_to_builtin_name():
    # Array = 5;  -- var 없는 대입도 선언과 마찬가지로 전역 built-in을
    # 영구히 덮어쓰므로(Storage.set이 이름 기반으로 전역까지 거슬러
    # 올라가 찾아서 덮어씀) 막아야 한다.
    assign = AssignExpr(name=Token(TokenType.IDENTIFIER, "Array"), value=LiteralExpr(5.0))
    statements = [ExpressionStmt(expression=assign)]
    checker = CheckerUnit(statements)

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Cannot reassign built-in name 'Array'."


def test_check_allows_assignment_to_locally_shadowed_builtin_name():
    # { var Array = 1; Array = 2; }  -- 지역에서 그림자를 만든 뒤 그 지역
    # 변수에 대입하는 거라 실제 전역 built-in은 건드리지 않으므로 허용된다.
    assign = AssignExpr(name=Token(TokenType.IDENTIFIER, "Array"), value=LiteralExpr(2.0))
    statements = [BlockStmt(statements=[make_var_decl("Array"), ExpressionStmt(expression=assign)])]
    checker = CheckerUnit(statements)

    assert checker.check() == []


def test_check_detects_duplicate_declaration_inside_nested_block():
    # { var a = "hi"; var a = 3; }
    statements = [
        BlockStmt(
            statements=[
                make_var_decl("a", LiteralExpr("hi")),
                make_var_decl("a", LiteralExpr(3)),
            ]
        ),
    ]
    checker = CheckerUnit(statements)

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Already a variable with this name in this scope."


# 자기 참조 검사
def test_check_detects_self_reference_in_initializer():
    # { var a = a; }
    statements = [
        BlockStmt(
            statements=[
                make_var_decl("a", VariableExpr(Token(TokenType.IDENTIFIER, "a"))),
            ]
        ),
    ]
    checker = CheckerUnit(statements)

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Can't read local variable in initializer."


def test_check_detects_self_reference_even_when_outer_scope_has_same_name():
    # var a = 1; { var a = a; }  -- 로컬 a가 바깥을 가려도 초기화식은 로컬 a를 읽는다.
    statements = [
        make_var_decl("a", LiteralExpr(1)),
        BlockStmt(
            statements=[
                make_var_decl("a", VariableExpr(Token(TokenType.IDENTIFIER, "a"))),
            ]
        ),
    ]
    checker = CheckerUnit(statements)

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Can't read local variable in initializer."

def test_check_does_not_crash_when_initializer_is_not_an_expr_node():
    # Expr이 아닌 초기화식이 와도 죽지 않아야 한다.
    broken_initializer = "a"
    checker = CheckerUnit([make_var_decl("a", broken_initializer)])

    assert checker.check() == []


def test_check_does_not_crash_when_var_decl_name_token_is_missing():
    # name 토큰이 없어도(None) 죽지 않아야 한다.
    broken_statement = VarDeclStmt(name=None, initializer=None)
    checker = CheckerUnit([broken_statement])

    assert checker.check() == []


def test_check_does_not_crash_on_self_referencing_block():
    # 블록이 자기 자신을 포함하는 순환 참조에도 죽지 않아야 한다.
    cyclic_block = BlockStmt(statements=[])
    cyclic_block.statements.append(cyclic_block)
    checker = CheckerUnit([cyclic_block])

    errors = checker.check()

    assert isinstance(errors, list)


# for 문 검사
def test_check_for_loop_with_no_issues_has_no_errors():
    # for (var i = 0; i < 10; i = i + 1) { print i; }
    i_token = Token(TokenType.IDENTIFIER, "i")
    statements = [
        ForStmt(
            initializer=VarDeclStmt(name=i_token, initializer=LiteralExpr(0)),
            condition=BinaryExpr(
                left=VariableExpr(i_token),
                operator=Token(TokenType.LESS, "<"),
                right=LiteralExpr(10),
            ),
            increment=AssignExpr(
                name=i_token,
                value=BinaryExpr(
                    left=VariableExpr(i_token),
                    operator=Token(TokenType.PLUS, "+"),
                    right=LiteralExpr(1),
                ),
            ),
            body=BlockStmt(statements=[PrintStmt(expression=VariableExpr(i_token))]),
        ),
    ]
    checker = CheckerUnit(statements)

    assert checker.check() == []


def test_check_detects_duplicate_declaration_between_outer_var_and_for_initializer():
    # var i = 0; for (var i = 1; ; ) {}  -- for initializer는 새 스코프를 열지 않는다.
    statements = [
        make_var_decl("i", LiteralExpr(0)),
        ForStmt(
            initializer=make_var_decl("i", LiteralExpr(1)),
            condition=None,
            increment=None,
            body=BlockStmt(statements=[]),
        ),
    ]
    checker = CheckerUnit(statements)

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Already a variable with this name in this scope."


def test_check_detects_duplicate_declaration_between_for_initializer_and_bare_body_statement():
    # for (var i = 0; ; ) var i = 1;  -- body가 블록이 아니면 initializer와 스코프를 공유한다.
    statements = [
        ForStmt(
            initializer=make_var_decl("i", LiteralExpr(0)),
            condition=None,
            increment=None,
            body=make_var_decl("i", LiteralExpr(1)),
        ),
    ]
    checker = CheckerUnit(statements)

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Already a variable with this name in this scope."


def test_check_allows_same_name_when_if_then_and_else_are_blocks():
    # if (true) { var a = 1; } else { var a = 2; }  -- 블록이면 각자 새 스코프를 연다.
    statements = [
        IfStmt(
            condition=LiteralExpr(True),
            then_branch=BlockStmt(statements=[make_var_decl("a", LiteralExpr(1))]),
            else_branch=BlockStmt(statements=[make_var_decl("a", LiteralExpr(2))]),
        ),
    ]
    checker = CheckerUnit(statements)

    assert checker.check() == []


def test_check_detects_duplicate_declaration_when_if_then_and_else_are_bare_statements():
    # if (true) var a = 1; else var a = 2;  -- 블록이 아니면 바깥과 스코프를 공유한다.
    statements = [
        IfStmt(
            condition=LiteralExpr(True),
            then_branch=make_var_decl("a", LiteralExpr(1)),
            else_branch=make_var_decl("a", LiteralExpr(2)),
        ),
    ]
    checker = CheckerUnit(statements)

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Already a variable with this name in this scope."


# 함수/클래스 선언 이름도 이 스코프의 선언이다 - var와 동일한 중복 규칙을 따른다.

def test_check_detects_duplicate_function_declaration_in_same_scope():
    statements = [make_function("foo"), make_function("foo")]
    checker = CheckerUnit(statements)

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Already a variable with this name in this scope."


def test_check_detects_duplicate_class_declaration_in_same_scope():
    statements = [make_class("Robot"), make_class("Robot")]
    checker = CheckerUnit(statements)

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Already a variable with this name in this scope."


def test_check_detects_function_name_colliding_with_existing_variable():
    statements = [make_var_decl("foo"), make_function("foo")]
    checker = CheckerUnit(statements)

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Already a variable with this name in this scope."


def test_check_detects_function_declaration_named_after_builtin():
    # Func Array() {}  -- var Array = ...;와 동일하게 built-in을 가려버리므로 막아야 한다.
    statements = [make_function("Array")]
    checker = CheckerUnit(statements)

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Already a variable with this name in this scope."


def test_check_detects_class_declaration_named_after_builtin():
    statements = [make_class("Array")]
    checker = CheckerUnit(statements)

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Already a variable with this name in this scope."


def test_check_allows_function_name_shadowing_outer_function_in_nested_block():
    # Func foo(){} { Func foo(){} }  -- 다른 스코프라 shadowing으로 허용된다.
    statements = [make_function("foo"), BlockStmt(statements=[make_function("foo")])]
    checker = CheckerUnit(statements)

    assert checker.check() == []
