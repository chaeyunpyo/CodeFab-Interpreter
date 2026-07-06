from checker.checker import CheckerUnit
from nodes.stmt import BlockStmt, ExpressionStmt, VarDeclStmt
from nodes.tokens import Token
from nodes.token_type import TokenType


def make_var_decl(name: str = "a") -> VarDeclStmt:
    return VarDeclStmt(name=Token(TokenType.IDENTIFIER, name), initializer=None)


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
    assert "a" in errors[0].message


def test_check_allows_same_name_in_nested_block():
    statements = [
        make_var_decl("a"),
        BlockStmt(statements=[make_var_decl("a")]),
    ]
    checker = CheckerUnit(statements)

    assert checker.check() == []


def test_check_detects_duplicate_declaration_inside_nested_block():
    statements = [
        BlockStmt(statements=[make_var_decl("a"), make_var_decl("a")]),
    ]
    checker = CheckerUnit(statements)

    errors = checker.check()

    assert len(errors) == 1
    assert "a" in errors[0].message
