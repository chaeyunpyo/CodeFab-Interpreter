import sys

from assembler import Assembler, AssemblerError, AstBuilder, Tokenizer, UnexpectedTokenError
from checker import CheckerUnit
from executor import ExecutionError
from nodes.token_type import TokenType
from pipeline import Pipeline

from ._debugger import Debugger


class PromptShell:
    """소스코드 한 줄을 입력받아 Pipeline(Assembler -> Checker -> Executor)을 실행하는 REPL 셸.

    '{' 로 시작한 블록이나 then_branch가 아직 없는 if/for 처럼 여러 줄에 걸친 문장은,
    문장이 완성될 때까지 입력을 버퍼에 모아두었다가 한 번에 실행한다.
    (PDF p.17: 한 줄 입력마다 파이프라인 수행)
    """

    def __init__(self):
        self.pipeline = Pipeline()
        self._buffer = ""

    def run(self, source: str) -> None:
        self._buffer = f"{self._buffer}\n{source}" if self._buffer else source

        if self._is_waiting_for_more_input(self._buffer):
            return

        buffered_source = self._buffer
        self._buffer = ""

        for error in self.pipeline.run(buffered_source):
            print(error)

    @staticmethod
    def _is_waiting_for_more_input(source: str) -> bool:
        try:
            tokens = Tokenizer(source).tokenize()
        except Exception:
            return False  # 실제 오류는 Pipeline이 보고하도록 그대로 진행시킨다.

        if PromptShell._has_unclosed_block(tokens):
            return True

        try:
            AstBuilder(tokens).build()
        except UnexpectedTokenError as error:
            # if/for 등이 본문(then_branch/body) 없이 끝났다 -> 다음 줄을 기다린다.
            return error.token is not None and error.token.type == TokenType.EOF
        except Exception:
            return False  # 다른 오류는 Pipeline이 보고하도록 그대로 진행시킨다.

        return False

    @staticmethod
    def _has_unclosed_block(tokens) -> bool:
        depth = 0
        for token in tokens:
            if token.type == TokenType.LEFT_BRACE:
                depth += 1
            elif token.type == TokenType.RIGHT_BRACE:
                depth -= 1
        return depth > 0


def run_cli() -> None:
    """터미널에서 한 줄씩 입력받아 실행하는 대화형 REPL 진입점.

    'exit'/'quit' 입력, EOF(Ctrl+D), Ctrl+C 중 하나로 종료한다.
    """
    shell = PromptShell()
    while True:
        try:
            line = input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if line.strip() in ("exit", "quit"):
            break

        shell.run(line)


def run_file(path: str) -> None:
    """파일 하나를 읽어 전체 내용을 한 번에 실행한다.

    파일이 없으면 명확한 오류 메시지를 출력한다. 실행 중 오류가 나면
    (Pipeline이 줄 번호를 포함해 보고하는) 메시지를 출력하고 더 진행하지 않는다.
    """
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
    except OSError as error:
        print(f"파일을 열 수 없습니다: {error}")
        return

    PromptShell().run(source)


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

    checker_errors = CheckerUnit(assembler.ast).check()
    if checker_errors:
        for error in checker_errors:
            print(error)
        return

    _debug_repl(Debugger(assembler.ast), source.splitlines())


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


def main(args=None) -> None:
    """CLI 진입점.

    사용법:
        factory              -> Prompt Shell(REPL) 모드
        factory run <파일>    -> 파일 모드 (파일 전체를 한 번에 실행)
        factory debug <파일>  -> 디버그 모드
    """
    if args is None:
        args = sys.argv[1:]

    if not args:
        run_cli()
        return

    command, *rest = args

    if command == "run":
        if not rest:
            print("사용법: run <파일 경로>")
            return
        run_file(rest[0])
    elif command == "debug":
        if not rest:
            print("사용법: debug <파일 경로>")
            return
        run_debug(rest[0])
    else:
        print(f"알 수 없는 명령입니다: {command}")
        print("사용법: (인자 없음) | run <파일 경로> | debug <파일 경로>")
