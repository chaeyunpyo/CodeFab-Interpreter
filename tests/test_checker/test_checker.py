from checker import CheckerUnit
from nodes.expr import AssignExpr, BinaryExpr, LiteralExpr, VariableExpr
from nodes.stmt import BlockStmt, ExpressionStmt, ForStmt, IfStmt, PrintStmt, VarDeclStmt
from nodes.tokens import Token
from nodes.token_type import TokenType


def make_var_decl(name: str = "a", initializer=None) -> VarDeclStmt:
    return VarDeclStmt(name=Token(TokenType.IDENTIFIER, name), initializer=initializer)


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

#

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

    assert str(errors[0]) == "[Line 5] Already a variable with this name in this scope."


# 변수 중복 선언 검사

def test_check_allows_same_name_in_nested_block():
    statements = [
        make_var_decl("a"),
        BlockStmt(statements=[make_var_decl("a")]),
    ]
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
    # var a = 1; { var a = a; } -- the local `a` shadows the outer one, so the
    # initializer still reads the not-yet-initialized local `a`.
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
    # var i = 0; for (var i = 1; ; ) {}
    # for의 initializer는 새 스코프를 열지 않으므로 바깥의 i와 충돌한다.
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
