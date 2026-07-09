from cli import run_file


# --- run_file() - 파일 하나를 통째로 읽어 한 번에 실행 ---

def test_run_file_executes_whole_file_at_once(tmp_path, capsys):
    """파일 내용을 한 번에 읽어 실행하면, 여러 줄에 걸친 블록도 정상 동작해야 한다."""
    script = tmp_path / "script.txt"
    script.write_text(
        'var x = "global";\n'
        "{\n"
        '  var x = "inner";\n'
        "  print x;\n"
        "}\n"
        "print x;\n",
        encoding="utf-8",
    )

    run_file(str(script))

    assert capsys.readouterr().out == "inner\nglobal\n"


def test_run_file_reports_missing_file_without_crashing(capsys):
    """존재하지 않는 파일 경로를 주면, 예외가 그대로 튀어나오지 않고 메시지만 출력해야 한다."""
    run_file("이런_파일은_없다.txt")

    assert capsys.readouterr().out != ""


def test_run_file_reports_error_for_unclosed_block_instead_of_silently_returning(tmp_path, capsys):
    """'{' 짝이 안 맞아 파일이 끝나면, 조용히 무시하지 말고 오류를 출력해야 한다.

    PromptShell의 "다음 줄을 더 기다린다" 판단(REPL 전제)을 파일 모드에
    그대로 적용하면, 파일이 이미 다 읽혔는데도 계속 기다리는 것으로
    오판해 아무 출력도 없이 그냥 반환해버리는 버그가 있었다.
    """
    script = tmp_path / "script.txt"
    script.write_text('print 1;\nif (true) {\n', encoding="utf-8")

    run_file(str(script))

    assert capsys.readouterr().out != ""


def test_run_file_reports_error_for_if_without_body_at_eof(tmp_path, capsys):
    """then_branch 없이 파일이 끝난 if문도 조용히 무시하지 말고 오류를 출력해야 한다."""
    script = tmp_path / "script.txt"
    script.write_text("if (true)", encoding="utf-8")

    run_file(str(script))

    assert capsys.readouterr().out != ""
