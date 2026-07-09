"""Checker Unit 정의. 자세한 설명은 요구사항_정리/Unit.md 참고."""

import dataclasses
import operator

from nodes.expr import (
    AssignExpr,
    BinaryExpr,
    Expr,
    GroupingExpr,
    LiteralExpr,
    SuperExpr,
    ThisExpr,
    UnaryExpr,
    VariableExpr,
)
from nodes.stmt import BlockStmt, ClassStmt, ForStmt, FunctionStmt, IfStmt, ImportStmt, ReturnStmt, VarDeclStmt
from nodes.token_type import TokenType
from source_error import SourceError

_NOT_FOLDABLE = object()

_NUMERIC_BINARY_OPS = {
    TokenType.MINUS: operator.sub,
    TokenType.STAR: operator.mul,
    TokenType.GREATER: operator.gt,
    TokenType.LESS: operator.lt,
    TokenType.GREATER_EQUAL: operator.ge,
    TokenType.LESS_EQUAL: operator.le,
    TokenType.EQUAL_GREATER: operator.ge,
    TokenType.EQUAL_LESS: operator.le,
    TokenType.EQUAL_EQUAL: operator.eq,
    TokenType.BANG_EQUAL: operator.ne,
}


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_string(value):
    return isinstance(value, str)


def _fold_binary_value(operator_token, left, right):
    """Executor의 _evaluate_binary와 같은 규칙으로 계산하되, 접을 수 없으면 _NOT_FOLDABLE."""
    op = operator_token.type

    if op == TokenType.SLASH:
        if _is_number(left) and _is_number(right) and right != 0:
            return left / right
        return _NOT_FOLDABLE

    if op == TokenType.PLUS:
        if _is_string(left) and _is_string(right):
            return left + right
        if _is_number(left) and _is_number(right):
            return left + right
        return _NOT_FOLDABLE

    numeric_op = _NUMERIC_BINARY_OPS.get(op)
    if numeric_op is not None and _is_number(left) and _is_number(right):
        return numeric_op(left, right)

    return _NOT_FOLDABLE


def _fold_unary_value(operator_token, value):
    """Executor의 _evaluate_unary와 같은 규칙으로 계산하되, 접을 수 없으면 _NOT_FOLDABLE."""
    op = operator_token.type

    if op == TokenType.MINUS:
        return -value if _is_number(value) else _NOT_FOLDABLE
    if op == TokenType.PLUS:
        return value if _is_number(value) else _NOT_FOLDABLE
    if op == TokenType.BANG:
        return not value

    return _NOT_FOLDABLE


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


class VariableUseFinder:
    """Expr 트리 안에서 변수 참조(VariableExpr)와 대입(AssignExpr)을 전부 찾는다."""

    def find(self, expr):
        found = []
        self._walk(expr, found)
        return found

    def _walk(self, expr, found):
        if not isinstance(expr, Expr):
            return

        if isinstance(expr, VariableExpr):
            found.append(expr)
            return

        if isinstance(expr, AssignExpr):
            found.append(expr)
            self._walk(expr.value, found)
            return

        for field in dataclasses.fields(expr):
            value = getattr(expr, field.name)
            if isinstance(value, Expr):
                self._walk(value, found)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, Expr):
                        self._walk(item, found)


class ConstantFolder:
    """리터럴로만 구성된 Binary/Unary/Grouping을 접어서 LiteralExpr로 치환한다.

    (요구사항_정리/실행전_최적화.md) 변수가 섞여 있거나, 접었을 때 런타임
    오류가 나는 조합(0으로 나누기 등)은 원본 그대로 둔다.
    """

    def fold(self, expr):
        if not isinstance(expr, Expr):
            return expr

        if isinstance(expr, GroupingExpr):
            expr.expression = self.fold(expr.expression)
            if isinstance(expr.expression, LiteralExpr):
                return LiteralExpr(expr.expression.value)
            return expr

        if isinstance(expr, UnaryExpr):
            expr.right = self.fold(expr.right)
            if isinstance(expr.right, LiteralExpr):
                folded = _fold_unary_value(expr.operator, expr.right.value)
                if folded is not _NOT_FOLDABLE:
                    return LiteralExpr(folded)
            return expr

        if isinstance(expr, BinaryExpr):
            expr.left = self.fold(expr.left)
            expr.right = self.fold(expr.right)
            if isinstance(expr.left, LiteralExpr) and isinstance(expr.right, LiteralExpr):
                folded = _fold_binary_value(expr.operator, expr.left.value, expr.right.value)
                if folded is not _NOT_FOLDABLE:
                    return LiteralExpr(folded)
            return expr

        for field in dataclasses.fields(expr):
            value = getattr(expr, field.name)
            if isinstance(value, Expr):
                setattr(expr, field.name, self.fold(value))
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, Expr):
                        value[i] = self.fold(item)

        return expr


class ScopeChecker:
    """블록 하나(스코프)의 변수 선언 오류를 검사한다."""

    def __init__(self, expr_name_finder, errors, parent=None):
        self.declared_names = []
        self.imported_paths = []
        self.expr_name_finder = expr_name_finder
        self.errors = errors
        self.parent = parent

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
        elif self._is_imported_in_ancestor(path):
            self._record_error("Already imported this file in an enclosing scope.", statement.keyword)
        else:
            self.imported_paths.append(path)

        self.declare_name(statement.alias.lexeme, statement.alias)

    def _is_imported_in_ancestor(self, path):
        ancestor = self.parent
        while ancestor is not None:
            if path in ancestor.imported_paths:
                return True
            ancestor = ancestor.parent
        return False

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
        self._check_function_body(statement.params, statement.body, is_init=False, parent=scope)

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
