"""Prompt Shell: 소스코드 한 줄을 Pipeline(Assembler -> Checker -> Executor)으로 실행하는 REPL 셸.

Public API:
    PromptShell - 소스 코드 문자열을 받아 실행하는 진입점
    run_cli     - 터미널에서 대화형으로 실행하는 CLI 진입점
    run_file    - 파일 하나를 읽어 전체 내용을 한 번에 실행
    run_debug   - Stmt 단위 stepping/breakpoint/watch 디버그 모드
    Debugger    - run_debug이 사용하는 디버그 세션 (step/next/continue/watch/inspect)
    main        - argv를 보고 모드(REPL/run/debug)를 고르는 진입점
"""

from ._debugger import Debugger
from ._prompt_shell import PromptShell, main, run_cli, run_debug, run_file

__all__ = [
    "PromptShell",
    "run_cli",
    "run_file",
    "run_debug",
    "Debugger",
    "main",
]
