import pytest

from prompt_shell import PromptShell, run_cli


# --- 0단계: 가장 단순한 케이스 (print 문 한 줄을 실행하면 결과가 출력되어야 한다) ---

def test_step0_runs_print_statement_and_outputs_value(capsys):
    """PromptShell.run()에 소스 한 줄을 넣으면 Pipeline을 거쳐 표준출력에 결과가 찍혀야 한다."""
    shell = PromptShell()
    shell.run("print 1;")

    assert capsys.readouterr().out == "1\n"

# --- 1단계: 변수 선언 후 사용 (PDF p.17: 한 줄 입력마다 파이프라인이 수행되고, 상태는 유지되어야 한다) ---

def test_step1_declares_variable_then_uses_it_on_a_later_line(capsys):
    """var a = 10; 을 실행한 뒤, 다른 줄에서 print a; 를 실행해도 이전에 선언한 값을 읽을 수 있어야 한다."""
    shell = PromptShell()
    shell.run("var a = 10;")
    shell.run("print a;")

    assert capsys.readouterr().out == "10\n"

# --- 2단계: 미정의 변수 참조 (PDF p.87: 셸이 죽지 않고 에러 메시지를 출력해야 한다) ---

def test_step2_undefined_variable_reference_does_not_crash_the_shell(capsys):
    """선언한 적 없는 변수를 참조하면, 예외가 그대로 튀어나오는 게 아니라
    셸이 잡아서 에러 메시지를 출력하고 계속 살아있어야 한다."""
    shell = PromptShell()
    shell.run("print notDefined;")

    assert "notDefined" in capsys.readouterr().out

# --- 3단계: Checker 에러 (PDF p.73: 자기참조 초기화도 셸이 죽지 않고 메시지를 출력해야 한다) ---

def test_step3_checker_error_reports_message_without_crashing(capsys):
    """var a = a; 처럼 초기화식이 자기 자신을 참조하는 Checker 에러가 나면,
    셸이 죽지 않고 에러 메시지가 출력되어야 한다."""
    shell = PromptShell()
    shell.run("{ var a = a; }")

    assert "initializer" in capsys.readouterr().out

# --- 4단계: 재할당 (PDF 테스트 스크립트: var a = 10; a = a + 5; print a; -> 15) ---

def test_step4_reassigns_variable_across_lines(capsys):
    """이미 선언된 변수를 다른 줄에서 재할당하면, 이후 참조에 새 값이 반영되어야 한다."""
    shell = PromptShell()
    shell.run("var a = 10;")
    shell.run("a = a + 5;")
    shell.run("print a;")

    assert capsys.readouterr().out == "15\n"

# --- 5단계: 잘못된 대입 대상 (재할당의 엣지케이스, PDF 참고 gist: a + b = 3; -> 에러) ---

def test_step5_invalid_assignment_target_does_not_crash_the_shell(capsys):
    """a + b = 3; 처럼 변수가 아닌 표현식에 대입하려 하면 Assembler 단계에서 실패하는데,
    셸이 죽지 않고 에러 메시지를 출력하고 계속 살아있어야 한다."""
    shell = PromptShell()
    shell.run("var a = 1;")
    shell.run("var b = 2;")
    shell.run("a + b = 3;")

    assert "assignment" in capsys.readouterr().out.lower()

# --- 6단계: 구문 오류 - 세미콜론/괄호 누락 (PDF 참고 gist 에러 케이스) ---

@pytest.mark.parametrize(
    "source",
    [
        "print 1 + 2",       # 세미콜론 누락
        "print (1 + 2;",     # 닫는 괄호 누락
        "print * 5;",        # 표현식이 와야 할 자리에 엉뚱한 토큰
    ],
)
def test_step6_syntax_error_does_not_crash_the_shell(source, capsys):
    """세미콜론/괄호 누락 등 구문 오류가 나도 셸이 죽지 않고 이후에도 계속 사용할 수 있어야 한다."""
    shell = PromptShell()
    shell.run(source)
    shell.run("print 1;")

    assert capsys.readouterr().out.endswith("1\n")

# --- 6-1단계: 에러 메시지에 줄 번호가 포함되어야 한다 (PDF p.73/86/87/88 공통 요구사항) ---

def test_step6_1_runtime_error_message_includes_line_number(capsys):
    """2번째 줄에서 미정의 변수를 참조하면, 에러 메시지에 줄 번호(Line 2)가 포함되어야 한다.
    (SourceError.__str__ 이 "[Unit] Line N: message" 형식을 만들어준다.)"""
    shell = PromptShell()
    shell.run("print 1;\nprint notDefined;")

    assert "Line 2" in capsys.readouterr().out

# --- 7단계: 런타임 타입 불일치 (PDF p.86: true * false, 3 - "hello") ---

@pytest.mark.parametrize(
    "source",
    [
        "print true * false;",   # Boolean 타입에 대해 * 연산은 지원하지 않는다
        'print 3 - "hello";',    # 숫자 - 문자열은 불가능하다
    ],
)
def test_step7_type_mismatch_does_not_crash_the_shell(source, capsys):
    """피연산자 타입이 안 맞는 연산을 실행해도 셸이 죽지 않고 이후에도 계속 사용할 수 있어야 한다."""
    shell = PromptShell()
    shell.run(source)
    shell.run("print 1;")

    assert capsys.readouterr().out.endswith("1\n")

# --- 8단계: 블록 스코프 shadowing을 한 줄씩(real REPL처럼) 입력하는 경우 ---

def test_step8_block_scope_shadowing_line_by_line(capsys):
    """PDF p.17: 한 줄 입력받을 때마다 파이프라인이 수행된다 -> 여러 줄에 걸친 블록도
    한 줄씩 run()에 넣었을 때 shadowing이 올바르게 동작해야 한다 (inner -> global 순으로 출력)."""
    shell = PromptShell()
    shell.run('var x = "global";')
    shell.run("{")
    shell.run('var x = "inner";')
    shell.run("print x;")
    shell.run("}")
    shell.run("print x;")

    assert capsys.readouterr().out == "inner\nglobal\n"

# --- 9단계: 중첩 블록/dangling else (PDF 참고 gist: else는 가장 가까운 if에 결합, 기대: bbq) ---

def test_step9_dangling_else_in_nested_block_line_by_line(capsys):
    """PDF 참고 gist 원문 형식대로 'if (true)' 다음 줄에 '{' 가 오는 경우도
    (then_branch 없이 끝난 if는 다음 줄을 기다리는 로직 덕분에) 정상 동작해야 한다."""
    shell = PromptShell()
    shell.run("if (true)")
    shell.run("{")
    shell.run('if (false) print "kfc";')
    shell.run('else print "bbq";')
    shell.run("}")

    assert capsys.readouterr().out == "bbq\n"

# --- 10단계: else는 반드시 '}'와 같은 줄에 붙여 써야 한다 ---
#
# else 없는 if로 끝난 입력을 계속 대기시키면 step9와 정면 충돌한다: "if (true) { ... }" 까지만
# 입력되고 더 이상 줄이 없을 때는 즉시 확정 실행되어야 하므로, "혹시 다음 줄에 else가 올 수도
# 있다"며 무기한 대기할 수 없다. 이 REPL은 dangling else를 여러 줄에 걸쳐 나중에 붙이는 것을
# 지원하지 않는다. 대신 '} else' 처럼 같은 줄에 붙여 쓰면 브레이스 depth가 0으로 돌아오기
# 전에 else까지 같이 소비되어 정상 동작한다.

def test_step10_else_must_be_on_the_same_line_as_closing_brace(capsys):
    """'}'와 'else'를 같은 줄에 붙여 쓰면(흔한 K&R 스타일), 중첩 스코프에서도 정상 동작해야 한다."""
    shell = PromptShell()
    shell.run("if (false)")
    shell.run("{")
    shell.run("print 1;")
    shell.run("} else")
    shell.run("{")
    shell.run("print 2;")
    shell.run("}")

    assert capsys.readouterr().out == "2\n"

# --- 11단계: 중첩 스코프 변수 조회 순서 (PDF p.84: 현재 -> 상위 -> ... -> Global) ---

def test_step11_nested_scope_variable_lookup_order_line_by_line(capsys):
    """가장 안쪽 스코프부터 바깥으로 거슬러 올라가며 변수를 찾아야 한다.
    한 줄씩 입력해도(real REPL처럼) 임의 깊이의 중첩 스코프가 올바르게 동작해야 한다."""
    shell = PromptShell()
    shell.run("var ga = 3;")
    shell.run("{")
    shell.run("var a = 2;")
    shell.run("{")
    shell.run("var a = 7;")
    shell.run("{")
    shell.run("print a;")
    shell.run("print ga;")
    shell.run("}")
    shell.run("print a;")
    shell.run("}")
    shell.run("}")

    assert capsys.readouterr().out == "7\n3\n7\n"

# --- 12단계: 문자열 연결 (PDF 참고 gist: "Hello, " + "CodeFab!" -> Hello, CodeFab!) ---

def test_step12_string_concatenation(capsys):
    """+ 연산자로 문자열 두 개를 이어붙일 수 있어야 한다."""
    shell = PromptShell()
    shell.run('print "Hello, " + "CodeFab!";')

    assert capsys.readouterr().out == "Hello, CodeFab!\n"

# --- 13단계: run_cli() - 실제 터미널 진입점 (PDF 목표 3: Prompt Shell/CLI Shell 제작) ---

def test_step13_run_cli_executes_each_input_line(monkeypatch, capsys):
    """input()으로 한 줄씩 받아 즉시 실행하고, 상태가 여러 줄에 걸쳐 유지되어야 한다."""
    lines = iter(["var a = 10;", "print a;", "exit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(lines))

    run_cli()

    assert capsys.readouterr().out == "10\n"


def test_step13_run_cli_stops_on_eof(monkeypatch, capsys):
    """더 이상 입력이 없어 EOFError(Ctrl+D)가 나면 예외 없이 종료해야 한다."""
    lines = iter(["print 1;"])

    def fake_input(prompt=""):
        try:
            return next(lines)
        except StopIteration:
            raise EOFError

    monkeypatch.setattr("builtins.input", fake_input)

    run_cli()

    # EOF를 만나면 커서를 다음 줄로 넘기기 위한 개행이 하나 더 찍힌다 (터미널 UX).
    assert capsys.readouterr().out == "1\n\n"
