"""if/else, dangling else, for 반복문 관련 블랙박스 테스트."""

import textwrap


def test_if_else(run_source):
    assert run_source('if (true) print "bbq";') == "bbq\n"
    assert run_source('if (false) print "no"; else print "kfc";') == "kfc\n"


def test_dangling_else_binds_to_nearest_if(run_source):
    output = run_source(
        """
        if (true)
        {
          if (false) print "kfc";
          else print "bbq";
        }
        """
    )
    assert output == "bbq\n"


def test_for_loop_prints_each_iteration(run_source):
    output = run_source("for (var j = 0; j < 3; j = j + 1) { print j; }")
    assert output == textwrap.dedent(
        """\
        0
        1
        2
        """
    )


def test_for_loop_mutates_outer_scope_variable(run_source):
    output = run_source(
        """
        var total = 0;
        for (var i = 0; i < 5; i = i + 1) {
          total = total + i;
        }
        print total;
        """
    )
    assert output == "10\n"


def test_for_loop_with_omitted_initializer_and_increment(run_source):
    """초기식/증감식은 생략 가능하다 — 조건식만으로도 while처럼 동작해야 한다."""
    output = run_source(
        """
        var i = 0;
        for (; i < 3;) { print i; i = i + 1; }
        """
    )
    assert output == textwrap.dedent(
        """\
        0
        1
        2
        """
    )


def test_nested_for_loops(run_source):
    output = run_source(
        """
        for (var i = 1; i <= 2; i = i + 1) {
          for (var j = 1; j <= 2; j = j + 1) {
            print i * j;
          }
        }
        """
    )
    assert output == textwrap.dedent(
        """\
        1
        2
        2
        4
        """
    )


def test_if_without_else_produces_no_output_when_condition_is_false(run_source):
    assert run_source('if (false) print "unreachable";') == ""
