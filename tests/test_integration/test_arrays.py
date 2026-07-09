"""정적 배열 생성/인덱스 읽기·쓰기/런타임 오류 관련 블랙박스 테스트.
(요구사항_정리/정적배열.md)
"""

import textwrap


def test_array_creation_initializes_with_null(run_source):
    output = run_source(
        """
        var arr = Array(3);
        print arr;
        """
    )
    assert output == "[null, null, null]\n"


def test_array_index_write_then_read(run_source):
    output = run_source(
        """
        var arr = Array(3);
        arr[0] = 10;
        print arr[0];
        print arr;
        """
    )
    assert output == textwrap.dedent(
        """\
        10
        [10, null, null]
        """
    )


def test_array_index_update_reads_and_writes(run_source):
    output = run_source(
        """
        var arr = Array(2);
        arr[0] = 5;
        arr[0] = arr[0] + 1;
        print arr[0];
        """
    )
    assert output == "6\n"


def test_array_index_out_of_range_raises_executor_error(run_source):
    output = run_source(
        """\
        var arr = Array(2);
        print arr[5];
        """
    )
    assert output == "[Executor] Line 2: 인덱스 5는 배열 범위(0~1)를 벗어났습니다.\n"


def test_array_index_non_number_raises_executor_error(run_source):
    output = run_source(
        """\
        var arr = Array(2);
        print arr["x"];
        """
    )
    assert output == "[Executor] Line 2: 인덱스는 숫자여야 합니다. (받은 값: 'x')\n"


def test_indexing_a_non_array_value_raises_executor_error(run_source):
    output = run_source(
        """\
        var x = 10;
        print x[0];
        """
    )
    assert output == "[Executor] Line 2: [] 연산은 배열에만 사용할 수 있습니다. (받은 값: 10.0)\n"


def test_array_creation_with_non_number_size_raises_executor_error(run_source):
    """예전에는 이 오류에 토큰이 실려있지 않아 줄 번호가 항상 '?'로
    나왔는데(aeca5cc에서 수정됨), 이제는 실제 줄 번호가 나와야 한다.
    """
    output = run_source('var arr = Array("hi");')
    assert output == "[Executor] Line 1: 배열 크기는 숫자여야 합니다. (받은 값: 'hi')\n"


def test_array_variable_assignment_shares_the_same_underlying_array(run_source):
    """배열은 참조로 다뤄지므로, 같은 배열을 가리키는 다른 변수를 통해
    수정해도 원래 변수에서 그 변화가 그대로 보여야 한다.
    """
    output = run_source(
        """
        var a = Array(2);
        a[0] = 1;
        var b = a;
        b[0] = 99;
        print a[0];
        """
    )
    assert output == "99\n"


def test_array_filled_via_for_loop(run_source):
    output = run_source(
        """
        var arr = Array(3);
        for (var i = 0; i < 3; i = i + 1) {
          arr[i] = i * i;
        }
        print arr;
        """
    )
    assert output == "[0, 1, 4]\n"
