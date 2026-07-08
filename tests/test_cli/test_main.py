from cli import main


# --- main(args) - argv 기반 모드 분기 (factory / factory run <파일> / factory debug <파일>) ---

def test_main_with_no_args_runs_prompt_shell(monkeypatch, capsys):
    """인자 없이 실행하면(factory) Prompt Shell(REPL) 모드로 진입해야 한다."""
    inputs = iter(["print 1;", "exit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    main([])

    assert capsys.readouterr().out.endswith("1\n")


def test_main_run_command_executes_file(tmp_path, capsys):
    """factory run <파일>은 해당 파일을 파일 모드로 실행해야 한다."""
    script = tmp_path / "script.txt"
    script.write_text("print 42;\n", encoding="utf-8")

    main(["run", str(script)])

    assert capsys.readouterr().out == "42\n"


def test_main_run_command_without_path_shows_usage(capsys):
    """factory run (파일 경로 없이)은 크래시 없이 사용법 메시지를 출력해야 한다."""
    main(["run"])

    assert capsys.readouterr().out != ""


def test_main_debug_command_enters_debug_repl(monkeypatch, tmp_path, capsys):
    """factory debug <파일>은 디버그 모드로 진입해서 명령을 받아야 한다."""
    script = tmp_path / "script.txt"
    script.write_text("var a = 1;\n", encoding="utf-8")
    monkeypatch.setattr("builtins.input", lambda prompt="": "exit")

    main(["debug", str(script)])

    out = capsys.readouterr().out
    assert f"[DEBUG] 소스코드 로딩: {script}" in out
    assert "[DEBUG] 1번째 줄에서 정지 -> var a = 1;" in out


def test_main_unknown_command_shows_usage_without_crashing(capsys):
    """알 수 없는 명령을 줘도 크래시 없이 사용법 메시지를 출력해야 한다."""
    main(["foo"])

    assert capsys.readouterr().out != ""
