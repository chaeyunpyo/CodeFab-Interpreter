"""Checker Unit 정의. 자세한 설명은 checker_summary.txt 참고."""

import dataclasses

from nodes.expr import Expr, VariableExpr
from nodes.stmt import BlockStmt, ForStmt, IfStmt, VarDeclStmt


class CheckerError(Exception):
    """검사 중 발견한 오류 하나를 표현한다."""

    def __init__(self, message, token):
        super().__init__(message)
        self.message = message
        self.token = token


class ExprNameFinder:
    """Expr 안에서 특정 변수 이름을 쓰는 곳이 있는지 찾는다."""

    def uses_name(self, expr, name):
        # expr이 진짜 Expr가 아니면(예: 손상된 AST) 그냥 False.
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
        # name 토큰이 없으면(손상된 AST) 그냥 넘어간다.
        if statement.name is None:
            return

        name = statement.name.lexeme

        # 1. 초기화식이 자기 자신을 읽고 있는지 검사한다. 예: var a = a;
        if statement.initializer is not None:
            if self.expr_name_finder.uses_name(statement.initializer, name):
                message = "Can't read local variable in initializer."
                self.errors.append(CheckerError(message, statement.name))

        # 2. 같은 블록에 이미 같은 이름이 선언되어 있었는지 검사한다.
        if name in self.declared_names:
            message = "Already a variable with this name in this scope."
            self.errors.append(CheckerError(message, statement.name))
        else:
            self.declared_names.append(name)


class CheckerUnit:
    """Stmt 목록을 DFS로 순회하며 오류를 찾는다."""

    def __init__(self, statements):
        self.statements = statements
        self.expr_name_finder = ExprNameFinder()
        self.errors = []
        self.visited_blocks = set()

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
        if isinstance(statement, VarDeclStmt):
            scope.check_var_decl(statement)

        elif isinstance(statement, BlockStmt):
            # 이미 검사한 블록을 다시 만나면(순환 참조) 더 들어가지 않는다.
            if id(statement) in self.visited_blocks:
                return
            self.visited_blocks.add(id(statement))
            # 블록 안은 새로운 스코프이므로 check_block을 다시 호출한다.
            self.check_block(statement.statements)

        elif isinstance(statement, IfStmt):
            self.check_statement(statement.then_branch, scope)
            if statement.else_branch is not None:
                self.check_statement(statement.else_branch, scope)

        elif isinstance(statement, ForStmt):
            if statement.initializer is not None:
                self.check_statement(statement.initializer, scope)
            self.check_statement(statement.body, scope)
