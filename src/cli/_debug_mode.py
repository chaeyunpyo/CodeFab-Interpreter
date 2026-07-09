"""Stmt 단위 stepping/breakpoint/watch를 지원하는 디버그 모드.

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

from assembler import Assembler, AssemblerError
from checker import CheckerUnit
from executor import ExecutionError, LoxCallable, Storage, evaluate, execute
from nodes.stmt import BlockStmt, ForStmt, IfStmt


class Debugger:
    def __init__(self, statements, locals=None):
        self.storage = Storage(locals)
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
        except ExecutionError:
            self.finished = True
            self.current_stmt = None
            self.current_line = None
            self._current_index = None
            raise
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


def run_debug(path: str) -> None:
    """Stmt 단위 stepping/breakpoint/watch를 지원하는 디버그 모드 진입점.

    파일을 파싱한 뒤 정지시킨 상태로 시작하고, step/next/continue/break/watch/inspect
    명령을 받아가며 한 Stmt씩 실행 상태를 점검한다.
    """
    print(f"[DEBUG] 소스코드 로딩: {path}")

    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
    except OSError as error:
        print(f"파일을 열 수 없습니다: {error}")
        return

    assembler = Assembler(source)
    try:
        assembler.execute()
    except AssemblerError as error:
        print(error)
        return

    checker = CheckerUnit(assembler.ast)
    checker_errors = checker.check()
    if checker_errors:
        for error in checker_errors:
            print(error)
        return

    _debug_repl(Debugger(assembler.ast, checker.locals), source.splitlines())


def _debug_repl(debugger: Debugger, source_lines) -> None:
    _print_debugger_status(debugger, source_lines)
    while True:
        try:
            command = input("(debug) ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if command in ("exit", "quit"):
            return

        _handle_debug_command(debugger, command, source_lines)


def _handle_debug_command(debugger: Debugger, command: str, source_lines) -> None:
    name, _, arg = command.partition(" ")
    arg = arg.strip()

    if name == "step":
        _run_stepping_command(debugger, debugger.step, source_lines)
    elif name == "next":
        _run_stepping_command(debugger, debugger.next, source_lines)
    elif name == "continue":
        _run_stepping_command(debugger, debugger.continue_, source_lines)
    elif name == "break":
        line = _parse_line_number(arg, "break <줄번호>")
        if line is not None:
            debugger.add_breakpoint(line)
            print(f"[DEBUG] {line}번째 줄에 breakpoint 설정")
    elif name == "remove":
        line = _parse_line_number(arg, "remove <줄번호>")
        if line is not None:
            debugger.remove_breakpoint(line)
            print(f"[DEBUG] {line}번째 줄 breakpoint 해제")
    elif name == "breakpoints":
        print(f"[DEBUG] 현재 breakpoint: {sorted(debugger.breakpoints)}")
    elif name == "watch":
        debugger.watch(arg)
        print(f"[DEBUG] '{arg}' 변수 감시 시작")
    elif name == "unwatch":
        debugger.unwatch(arg)
        print(f"[DEBUG] '{arg}' 변수 감시 해제")
    elif name == "watches":
        print("[DEBUG] 감시 중인 변수")
        _print_watches(debugger)
    elif name == "inspect":
        print("[DEBUG] 현재 스코프 변수")
        _print_inspect(debugger)
    else:
        print(f"알 수 없는 명령입니다: {command}")


def _run_stepping_command(debugger: Debugger, action, source_lines) -> None:
    """step/next/continue 공통 실행: 실행 중 런타임 오류가 나도 세션이 죽지 않게 잡는다."""
    try:
        action()
    except ExecutionError as error:
        print(error)
    _print_debugger_status(debugger, source_lines)


def _parse_line_number(arg: str, usage: str):
    try:
        return int(arg)
    except ValueError:
        print(f"사용법: {usage}")
        return None


def _print_debugger_status(debugger: Debugger, source_lines) -> None:
    if debugger.finished:
        print("[DEBUG] 실행 종료")
    else:
        code = _source_line_text(source_lines, debugger.current_line)
        print(f"[DEBUG] {debugger.current_line}번째 줄에서 정지 -> {code}")

    if debugger.watches:
        _print_watches(debugger)


def _source_line_text(source_lines, line_number) -> str:
    if line_number is None or not (1 <= line_number <= len(source_lines)):
        return "(알 수 없음)"
    return source_lines[line_number - 1].strip()


def _print_watches(debugger: Debugger) -> None:
    for name, value in debugger.watched_values().items():
        print(f"[WATCH] {name} = {value}")


def _print_inspect(debugger: Debugger) -> None:
    local_items, global_items = debugger.inspect()

    if not local_items:
        # 최상위(블록 밖)에서는 로컬 스코프가 곧 전역 스코프라, 중복 표시를 피하려고
        # 항상 비워둔다. 이게 "버그처럼" 보이지 않도록 명시적으로 알려준다.
        print("[로컬] (없음 - 현재 블록 스코프 안이 아님)")
    for name, value in local_items.items():
        print(f"[로컬] {name} = {value}")

    if not global_items:
        print("[전역] (없음)")
    for name, value in global_items.items():
        print(f"[전역] {name} = {value}")
