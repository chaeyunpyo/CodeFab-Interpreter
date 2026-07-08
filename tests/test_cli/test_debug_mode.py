from cli import run_debug


# --- run_debug() - 디버그 모드 REPL (step/next/continue/break/watch/inspect) ---

def test_run_debug_reports_missing_file_without_crashing(capsys):
    """존재하지 않는 파일을 주면 크래시 없이 메시지만 출력해야 한다."""
    run_debug("이런_파일은_없다.ez")

    assert capsys.readouterr().out != ""


def test_run_debug_runtime_error_during_step_does_not_crash_the_session(
    monkeypatch, tmp_path, capsys
):
    """step 도중 런타임 오류(미정의 변수 등)가 나도 세션이 죽지 않고 메시지만 출력해야 한다."""
    script = tmp_path / "script.txt"
    script.write_text("print 1;\nprint notDefined;\nprint 3;\n", encoding="utf-8")
    inputs = iter(["step", "step", "step", "exit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    run_debug(str(script))  # 예외가 여기서 그대로 튀어나오면 테스트 자체가 실패한다

    out = capsys.readouterr().out
    assert "Undefined variable" in out
    assert "[DEBUG] 실행 종료" in out


def test_run_debug_step_executes_one_statement_at_a_time(monkeypatch, tmp_path, capsys):
    """step 명령마다 Stmt 하나씩 실행되어야 한다 (print 문이 하나씩 출력됨)."""
    script = tmp_path / "script.txt"
    script.write_text("print 1;\nprint 2;\n", encoding="utf-8")
    inputs = iter(["step", "step", "exit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    run_debug(str(script))

    out = capsys.readouterr().out
    assert "1\n" in out
    assert "2\n" in out


def test_run_debug_watch_prints_variable_value_after_each_step(monkeypatch, tmp_path, capsys):
    """watch로 등록한 변수는 정지할 때마다 자동으로 값이 출력되어야 한다."""
    script = tmp_path / "script.txt"
    script.write_text("var a = 1;\na = a + 1;\n", encoding="utf-8")
    inputs = iter(["watch a", "step", "step", "exit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    run_debug(str(script))

    out = capsys.readouterr().out
    assert "[WATCH] a = 2.0" in out


def test_run_debug_break_and_continue_stops_at_breakpoint(monkeypatch, tmp_path, capsys):
    """break <줄번호> 이후 continue는 해당 줄 직전에서 멈춰야 한다."""
    # print 1; 처럼 리터럴만 있는 문장도 이제 파서가 line을 직접 기록해서 정확히 동작한다.
    script = tmp_path / "script.txt"
    script.write_text("var a = 1;\nprint a;\nprint a;\n", encoding="utf-8")
    inputs = iter(["break 3", "continue", "exit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    run_debug(str(script))

    out = capsys.readouterr().out
    assert out.count("1\n") == 1  # 2번째 줄까지만 실행되고 3번째 줄 직전에 멈췄다
    assert "[DEBUG] 3번째 줄에서 정지 -> print a;" in out


def test_run_debug_inspect_prints_current_scope_variables(monkeypatch, tmp_path, capsys):
    """inspect는 현재 스코프의 모든 변수와 값을 출력해야 한다."""
    script = tmp_path / "script.txt"
    script.write_text("var a = 1;\nvar b = 2;\n", encoding="utf-8")
    inputs = iter(["step", "step", "inspect", "exit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    run_debug(str(script))

    out = capsys.readouterr().out
    assert "[전역] a = 1.0" in out
    assert "[전역] b = 2.0" in out
    assert "[로컬] (없음 - 현재 블록 스코프 안이 아님)" in out  # 최상위라 로컬은 없다


def test_run_debug_inspect_shows_local_variables_inside_a_block(monkeypatch, tmp_path, capsys):
    """블록 안에 멈춰 있을 때 inspect는 [로컬]에 블록 스코프 변수를 보여줘야 한다."""
    script = tmp_path / "script.txt"
    script.write_text("var ga = 3;\n{\n  var a = 1;\n  var b = 2;\n}\n", encoding="utf-8")
    inputs = iter(["step", "step", "inspect", "exit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    run_debug(str(script))

    out = capsys.readouterr().out
    assert "[로컬] a = 1.0" in out
    assert "[전역] ga = 3.0" in out
    assert "[로컬] b" not in out  # b는 아직 선언 전
