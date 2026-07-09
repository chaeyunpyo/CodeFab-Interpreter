from pipeline import Pipeline


def run_file(path: str) -> None:
    """파일 하나를 읽어 전체 내용을 한 번에 실행한다 (파일 모드).

    파일이 없으면 명확한 오류 메시지를 출력한다. 실행 중 오류가 나면
    (Pipeline이 줄 번호를 포함해 보고하는) 메시지를 출력하고 더 진행하지 않는다.

    PromptShell이 아니라 Pipeline을 직접 쓴다: PromptShell.run()의 "입력을
    더 기다린다" 판단은 다음 줄이 더 올 수 있는 REPL 전제 위에서만 의미가
    있는데, 파일 모드는 파일 전체를 이미 한 번에 다 읽은 상태라 그 전제가
    성립하지 않는다. 그 판단을 그대로 썼다면, 짝이 안 맞는 '{'처럼 실제로는
    끝난 파일을 "아직 안 끝났다"고 보고 아무 것도 출력하지 않은 채 조용히
    반환해버린다.
    """
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
    except OSError as error:
        print(f"파일을 열 수 없습니다: {error}")
        return

    for error in Pipeline().run(source):
        print(error)
