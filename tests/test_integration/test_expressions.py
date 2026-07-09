"""표현식 관련 블랙박스 테스트: 산술/비교/논리/문자열/숫자 출력 형식.

요구사항_정리 문서에 묶이지 않는, 언어의 기본 문법(PDF 기준) 영역이다.
"""


def test_arithmetic_operator_precedence(run_source):
    assert run_source("print 1 + 2 * 3;") == "7\n"
    assert run_source("print (1 + 2) * 3;") == "9\n"
    assert run_source("print 10 - 4 - 3;") == "3\n"
    assert run_source("print 8 / 2 / 2;") == "2\n"


def test_unary_operators(run_source):
    assert run_source("print -3 + 2;") == "-1\n"
    assert run_source("print !true;") == "false\n"
    assert run_source("print !false;") == "true\n"


def test_comparison_operators(run_source):
    assert run_source("print 1 < 2;") == "true\n"
    assert run_source("print 3 > 5;") == "false\n"
    assert run_source("print 3 == 3;") == "true\n"
    assert run_source("print 3 != 3;") == "false\n"
    assert run_source("print 3 >= 3;") == "true\n"
    assert run_source("print 2 <= 1;") == "false\n"


def test_string_concatenation(run_source):
    assert run_source('print "Hello, " + "CodeFab!";') == "Hello, CodeFab!\n"


def test_number_formatting_drops_trailing_zero(run_source):
    """정수 값을 갖는 float은 5.0이 아니라 5로 출력해야 한다."""
    assert run_source("print 5;") == "5\n"
    assert run_source("print 5.0;") == "5\n"
    assert run_source("print 3.14;") == "3.14\n"


def test_boolean_literals_and_logical_operators(run_source):
    assert run_source("print true;") == "true\n"
    assert run_source("print false;") == "false\n"
    assert run_source("print true and false;") == "false\n"
    assert run_source("print true or false;") == "true\n"


def test_boolean_literal_keywords_are_case_sensitive(run_source):
    """true/false만 유효한 키워드다 (요구사항_정리/TokenType.md 참고).
    True/False로 쓰면 예약어가 아니라 그냥 식별자로 취급되어, 값을
    대입하기 전에는 정의되지 않은 변수 오류가 나야 한다.
    """
    assert run_source("print True;") == "[Executor] Line 1: Undefined variable 'True'\n"


def test_logical_operators_short_circuit(run_source):
    """and의 좌변이 false면, or의 좌변이 true면 우변을 평가하지 않아야
    하므로 우변의 대입(부작용)이 일어나지 않아야 한다.
    """
    output = run_source(
        """
        var log = "not called";
        false and (log = "called");
        print log;
        """
    )
    assert output == "not called\n"

    output = run_source(
        """
        var log = "not called";
        true or (log = "called");
        print log;
        """
    )
    assert output == "not called\n"


def test_grouping_overrides_precedence(run_source):
    assert run_source("print (2 + 3) * (4 - 1);") == "15\n"


def test_double_unary_negation(run_source):
    assert run_source("print - -5;") == "5\n"


def test_assignment_expression_evaluates_to_the_assigned_value(run_source):
    """대입(=)도 표현식이라 값으로 쓰일 수 있어야 한다 — print(a = 5)는
    a에 5를 대입한 뒤 그 5를 그대로 print의 값으로 써야 한다.
    """
    output = run_source("var a = 0;\nprint (a = 5);")
    assert output == "5\n"


def test_comparison_operators_require_numeric_operands(run_source):
    """비교 연산자(==, <, > 등)는 문자열끼리는 지원하지 않고 숫자만
    받는다 — 문자열은 +로 연결(concat)만 가능하다.
    """
    assert run_source('print "a" == "a";') == "[Executor] Line 1: 피연산자는 반드시 숫자여야 합니다.\n"
    assert run_source('print "a" < "b";') == "[Executor] Line 1: 피연산자는 반드시 숫자여야 합니다.\n"
