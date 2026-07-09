import pytest

from cli import PromptShell


@pytest.fixture
def run_source(capsys):
    """소스코드 문자열 하나를 통째로 실행하고, 표준 출력에 찍힌 텍스트를 그대로 반환한다.

    사용자가 `factory run <파일>`로 프로그램을 돌리는 것과 동일한 경로를
    타도록, cli 패키지가 공개하는 PromptShell만 사용한다(run_file()도
    내부적으로 파일을 읽어 PromptShell().run(source)를 호출할 뿐이다).
    Assembler/Checker/Executor 내부 모듈은 이 블랙박스 테스트에서
    직접 건드리지 않는다 — 오류가 나도 사용자가 터미널에서 보는 것과
    똑같은 문자열(`[Assembler] Line 1: ...` 등)이 그대로 출력에 담긴다.
    """

    def _run(source: str) -> str:
        PromptShell().run(source)
        return capsys.readouterr().out

    return _run
