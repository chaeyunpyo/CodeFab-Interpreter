"""Checker Unit 정의.

Checker Unit이 검출하는 오류:
- 변수 중복 선언 오류 (같은 블록 안에서 같은 이름을 두 번 선언)
- 지역 변수 초기화식에서 자기 자신을 읽는 오류 (예: var a = a;)

동작 방식:
Stmt 목록을 받아서 하나씩 순서대로 검사한다. 블록(BlockStmt)을 만나면
그 안으로 들어가서 다시 검사하고, if/for 문을 만나면 그 안의 statement도
계속 검사한다. 이렇게 안쪽까지 파고들며 검사하는 방식을 DFS(깊이 우선 탐색)
라고 부른다.

역할 구분:
- CheckerError    : 오류 하나를 표현
- ExprNameFinder  : Expr 트리 안에서 특정 변수 이름을 쓰는 곳이 있는지 찾음
- ScopeChecker    : 블록 하나(스코프) 안의 변수 선언 오류를 검사
- CheckerUnit     : Stmt 목록을 DFS로 순회하며 어디서 새 스코프를 열지 결정
"""

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
    def uses_name(self, expr, name):
        if isinstance(expr, VariableExpr):
            return expr.name.lexeme == name

        for field in dataclasses.fields(expr):
            value = getattr(expr, field.name)
            if isinstance(value, Expr) and self.uses_name(value, name):
                return True

        return False


class ScopeChecker:
    def __init__(self, expr_name_finder):
        self.declared_names = []
        self.expr_name_finder = expr_name_finder

    def check_var_decl(self, statement, errors):
        """변수 선언문(var a = ...;) 하나를 검사한다."""
        name = statement.name.lexeme

        # 1. 초기화식이 자기 자신을 읽고 있는지 검사한다. 예: var a = a;
        if statement.initializer is not None:
            if self.expr_name_finder.uses_name(statement.initializer, name):
                message = "Can't read local variable in initializer."
                errors.append(CheckerError(message, statement.name))

        # 2. 같은 블록에 이미 같은 이름이 선언되어 있었는지 검사한다.
        if name in self.declared_names:
            message = "Already a variable with this name in this scope."
            errors.append(CheckerError(message, statement.name))
        else:
            self.declared_names.append(name)


class CheckerUnit:
    def __init__(self, statements):
        self.statements = statements
        self.expr_name_finder = ExprNameFinder()

    def check(self):
        errors = []
        self.check_block(self.statements, errors)
        return errors

    def check_block(self, statements, errors):
        scope = ScopeChecker(self.expr_name_finder)
        for statement in statements:
            self.check_statement(statement, scope, errors)

    def check_statement(self, statement, scope, errors):

        if isinstance(statement, VarDeclStmt):
            scope.check_var_decl(statement, errors)

        elif isinstance(statement, BlockStmt):
            # 블록 안은 새로운 스코프이므로 check_block을 다시 호출한다.
            self.check_block(statement.statements, errors)

        elif isinstance(statement, IfStmt):
            self.check_statement(statement.then_branch, scope, errors)
            if statement.else_branch is not None:
                self.check_statement(statement.else_branch, scope, errors)

        elif isinstance(statement, ForStmt):
            if statement.initializer is not None:
                self.check_statement(statement.initializer, scope, errors)
            self.check_statement(statement.body, scope, errors)
