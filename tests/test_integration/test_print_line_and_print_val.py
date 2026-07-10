"""print_line; / print_val; 문장 블랙박스 테스트.

print처럼 괄호 없이 쓰는 문장 키워드다 (TokenType.PRINT_LINE/PRINT_VAL).
"""

import shutil


def test_print_line_prints_a_separator_spanning_the_terminal_width(run_source):
    output = run_source("print_line;")
    expected_width = shutil.get_terminal_size().columns
    assert output == "=" * expected_width + "\n"


def test_print_line_with_parentheses_is_a_syntax_error(run_source):
    """print_line은 더 이상 호출 가능한 값이 아니라 문장 키워드라, 괄호를 붙이면 안 된다."""
    output = run_source("print_line();")
    assert "Expected ';' after print_line" in output


def test_print_val_prints_global_variables_at_top_level(run_source):
    output = run_source(
        """
        var a = 3;
        var b = "hi";
        print_val;
        """
    )
    assert "[전역] a = 3\n" in output
    assert "[전역] b = hi\n" in output
    assert "[로컬]" not in output  # 최상위라 로컬은 없다


def test_print_val_separates_local_and_global_inside_a_block(run_source):
    output = run_source(
        """
        var a = 1;
        {
            var b = 2;
            print_val;
        }
        """
    )
    assert "[로컬] b = 2\n" in output
    assert "[전역] a = 1\n" in output


def test_print_val_shows_outer_local_scopes_too_not_just_the_innermost(run_source):
    """상위(바깥) 블록에서 선언된 변수도 [로컬]로 함께 보여야 한다."""
    output = run_source(
        """
        var g = 0;
        {
            var outer = 1;
            {
                var inner = 2;
                print_val;
            }
        }
        """
    )
    assert "[로컬] outer = 1\n" in output
    assert "[로컬] inner = 2\n" in output
    assert "[전역] g = 0\n" in output


def test_print_val_inner_scope_shadows_outer_scope_of_same_name(run_source):
    """안쪽 스코프가 같은 이름을 가리면(shadowing) 안쪽 값이 나와야 한다."""
    output = run_source(
        """
        {
            var x = 1;
            {
                var x = 2;
                print_val;
            }
        }
        """
    )
    assert "[로컬] x = 2\n" in output
    assert "[로컬] x = 1\n" not in output


def test_print_val_shows_outer_block_locals_inside_a_function(run_source):
    """함수 안에서도 파라미터 스코프뿐 아니라 바깥 블록의 지역 변수까지 [로컬]로 보여야 한다."""
    output = run_source(
        """
        Func foo(x) {
            {
                var y = 5;
                print_val;
            }
        }
        foo(9);
        """
    )
    assert "[로컬] x = 9\n" in output
    assert "[로컬] y = 5\n" in output


def test_print_val_separates_local_and_global_inside_a_function(run_source):
    output = run_source(
        """
        var g = 1;
        Func foo(x) {
            print_val;
        }
        foo(9);
        """
    )
    assert "[로컬] x = 9\n" in output
    assert "[전역] g = 1\n" in output


def test_print_val_with_parentheses_is_a_syntax_error(run_source):
    output = run_source("print_val();")
    assert "Expected ';' after print_val" in output
