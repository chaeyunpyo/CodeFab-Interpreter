"""Prompt Shell: 소스코드 한 줄을 Pipeline(Assembler -> Checker -> Executor)으로 실행하는 REPL 셸.

Public API:
    PromptShell - 소스 코드 문자열을 받아 실행하는 진입점
    run_cli     - 터미널에서 대화형으로 실행하는 CLI 진입점
"""

from ._prompt_shell import PromptShell, run_cli

__all__ = [
    "PromptShell",
    "run_cli",
]
