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
