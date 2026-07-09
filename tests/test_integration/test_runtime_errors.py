"""특정 기능에 묶이지 않는 일반 런타임(Executor) 오류 블랙박스 테스트.

배열/클래스 전용 런타임 오류는 각각 test_arrays.py/test_classes.py에 있다.
"""

import textwrap


def test_division_by_zero_raises_executor_error(run_source):
    assert run_source("print 1 / 0;") == "[Executor] Line 1: 0으로 나눌 수 없습니다.\n"


def test_reading_undefined_variable_raises_executor_error(run_source):
    assert run_source("print y;") == "[Executor] Line 1: Undefined variable 'y'\n"


def test_assigning_to_undefined_variable_raises_executor_error(run_source):
    assert run_source("z = 5;") == "[Executor] Line 1: Undefined variable 'z'\n"


def test_type_mismatch_between_number_and_boolean_raises_executor_error(run_source):
    assert run_source("print 1 + true;") == "[Executor] Line 1: 피연산자는 반드시 숫자여야 합니다.\n"


def test_arithmetic_between_string_and_number_raises_executor_error(run_source):
    """+는 문자열 연결에만 쓰이고, -/*//는 문자열에는 쓸 수 없다."""
    assert run_source('print "a" - 1;') == "[Executor] Line 1: 피연산자는 반드시 숫자여야 합니다.\n"


def test_line_numbers_stay_correct_after_a_multiline_string_literal(run_source):
    """문자열 리터럴 내부의 개행도 줄 번호에 반영되어야 한다. 그렇지
    않으면 이 문자열 뒤에 오는 모든 문장의 줄 번호가 실제보다 하나
    앞선 것으로 나온다. 여기서는 \\n을 실제 개행으로 그대로 써서
    (일반 문자열 이어붙이기가 아니라) "문자열 리터럴 안의 개행"이라는
    시나리오 자체를 명확하게 표현한다.
    """
    output = run_source('var s = "line1\nline2";\nprint s;\nprint 1 / 0;')
    assert output == textwrap.dedent(
        """\
        line1
        line2
        [Executor] Line 4: 0으로 나눌 수 없습니다.
        """
    )


def test_execution_stops_after_the_first_runtime_error(run_source):
    """오류가 난 문장 이전까지는 출력되고, 오류 문장부터는 더 진행되지 않아야 한다."""
    output = run_source(
        """\
        print "before";
        print 1 / 0;
        print "after";
        """
    )
    assert output == textwrap.dedent(
        """\
        before
        [Executor] Line 2: 0으로 나눌 수 없습니다.
        """
    )
