"""Checker Unit 정의. 자세한 설명은 checker_summary.txt 참고."""

import dataclasses

from nodes.expr import Expr, VariableExpr
from nodes.stmt import BlockStmt, ForStmt, IfStmt, VarDeclStmt
from source_error import SourceError


class CheckerError(SourceError):
    """검사 중 발견한 오류 하나를 표현한다."""

    UNIT = "Checker"


class ExprNameFinder:
    """Expr 안에서 특정 변수 이름을 쓰는 곳이 있는지 찾는다."""

    def uses_name(self, expr, name):
        if not isinstance(expr, Expr):
            return False

        if isinstance(expr, VariableExpr):
            return expr.name.lexeme == name

        for field in dataclasses.fields(expr):
            value = getattr(expr, field.name)
            if isinstance(value, Expr) and self.uses_name(value, name):
                return True

        return False


class ScopeChecker:
    """블록 하나(스코프)의 변수 선언 오류를 검사한다."""

    def __init__(self, expr_name_finder, errors):
        self.declared_names = []
        self.expr_name_finder = expr_name_finder
        self.errors = errors

    def check_var_decl(self, statement):
        """변수 선언문(var a = ...;) 하나를 검사한다."""
        name_token = statement.name
        if name_token is None:
            return

        name = name_token.lexeme

        initializer_uses_name = (
            statement.initializer is not None
            and self.expr_name_finder.uses_name(statement.initializer, name)
        )
        if initializer_uses_name:
            self._record_error("Can't read local variable in initializer.", name_token)

        if name in self.declared_names:
            self._record_error("Already a variable with this name in this scope.", name_token)
        else:
            self.declared_names.append(name)

    def _record_error(self, message, token):
        self.errors.append(CheckerError(message, token))


class CheckerUnit:
    """Stmt 목록을 DFS로 순회하며 오류를 찾는다."""

    def __init__(self, statements):
        self.statements = statements
        self.expr_name_finder = ExprNameFinder()
        self._stmt_handlers = {
            VarDeclStmt: self._check_var_decl_stmt,
            BlockStmt: self._check_block_stmt,
            IfStmt: self._check_if_stmt,
            ForStmt: self._check_for_stmt,
        }

    def check(self):
        self.errors = []
        self.visited_blocks = set()
        self.check_block(self.statements)
        return self.errors

    def check_block(self, statements):
        scope = ScopeChecker(self.expr_name_finder, self.errors)
        for statement in statements:
            self.check_statement(statement, scope)

    def check_statement(self, statement, scope):
        handler = self._stmt_handlers.get(type(statement))
        if handler is not None:
            handler(statement, scope)

    def _check_var_decl_stmt(self, statement, scope):
        scope.check_var_decl(statement)

    def _check_block_stmt(self, statement, scope):
        if id(statement) in self.visited_blocks:
            return
        self.visited_blocks.add(id(statement))
        self.check_block(statement.statements)

    def _check_if_stmt(self, statement, scope):
        self.check_statement(statement.then_branch, scope)
        if statement.else_branch is not None:
            self.check_statement(statement.else_branch, scope)

    def _check_for_stmt(self, statement, scope):
        if statement.initializer is not None:
            self.check_statement(statement.initializer, scope)
        self.check_statement(statement.body, scope)
