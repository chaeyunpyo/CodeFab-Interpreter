"""Stmt 단위 stepping/breakpoint/watch를 지원하는 디버그 세션.

요구사항_정리/공장제어쉘.md 의 디버그 모드 사양:
    step               - 현재 Stmt 실행 후 다음 Stmt에서 정지 (블록/분기/반복 내부 포함)
    next               - 현재 최상위 Stmt를 전부 실행 후 다음 최상위 Stmt에서 정지 (내부로 진입 X)
    continue           - 다음 breakpoint까지 실행
    add_breakpoint(n)  - n번째 줄에 breakpoint 설정
    remove_breakpoint(n) - breakpoint 해제
    watch(name)/unwatch(name) - 변수 감시 목록 추가/제거
    watched_values()   - 감시 중인 변수들의 현재 값 (변수 저장소에서 직접 조회)
    inspect()          - 현재 스코프의 모든 변수와 값
"""

import dataclasses

from executor import ExecutionError, Storage, evaluate, execute
from nodes.ast_node import AstNode
from nodes.stmt import BlockStmt, ForStmt, IfStmt
from nodes.tokens import Token


def _find_line(node):
    """Stmt/Expr 트리 안에서 처음 발견되는 Token의 line을 재귀적으로 찾는다.

    Stmt 노드 자체는 line을 직접 들고 있지 않아서, 내부 필드를 훑어 Token을 찾는다.
    """
    if isinstance(node, Token):
        return node.line
    if isinstance(node, AstNode):
        for field in dataclasses.fields(node):
            line = _find_line(getattr(node, field.name))
            if line is not None:
                return line
        return None
    if isinstance(node, list):
        for item in node:
            line = _find_line(item)
            if line is not None:
                return line
        return None
    return None


class Debugger:
    def __init__(self, statements):
        self.storage = Storage()
        self.breakpoints = set()
        self.watches = []
        self.finished = False
        self.current_stmt = None
        self.current_line = None
        self._current_index = None
        self._generator = self._walk(statements)
        self._advance()

    # ── stepping ─────────────────────────────────────────────────────────

    def step(self):
        """현재 Stmt를 실행하고, 다음 Stmt(중첩 내부 포함)에서 정지한다."""
        if self.finished:
            return
        self._advance()

    def next(self):
        """현재 최상위 Stmt를 전부 실행하고, 다음 최상위 Stmt에서 정지한다 (내부로 진입 X)."""
        if self.finished:
            return
        index = self._current_index
        self._advance()
        while not self.finished and self._current_index == index:
            self._advance()

    def continue_(self):
        """다음 breakpoint를 만날 때까지(또는 끝날 때까지) 실행한다."""
        while not self.finished:
            if self.current_line in self.breakpoints:
                return
            self.step()

    def _advance(self):
        try:
            stmt, index = next(self._generator)
        except StopIteration:
            self.finished = True
            self.current_stmt = None
            self.current_line = None
            self._current_index = None
            return
        except ExecutionError:
            self.finished = True
            self.current_stmt = None
            self.current_line = None
            self._current_index = None
            raise
        self.current_stmt = stmt
        self.current_line = _find_line(stmt)
        self._current_index = index

    # ── breakpoints ──────────────────────────────────────────────────────

    def add_breakpoint(self, line):
        self.breakpoints.add(line)

    def remove_breakpoint(self, line):
        self.breakpoints.discard(line)

    # ── watch ────────────────────────────────────────────────────────────

    def watch(self, name):
        if name not in self.watches:
            self.watches.append(name)

    def unwatch(self, name):
        if name in self.watches:
            self.watches.remove(name)

    def watched_values(self):
        """감시 중인 변수들의 현재 값을 변수 저장소에서 직접 조회한다."""
        return {
            name: self.storage.get(name) if self.storage.exists(name) else None
            for name in self.watches
        }

    def inspect(self):
        """현재(가장 안쪽) 스코프의 모든 변수와 값을 반환한다."""
        return self.storage.current_scope_items()

    # ── AST 순회 (Stmt 단위로 yield) ─────────────────────────────────────

    def _walk(self, statements):
        for index, stmt in enumerate(statements):
            yield from self._walk_stmt(stmt, index)

    def _walk_stmt(self, stmt, index):
        if isinstance(stmt, BlockStmt):
            self.storage.push_scope()
            try:
                for inner in stmt.statements:
                    yield from self._walk_stmt(inner, index)
            finally:
                self.storage.pop_scope()
            return

        if isinstance(stmt, IfStmt):
            if evaluate(stmt.condition, self.storage):
                yield from self._walk_stmt(stmt.then_branch, index)
            elif stmt.else_branch is not None:
                yield from self._walk_stmt(stmt.else_branch, index)
            return

        if isinstance(stmt, ForStmt):
            if stmt.initializer is not None:
                yield from self._walk_stmt(stmt.initializer, index)
            while stmt.condition is None or evaluate(stmt.condition, self.storage):
                yield from self._walk_stmt(stmt.body, index)
                if stmt.increment is not None:
                    evaluate(stmt.increment, self.storage)
            return

        yield stmt, index
        execute(stmt, self.storage)
