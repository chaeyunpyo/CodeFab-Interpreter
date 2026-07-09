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


def test_deeply_nested_expression_raises_assembler_error_instead_of_crashing(run_source):
    """재귀 하강 파서는 중첩 한 단계마다 파이썬 함수 호출을 여러 겹
    소비하므로, 괄호를 극단적으로 깊게 중첩한 표현식은 파이썬 기본 재귀
    한도보다 훨씬 얕은 수준(중첩 100단계 안팎)에서 RecursionError로 죽을
    수 있다. Executor의 StackOverflowError와 같은 이유로, 여기서도
    RecursionError가 그대로 REPL을 죽이지 않고 깔끔한 Assembler 오류로
    보고되어야 한다.
    """
    depth = 100
    expression = "(" * depth + "1" + ")" * depth

    output = run_source(f"print {expression};")
    assert output == "[Assembler] Line 1: Expression or block nested too deeply.\n"


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


def test_reassigning_builtin_name_raises_checker_error(run_source):
    output = run_source("Array = 5;")
    assert output == "[Checker] Line 1: Cannot reassign built-in name 'Array'.\n"


def test_redeclaring_builtin_name_as_variable_raises_checker_error(run_source):
    output = run_source("var Array = 5;")
    assert output == "[Checker] Line 1: Already a variable with this name in this scope.\n"


def test_redeclaring_builtin_name_as_function_raises_checker_error(run_source):
    output = run_source("Func Array() { return 1; }")
    assert output == "[Checker] Line 1: Already a variable with this name in this scope.\n"


def test_self_referencing_initializer_raises_checker_error(run_source):
    """1일차 스펙 예시: `{ var a = a + 1; }` — 지역변수의 초기화식에서
    자기 자신(같은 이름의 바깥 변수가 아니라 아직 선언 중인 그 변수)을
    읽으려 하면 Checker가 막아야 한다.
    """
    output = run_source(
        """\
        {
          var a = a + 1;
        }
        """
    )
    assert output == "[Checker] Line 2: Can't read local variable in initializer.\n"


def test_static_errors_prevent_any_execution(run_source):
    """정적 오류가 있으면 그 전에 있는 print문도 실행되지 않아야 한다
    (Assembler/Checker 단계가 Executor보다 먼저 전체를 검사하기 때문에)."""
    output = run_source(
        """\
        print "should not print";
        return 5;
        """
    )
    assert output == "[Checker] Line 2: Can't return from top-level code.\n"
