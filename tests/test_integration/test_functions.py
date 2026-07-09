"""함수 선언/호출/return/재귀 관련 블랙박스 테스트. (요구사항_정리/function.md)"""

import textwrap


def test_function_declaration_and_call(run_source):
    output = run_source(
        """
        Func add(a, b) { return a + b; }
        print add(1, 2);
        """
    )
    assert output == "3\n"


def test_function_without_return_yields_null(run_source):
    output = run_source(
        """
        Func f() { }
        print f();
        """
    )
    assert output == "null\n"


def test_recursive_function(run_source):
    output = run_source(
        """
        Func fact(n) { if (n <= 1) return 1; return n * fact(n - 1); }
        print fact(5);
        """
    )
    assert output == "120\n"


def test_too_deep_recursion_reports_stack_overflow_instead_of_crashing(run_source):
    """Function.call()이 호출마다 파이썬 자체 콜스택을 소비하기 때문에,
    언어 레벨 재귀 깊이는 파이썬 기본 재귀 한도(1000)보다 훨씬 얕은
    수준(대략 100단계 안팎)에서 이미 바닥난다. 94315c8 이전에는 여기서
    처리되지 않은 RecursionError가 그대로 터져 나와 REPL 전체가
    죽었지만, 지금은 StackOverflowError(ExecutionError)로 감싸져 다른
    런타임 오류와 똑같이 깔끔한 오류 메시지로 보고되어야 한다.
    """
    output = run_source(
        """
        Func count(n) {
          if (n <= 0) return 0;
          return 1 + count(n - 1);
        }
        print count(150);
        """
    )
    assert output == "[Executor] Line 4: Recursion too deep.\n"


def test_nested_function_calls(run_source):
    output = run_source(
        """
        Func square(x) { return x * x; }
        Func sumSquares(a, b) { return square(a) + square(b); }
        print sumSquares(3, 4);
        """
    )
    assert output == "25\n"


def test_function_parameter_visible_throughout_body(run_source):
    output = run_source(
        """
        Func f(x) { print x; return x + 1; }
        print f(5);
        """
    )
    assert output == textwrap.dedent(
        """\
        5
        6
        """
    )


def test_calling_a_non_callable_value_raises_executor_error(run_source):
    output = run_source(
        """\
        var x = 1;
        x();
        """
    )
    assert output == "[Executor] Line 2: Can only call functions.\n"


def test_calling_function_with_wrong_argument_count_raises_executor_error(run_source):
    output = run_source(
        """\
        Func add(a, b) { return a + b; }
        add(1);
        """
    )
    assert output == "[Executor] Line 2: Expected 2 arguments but got 1.\n"


def test_mutual_recursion_between_two_functions(run_source):
    output = run_source(
        """
        Func isEven(n) { if (n == 0) return true; return isOdd(n - 1); }
        Func isOdd(n) { if (n == 0) return false; return isEven(n - 1); }
        print isEven(4);
        print isOdd(4);
        """
    )
    assert output == textwrap.dedent(
        """\
        true
        false
        """
    )


def test_function_reads_global_variable(run_source):
    output = run_source(
        """
        var g = 100;
        Func f() { return g + 1; }
        print f();
        """
    )
    assert output == "101\n"


def test_function_writes_to_global_variable_persist_after_call_returns(run_source):
    """함수는 클로저가 없어 지역 스코프 체인은 호출마다 초기화되지만,
    전역 변수는 진짜 "전역"이라 함수 안에서 대입한 값이 호출이 끝난
    뒤에도(return 없이도) 그대로 유지되어야 한다.
    """
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


def test_function_with_multiple_return_points(run_source):
    output = run_source(
        """
        Func sign(n) {
          if (n > 0) return 1;
          if (n < 0) return -1;
          return 0;
        }
        print sign(5);
        print sign(-5);
        print sign(0);
        """
    )
    assert output == textwrap.dedent(
        """\
        1
        -1
        0
        """
    )
