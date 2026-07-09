"""Assembler(문법)/Checker(정적 검사) 단계에서 실행 전에 걸러지는 오류들의
블랙박스 테스트. 이 오류들은 Executor가 한 줄도 실행하기 전에 보고되므로,
평가 결과가 아니라 오류 메시지 자체가 곧 "결과"다.
"""


def test_invalid_assignment_target_raises_assembler_error(run_source):
    assert run_source("3 = 5;") == "[Assembler] Line 1: Invalid assignment target\n"


def test_var_declaration_without_initializer_raises_assembler_error(run_source):
    """`var a;`처럼 초기값 없는 선언은 문법상 허용되지 않는다 — `var`
    뒤에는 항상 `= expression`이 있어야 한다.
    """
    output = run_source("var a;")
    assert output == "[Assembler] Line 1: Expected '=' after variable name\n"


def test_missing_semicolon_after_var_declaration_raises_assembler_error(run_source):
    output = run_source("var a = 5")
    assert output == "[Assembler] Line 1: Expected ';' after variable declaration\n"


def test_unterminated_string_raises_assembler_error(run_source):
    """닫는 "를 못 찾고 파일이 끝나면, 마지막 글자를 잘라먹은 채 조용히
    STRING 토큰을 만들지 말고 오류를 내야 한다.
    """
    output = run_source('print "abc')
    assert output == "[Assembler] Line 1: Unterminated string\n"


def test_duplicate_parameter_names_raise_checker_error(run_source):
    output = run_source("Func f(a, a) { return a; }")
    assert output == "[Checker] Line 1: Already a variable with this name in this scope.\n"


def test_return_outside_function_raises_checker_error(run_source):
    output = run_source("return 5;")
    assert output == "[Checker] Line 1: Can't return from top-level code.\n"


def test_this_outside_class_raises_checker_error(run_source):
    output = run_source("print This;")
    assert output == "[Checker] Line 1: Can't use 'this' outside of a class.\n"


def test_super_outside_class_raises_checker_error(run_source):
    output = run_source("Super.speak();")
    assert output == "[Checker] Line 1: Can't use 'super' outside of a class.\n"


def test_class_cannot_inherit_from_itself(run_source):
    output = run_source("Class A : A { }")
    assert output == "[Checker] Line 1: A class can't inherit from itself.\n"


def test_super_in_class_without_parent_raises_checker_error(run_source):
    output = run_source("Class A { speak() { Super.speak(); } }")
    assert output == "[Checker] Line 1: Can't use 'super' in a class with no superclass.\n"


def test_initializer_cannot_return_a_value(run_source):
    output = run_source("Class A { init() { return 5; } }")
    assert output == "[Checker] Line 1: Can't return a value from an initializer.\n"


def test_static_errors_prevent_any_execution(run_source):
    """정적 오류가 있으면 그 전에 있는 print문도 실행되지 않아야 한다
    (Assembler/Checker 단계가 Executor보다 먼저 전체를 검사하기 때문에)."""
    output = run_source(
        """
        print "should not print";
        return 5;
        """
    )
    assert output == "[Checker] Line 3: Can't return from top-level code.\n"
