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
