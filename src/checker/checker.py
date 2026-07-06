"""Checker Unit 정의.

Checker Unit이 검출하는 오류:
- 변수 중복 선언 오류 (같은 블록 안에서 같은 이름을 두 번 선언)
- 지역 변수 초기화식에서 자기 자신을 읽는 오류 (예: var a = a;)

동작 방식:
Stmt 목록을 받아서 하나씩 순서대로 검사한다. 블록(BlockStmt)을 만나면
그 안으로 들어가서 다시 검사하고, if/for 문을 만나면 그 안의 statement도
계속 검사한다. 이렇게 안쪽까지 파고들며 검사하는 방식을 DFS(깊이 우선 탐색)
라고 부른다.
"""

from nodes.expr import (
    AssignExpr,
    BinaryExpr,
    GroupingExpr,
    LogicalExpr,
    UnaryExpr,
    VariableExpr,
)
from nodes.stmt import BlockStmt, ForStmt, IfStmt, VarDeclStmt


class CheckerError(Exception):
    """검사 중 발견한 오류 하나를 표현한다."""

    def __init__(self, message, token):
        super().__init__(message)
        self.message = message
        self.token = token


class CheckerUnit:
    """Stmt 목록을 받아서 의미상 오류를 찾아내는 클래스."""

    def __init__(self, statements):
        self.statements = statements

    def check(self):
        """statements 전체를 검사하고, 발견한 오류들을 리스트로 돌려준다."""
        errors = []
        self.check_statements(self.statements, errors)
        return errors

    def check_statements(self, statements, errors):
        """statement 리스트 하나를 '블록(스코프)' 하나로 보고 순서대로 검사한다.

        declared_names는 지금까지 이 블록에서 선언된 변수 이름들을 담아두는
        리스트다. 새 블록에 들어올 때마다 새로 만들어지므로, 다른 블록의
        변수 이름과는 서로 겹쳐도 문제가 되지 않는다.
        """
        declared_names = []
        for statement in statements:
            self.check_statement(statement, declared_names, errors)

    def check_statement(self, statement, declared_names, errors):
        """statement 하나를 검사한다."""

        if isinstance(statement, VarDeclStmt):
            self.check_var_decl(statement, declared_names, errors)

        elif isinstance(statement, BlockStmt):
            # 블록 안은 새로운 스코프이므로 declared_names를 새로 만들어서 검사한다.
            self.check_statements(statement.statements, errors)

        elif isinstance(statement, IfStmt):
            self.check_statement(statement.then_branch, declared_names, errors)
            if statement.else_branch is not None:
                self.check_statement(statement.else_branch, declared_names, errors)

        elif isinstance(statement, ForStmt):
            if statement.initializer is not None:
                self.check_statement(statement.initializer, declared_names, errors)
            self.check_statement(statement.body, declared_names, errors)

    def check_var_decl(self, statement, declared_names, errors):
        """변수 선언문(var a = ...;) 하나를 검사한다."""
        name = statement.name.lexeme

        # 1. 초기화식이 자기 자신을 읽고 있는지 검사한다. 예: var a = a;
        if statement.initializer is not None:
            if self.expr_uses_name(statement.initializer, name):
                message = "Can't read local variable in initializer."
                errors.append(CheckerError(message, statement.name))

        # 2. 같은 블록에 이미 같은 이름이 선언되어 있었는지 검사한다.
        if name in declared_names:
            message = "Already a variable with this name in this scope."
            errors.append(CheckerError(message, statement.name))
        else:
            declared_names.append(name)

    def expr_uses_name(self, expr, name):
        """expr 안 어딘가에서 name이라는 변수를 사용하는지 검사한다.

        Expr도 트리 구조이기 때문에 하위 Expr을 하나씩 재귀적으로 확인한다.
        """

        if isinstance(expr, VariableExpr):
            return expr.name.lexeme == name

        if isinstance(expr, AssignExpr):
            return self.expr_uses_name(expr.value, name)

        if isinstance(expr, UnaryExpr):
            return self.expr_uses_name(expr.right, name)

        if isinstance(expr, BinaryExpr):
            left_uses_name = self.expr_uses_name(expr.left, name)
            right_uses_name = self.expr_uses_name(expr.right, name)
            return left_uses_name or right_uses_name

        if isinstance(expr, LogicalExpr):
            left_uses_name = self.expr_uses_name(expr.left, name)
            right_uses_name = self.expr_uses_name(expr.right, name)
            return left_uses_name or right_uses_name

        if isinstance(expr, GroupingExpr):
            return self.expr_uses_name(expr.expression, name)

        # LiteralExpr처럼 더 이상 하위 Expr이 없는 경우 name을 쓸 수 없다.
        return False
