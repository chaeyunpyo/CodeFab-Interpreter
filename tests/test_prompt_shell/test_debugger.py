from assembler import Assembler
from prompt_shell import Debugger


def _statements(source):
    assembler = Assembler(source)
    assembler.execute()
    return assembler.ast


# --- step: Stmt 하나씩, 중첩 블록/분기/반복 내부까지 진입 ---

def test_step_pauses_before_each_top_level_statement():
    debugger = Debugger(_statements("var a = 1;\nvar b = 2;\n"))

    assert debugger.current_line == 1
    assert debugger.storage.exists("a") is False  # 아직 실행 전

    debugger.step()

    assert debugger.current_line == 2
    assert debugger.storage.get("a") == 1.0  # 1번째 줄은 실행됨


def test_step_enters_nested_block_statements():
    source = "{\n  var a = 1;\n  var b = 2;\n}\n"
    debugger = Debugger(_statements(source))

    assert debugger.current_line == 2
    debugger.step()
    assert debugger.current_line == 3
    debugger.step()
    assert debugger.finished is True


def test_step_reaches_end_and_marks_finished():
    debugger = Debugger(_statements("print 1;\n"))

    debugger.step()

    assert debugger.finished is True
    assert debugger.current_stmt is None


# --- next: 최상위 Stmt 전체를 한 번에, 블록 내부로 진입 X ---

def test_next_skips_over_block_interior():
    # print 3; 처럼 리터럴만 있는 문장은 Token이 안 남아 line을 못 찾으므로(_find_line 참고),
    # 줄 번호로 검증하는 이 테스트는 Token이 남는 변수 선언문을 쓴다.
    source = "{\n  var a = 1;\n  var b = 2;\n}\nvar c = 3;\n"
    debugger = Debugger(_statements(source))

    debugger.next()  # 블록 전체(내부 2개 var 포함)를 한 번에 실행

    assert debugger.current_line == 5
    assert debugger.storage.exists("a") is False  # 블록 스코프라 밖에서는 안 보임


# --- continue: 다음 breakpoint까지 실행 ---

def test_continue_stops_right_before_breakpoint_line():
    source = "var a = 1;\nvar b = 2;\nvar c = 3;\n"
    debugger = Debugger(_statements(source))
    debugger.add_breakpoint(2)

    debugger.continue_()

    assert debugger.current_line == 2  # 2번째 줄 실행 "전"에 멈춘다
    assert debugger.storage.exists("b") is False  # 아직 실행 안 됨


def test_continue_without_breakpoints_runs_to_completion():
    debugger = Debugger(_statements("var a = 1;\nvar b = 2;\n"))

    debugger.continue_()

    assert debugger.finished is True


def test_continue_snaps_to_next_statement_when_breakpoint_line_has_no_statement():
    # 2번째 줄은 주석이라 실행되는 문장이 없다. breakpoint가 정확히 그 줄과
    # 같아지는 순간은 오지 않으므로, 그 줄을 지나치는 3번째 줄에서 멈춰야 한다.
    source = "var a = 1;\n// 그냥 주석\nvar b = 2;\nvar c = 3;\n"
    debugger = Debugger(_statements(source))
    debugger.add_breakpoint(2)

    debugger.continue_()

    assert debugger.current_line == 3
    assert debugger.storage.exists("b") is False  # 아직 실행 안 됨


def test_remove_breakpoint_lets_continue_pass_through():
    source = "print 1;\nprint 2;\n"
    debugger = Debugger(_statements(source))
    debugger.add_breakpoint(2)
    debugger.remove_breakpoint(2)

    debugger.continue_()

    assert debugger.finished is True


# --- watch / inspect: 변수 저장소 직접 조회 ---

def test_watched_values_reads_directly_from_storage():
    debugger = Debugger(_statements("var a = 10;\n"))
    debugger.watch("a")

    assert debugger.watched_values() == {"a": None}  # 아직 선언 전

    debugger.step()

    assert debugger.watched_values() == {"a": 10.0}


def test_unwatch_removes_variable_from_watch_list():
    debugger = Debugger(_statements("var a = 10;\n"))
    debugger.watch("a")
    debugger.unwatch("a")

    assert debugger.watched_values() == {}


def test_inspect_returns_all_variables_in_current_scope():
    # 최상위(전역)에서 선언했으므로 local은 비고, global에 잡혀야 한다.
    debugger = Debugger(_statements("var a = 1;\nvar b = 2;\n"))
    debugger.step()
    debugger.step()

    local_items, global_items = debugger.inspect()
    assert local_items == {}
    assert global_items == {"a": 1.0, "b": 2.0}


def test_inspect_distinguishes_local_from_global_scope():
    # 블록이 var 2개를 가져야, 블록이 끝나며 스코프가 pop 되기 전에 안에서 멈출 수 있다.
    source = "var ga = 3;\n{\n  var a = 1;\n  var b = 2;\n}\n"
    debugger = Debugger(_statements(source))
    debugger.step()  # var ga = 3; 실행 -> 전역에 ga 선언
    debugger.step()  # 블록 진입, var a = 1; 실행 -> 로컬에 a 선언 (아직 블록 안)

    local_items, global_items = debugger.inspect()
    assert local_items == {"a": 1.0}
    assert global_items == {"ga": 3.0}
