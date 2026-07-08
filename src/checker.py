"""Checker Unit 정의. 자세한 설명은 요구사항_정리/Unit.md 참고."""

import dataclasses

from nodes.expr import Expr, SuperExpr, ThisExpr, VariableExpr
from nodes.stmt import BlockStmt, ClassStmt, ForStmt, FunctionStmt, IfStmt, ImportStmt, ReturnStmt, VarDeclStmt
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


class ThisSuperFinder:
    """Expr 트리 안에서 this/super 사용을 전부 찾는다."""

    def find(self, expr):
        found = []
        self._walk(expr, found)
        return found

    def _walk(self, expr, found):
        if isinstance(expr, (ThisExpr, SuperExpr)):
            found.append(expr)
            return

        if not isinstance(expr, Expr):
            return

        for field in dataclasses.fields(expr):
            value = getattr(expr, field.name)
            if isinstance(value, Expr):
                self._walk(value, found)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, Expr):
                        self._walk(item, found)


class ScopeChecker:
    """블록 하나(스코프)의 변수 선언 오류를 검사한다."""

    def __init__(self, expr_name_finder, errors):
        self.declared_names = []
        self.imported_paths = []
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

        self.declare_name(name, name_token)

    def check_import(self, statement):
        """import문 하나를 검사한다. 같은 파일 재import와 alias 이름 충돌을 잡는다."""
        path = statement.path.literal
        if path in self.imported_paths:
            self._record_error("Already imported this file in this scope.", statement.keyword)
        else:
            self.imported_paths.append(path)

        self.declare_name(statement.alias.lexeme, statement.alias)

    def declare_name(self, name, token):
        """이 스코프에 이름 하나를 선언한다. 이미 있으면 중복 오류를 기록한다."""
        if name in self.declared_names:
            self._record_error("Already a variable with this name in this scope.", token)
        else:
            self.declared_names.append(name)

    def _record_error(self, message, token):
        self.errors.append(CheckerError(message, token))


class CheckerUnit:
    """Stmt 목록을 DFS로 순회하며 오류를 찾는다."""

    def __init__(self, statements):
        self.statements = statements
        self.expr_name_finder = ExprNameFinder()
        self.this_super_finder = ThisSuperFinder()
        self._stmt_handlers = {
            VarDeclStmt: self._check_var_decl_stmt,
            BlockStmt: self._check_block_stmt,
            IfStmt: self._check_if_stmt,
            ForStmt: self._check_for_stmt,
            FunctionStmt: self._check_function_stmt,
            ReturnStmt: self._check_return_stmt,
            ClassStmt: self._check_class_stmt,
            ImportStmt: self._check_import_stmt,
        }

    def check(self):
        self.errors = []
        self.visited_blocks = set()
        self.function_depth = 0
        self.init_stack = []
        self.class_stack = []
        self.loop_depth = 0
        self.check_block(self.statements)
        return self.errors

    def check_block(self, statements):
        scope = ScopeChecker(self.expr_name_finder, self.errors)
        for statement in statements:
            self.check_statement(statement, scope)

    def check_statement(self, statement, scope):
        self._check_this_super_usage(statement)
        handler = self._stmt_handlers.get(type(statement))
        if handler is not None:
            handler(statement, scope)

    def _check_this_super_usage(self, statement):
        for field in dataclasses.fields(statement):
            value = getattr(statement, field.name)
            if isinstance(value, Expr):
                for node in self.this_super_finder.find(value):
                    self._validate_this_or_super(node)

    def _validate_this_or_super(self, node):
        if not self.class_stack:
            if isinstance(node, ThisExpr):
                self.errors.append(CheckerError("Can't use 'this' outside of a class.", node.keyword))
            else:
                self.errors.append(CheckerError("Can't use 'super' outside of a class.", node.keyword))
            return

        if isinstance(node, SuperExpr) and not self.class_stack[-1]:
            self.errors.append(CheckerError("Can't use 'super' in a class with no superclass.", node.keyword))

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

        self.loop_depth += 1
        try:
            self.check_statement(statement.body, scope)
        finally:
            self.loop_depth -= 1

    def _check_import_stmt(self, statement, scope):
        if self.loop_depth > 0:
            self.errors.append(CheckerError("Can't use import statement inside a loop.", statement.keyword))
        scope.check_import(statement)

    def _check_function_stmt(self, statement, scope):
        self._check_function_body(statement.params, statement.body, is_init=False)

    def _check_return_stmt(self, statement, scope):
        if self.function_depth == 0:
            self.errors.append(CheckerError("Can't return from top-level code.", statement.keyword))
            return

        if self.init_stack[-1] and statement.value is not None:
            self.errors.append(CheckerError("Can't return a value from an initializer.", statement.keyword))

    def _check_class_stmt(self, statement, scope):
        self._check_self_inheritance(statement)

        self.class_stack.append(statement.superclass is not None)
        try:
            for method in statement.methods:
                is_init = method.name.lexeme == "init"
                self._check_function_body(method.params, method.body, is_init)
        finally:
            self.class_stack.pop()

    def _check_self_inheritance(self, statement):
        superclass = statement.superclass
        if isinstance(superclass, VariableExpr) and superclass.name.lexeme == statement.name.lexeme:
            self.errors.append(CheckerError("A class can't inherit from itself.", superclass.name))

    def _check_function_body(self, params, body, is_init):
        # 파라미터도 이 함수(메서드) 스코프의 선언으로 취급한다.
        function_scope = ScopeChecker(self.expr_name_finder, self.errors)
        for param in params:
            function_scope.declare_name(param.lexeme, param)

        self.function_depth += 1
        self.init_stack.append(is_init)
        try:
            for body_statement in body:
                self.check_statement(body_statement, function_scope)
        finally:
            self.init_stack.pop()
            self.function_depth -= 1
