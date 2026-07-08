from nodes.expr import LiteralExpr, SuperExpr, ThisExpr
from nodes.stmt import ClassStmt, FunctionStmt, ImportStmt, VarDeclStmt
from nodes.tokens import Token
from nodes.token_type import TokenType


def make_var_decl(name: str = "a", initializer=None) -> VarDeclStmt:
    return VarDeclStmt(name=Token(TokenType.IDENTIFIER, name), initializer=initializer)


def make_function(name="foo", params=None, body=None):
    return FunctionStmt(
        name=Token(TokenType.IDENTIFIER, name),
        params=params if params is not None else [],
        body=body if body is not None else [],
    )


def make_param(name):
    return Token(TokenType.IDENTIFIER, name)


def make_class(name="Robot", superclass=None, methods=None):
    return ClassStmt(
        name=Token(TokenType.IDENTIFIER, name),
        superclass=superclass,
        methods=methods if methods is not None else [],
    )


def make_this():
    return ThisExpr(keyword=Token(TokenType.THIS, "this"))


def make_super(method="move"):
    return SuperExpr(keyword=Token(TokenType.SUPER, "super"), method=Token(TokenType.IDENTIFIER, method))


def make_import(path="a.txt", alias="a"):
    return ImportStmt(
        keyword=Token(TokenType.IMPORT, "import"),
        path=LiteralExpr(path),
        alias=Token(TokenType.IDENTIFIER, alias),
    )
