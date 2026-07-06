import pytest

from checker.checker import CheckerUnit
from nodes.stmt import ExpressionStmt, VarDeclStmt
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


def test_check_raises_not_implemented_with_empty_statements():
    checker = CheckerUnit([])

    with pytest.raises(NotImplementedError):
        checker.check()


def test_check_raises_not_implemented_with_statements():
    checker = CheckerUnit([make_var_decl("a")])

    with pytest.raises(NotImplementedError):
        checker.check()
