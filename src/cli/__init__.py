"""CLI: Interpreter Factory를 실행하는 3가지 방식 (요구사항_정리/공장제어쉘.md).

    factory              -> Prompt Shell(REPL) 모드   (_repl.py)
    factory run <파일>    -> 파일 모드                 (_file_mode.py)
    factory debug <파일>  -> 디버그 모드                (_debug_mode.py)

Public API:
    main        - argv를 보고 세 모드 중 하나로 진입하는 진입점
    PromptShell - REPL 모드가 쓰는, 소스 한 줄을 실행하는 엔진
    run_cli     - Prompt Shell(REPL) 모드
    run_file    - 파일 모드
    run_debug   - 디버그 모드
    Debugger    - 디버그 모드가 쓰는 Stmt 단위 stepping/breakpoint/watch 세션
"""

from ._debug_mode import Debugger, run_debug
from ._file_mode import run_file
from ._main import main
from ._repl import PromptShell, run_cli

__all__ = [
    "main",
    "PromptShell",
    "run_cli",
    "run_file",
    "run_debug",
    "Debugger",
]
