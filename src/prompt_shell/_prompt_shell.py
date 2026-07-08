import sys

from assembler import AstBuilder, Tokenizer, UnexpectedTokenError
from nodes.token_type import TokenType
from pipeline import Pipeline


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

    아직 구현되지 않았다 (자리표시자).
    """
    print(f"디버그 모드는 아직 구현되지 않았습니다: {path}")


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
