"""Stmt 단위 stepping/breakpoint/watch를 지원하는 디버그 세션.

요구사항_정리/공장제어쉘.md 의 디버그 모드 사양:
    step               - 현재 Stmt 실행 후 다음 Stmt에서 정지 (블록/분기/반복 내부 포함)
    next               - 현재 최상위 Stmt를 전부 실행 후 다음 최상위 Stmt에서 정지 (내부로 진입 X)
    continue           - 다음 breakpoint까지 실행
    add_breakpoint(n)  - n번째 줄에 breakpoint 설정
    remove_breakpoint(n) - breakpoint 해제
    watch(name)/unwatch(name) - 변수 감시 목록 추가/제거
    watched_values()   - 감시 중인 변수들의 현재 값 (변수 저장소에서 직접 조회)
    inspect()          - (local_items, global_items) - 로컬/전역 스코프의 변수와 값
"""

from executor import LoxCallable, Storage, evaluate, execute
from nodes.stmt import BlockStmt, ForStmt, IfStmt


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
        """다음 breakpoint를 만날 때까지(또는 끝날 때까지) 실행한다.

        breakpoint가 주석/빈 줄처럼 실행되는 문장이 없는 줄에 찍혀도, 그 줄을
        지나치는 첫 문장에서 멈추도록 스냅한다 (정확히 그 줄이 실행되지 않아도 된다).
        """
        while not self.finished:
            previous_line = self.current_line
            self.step()
            if self.finished or self._crosses_breakpoint(previous_line, self.current_line):
                return

    def _crosses_breakpoint(self, previous_line, current_line):
        for breakpoint_line in self.breakpoints:
            if current_line == breakpoint_line:
                return True
            if previous_line is not None and previous_line < breakpoint_line < current_line:
                return True
        return False

    def _advance(self):
        try:
            stmt, index = next(self._generator)
        except StopIteration:
            self.finished = True
            self.current_stmt = None
            self.current_line = None
            self._current_index = None
            return
        self.current_stmt = stmt
        self.current_line = stmt.line
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
        """(local_items, global_items)를 반환한다.

        현재 스코프가 곧 전역 스코프이면(최상위) local_items는 비워서 중복 표시를
        피한다. 내장 함수(Array 등 LoxCallable)는 사용자 변수가 아니므로 제외한다.
        """
        global_items = self._without_callables(self.storage.global_scope_items())
        if self.storage.scope_depth() > 1:
            local_items = self._without_callables(self.storage.current_scope_items())
        else:
            local_items = {}
        return local_items, global_items

    @staticmethod
    def _without_callables(items):
        return {name: value for name, value in items.items() if not isinstance(value, LoxCallable)}

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
