import sys

from ._debug_mode import run_debug
from ._file_mode import run_file
from ._repl import run_cli


def main(args=None) -> None:
    """CLI 진입점. 세 가지 실행 방식을 argv로 고른다.

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
