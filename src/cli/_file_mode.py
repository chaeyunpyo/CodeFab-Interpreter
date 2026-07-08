from ._repl import PromptShell


def run_file(path: str) -> None:
    """파일 하나를 읽어 전체 내용을 한 번에 실행한다 (파일 모드).

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
