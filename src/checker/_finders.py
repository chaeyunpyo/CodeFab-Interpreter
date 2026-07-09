"""Expr 트리를 훑어서 특정 종류의 노드를 찾아내는 범용 워커들."""

import dataclasses

from nodes.expr import AssignExpr, Expr, SuperExpr, ThisExpr, VariableExpr


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
