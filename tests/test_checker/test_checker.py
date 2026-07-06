from checker.checker import CheckerUnit
from nodes.expr import LiteralExpr, VariableExpr
from nodes.stmt import BlockStmt, ExpressionStmt, VarDeclStmt
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


def test_check_returns_no_errors_for_single_declaration():
    checker = CheckerUnit([make_var_decl("a")])

    assert checker.check() == []


def test_check_detects_duplicate_declaration_in_same_block():
    statements = [make_var_decl("a"), make_var_decl("a")]
    checker = CheckerUnit(statements)

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Already a variable with this name in this scope."


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
