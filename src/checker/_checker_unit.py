"""CheckerUnit 정의. 자세한 설명은 요구사항_정리/Unit.md 참고."""

import dataclasses

from nodes.expr import Expr, SuperExpr, ThisExpr, VariableExpr
from nodes.stmt import BlockStmt, ClassStmt, ForStmt, FunctionStmt, IfStmt, ImportStmt, ReturnStmt, VarDeclStmt

from ._constant_folder import ConstantFolder
from ._finders import ExprNameFinder, ThisSuperFinder, VariableUseFinder
from ._scope import ScopeChecker
from .errors import CheckerError


class CheckerUnit:
    """Stmt 목록을 DFS로 순회하며 오류를 찾는다."""

    def __init__(self, statements):
        self.statements = statements
        self.expr_name_finder = ExprNameFinder()
        self.this_super_finder = ThisSuperFinder()
        self.variable_use_finder = VariableUseFinder()
        self.constant_folder = ConstantFolder()
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
        self.locals = {}
        self.scope_stack = []
        self.check_block(self.statements)
        return self.errors

    def check_block(self, statements, parent=None):
        scope = ScopeChecker(self.expr_name_finder, self.errors, parent=parent)
        for statement in statements:
            self.check_statement(statement, scope)

    def check_statement(self, statement, scope):
        self._check_this_super_usage(statement)
        self._resolve_variable_usage(statement)
        self._fold_constants(statement)
        handler = self._stmt_handlers.get(type(statement))
        if handler is not None:
            handler(statement, scope)

    def _resolve_variable_usage(self, statement):
        """지역 변수 참조/대입마다 몇 단계 위 스코프에 있는지(distance) 계산해둔다.

        (요구사항_정리/실행전_최적화.md) 최상위(전역)에서 선언/참조되는
        변수나, 함수 안에서 함수 바깥을 참조하는 경우는 기록하지 않는다
        (Storage가 호출마다 지역 스코프 체인을 초기화하기 때문).
        """
        for field in dataclasses.fields(statement):
            value = getattr(statement, field.name)
            if isinstance(value, Expr):
                for node in self.variable_use_finder.find(value):
                    self._resolve_variable_node(node)

    def _resolve_variable_node(self, node):
        name = node.name.lexeme
        for distance, local_scope in enumerate(reversed(self.scope_stack)):
            if name in local_scope:
                self.locals[id(node)] = distance
                return

    def _declare_local(self, name):
        if self.scope_stack:
            self.scope_stack[-1].add(name)

    def _fold_constants(self, statement):
        for field in dataclasses.fields(statement):
            value = getattr(statement, field.name)
            if isinstance(value, Expr):
                setattr(statement, field.name, self.constant_folder.fold(value))

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
        if statement.name is not None:
            self._declare_local(statement.name.lexeme)

    def _check_block_stmt(self, statement, scope):
        if id(statement) in self.visited_blocks:
            return
        self.visited_blocks.add(id(statement))
        self.scope_stack.append(set())
        try:
            self.check_block(statement.statements, parent=scope)
        finally:
            self.scope_stack.pop()

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
        # 일반 Func 선언은 메서드로 바인딩되지 않은 Function이라 This/Super가
        # 실행 시점에 없다(클로저 없음, src/executor/_function.py 참고).
        # 메서드 본문 자체를 검사하는 _check_class_stmt -> _check_function_body
        # 경로는 이 메서드를 거치지 않으므로 class_stack이 그대로 유지된다.
        outer_class_stack = self.class_stack
        self.class_stack = []
        try:
            self._check_function_body(statement.params, statement.body, is_init=False, parent=scope)
        finally:
            self.class_stack = outer_class_stack

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
                self._check_function_body(method.params, method.body, is_init, parent=scope)
        finally:
            self.class_stack.pop()

    def _check_self_inheritance(self, statement):
        superclass = statement.superclass
        if isinstance(superclass, VariableExpr) and superclass.name.lexeme == statement.name.lexeme:
            self.errors.append(CheckerError("A class can't inherit from itself.", superclass.name))

    def _check_function_body(self, params, body, is_init, parent=None):
        # 파라미터도 이 함수(메서드) 스코프의 선언으로 취급한다.
        function_scope = ScopeChecker(self.expr_name_finder, self.errors, parent=parent)

        # 함수 호출마다 Storage가 지역 스코프 체인을 초기화하므로(클로저
        # 없음, src/executor/_function.py 참고) 거리 계산도 여기서 새로
        # 시작해야 한다.
        outer_scope_stack = self.scope_stack
        self.scope_stack = [set()]
        for param in params:
            function_scope.declare_name(param.lexeme, param)
            self._declare_local(param.lexeme)

        self.function_depth += 1
        self.init_stack.append(is_init)
        try:
            for body_statement in body:
                self.check_statement(body_statement, function_scope)
        finally:
            self.init_stack.pop()
            self.function_depth -= 1
            self.scope_stack = outer_scope_stack
