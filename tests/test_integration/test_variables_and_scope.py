"""변수 선언/재할당/블록 스코프 관련 블랙박스 테스트."""

import textwrap


def test_variable_declaration_and_use(run_source):
    output = run_source(
        """
        var a = 10;
        var b = 20;
        print a + b;
        """
    )
    assert output == "30\n"


def test_variable_reassignment(run_source):
    output = run_source(
        """
        var a = 10;
        a = a + 5;
        print a;
        """
    )
    assert output == "15\n"


def test_block_scope_shadowing(run_source):
    output = run_source(
        """
        var x = "global";
        {
          var x = "inner";
          print x;
        }
        print x;
        """
    )
    assert output == textwrap.dedent(
        """\
        inner
        global
        """
    )


def test_inner_block_mutates_outer_variable(run_source):
    output = run_source(
        """
        var count = 0;
        {
          count = count + 1;
        }
        print count;
        """
    )
    assert output == "1\n"


def test_global_variable_mutated_inside_function_persists_after_call(run_source):
    # 전역 변수는 함수 호출이 끝나도 값이 유지된다(클로저는 없지만
    # 전역 dict 자체는 공유된다 - src/executor/_storage.py push_call_frame).
    output = run_source(
        """
        var count = 0;
        Func inc() { count = count + 1; }
        inc();
        inc();
        print count;
        """
    )
    assert output == "2\n"


def test_local_variable_shadowing_builtin_name_does_not_affect_global_builtin(run_source):
    output = run_source(
        """
        Func useLocalArray() {
          var Array = "shadowed";
          print Array;
        }
        useLocalArray();
        var arr = Array(2);
        arr[0] = 1;
        print arr[0];
        """
    )
    assert output == "shadowed\n1\n"


def test_nested_scope_variable_lookup_order(run_source):
    output = run_source(
        """
        var ga = 3;
        {
          var scoped = 2;
          {
            var scoped = 7;
            {
              print scoped;
              print ga;
            }
            print scoped;
          }
        }
        """
    )
    assert output == textwrap.dedent(
        """\
        7
        3
        7
        """
    )
