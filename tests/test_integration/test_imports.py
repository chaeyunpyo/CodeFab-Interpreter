"""import/alias 관련 블랙박스 테스트. (요구사항_정리/import.md)

import는 실제 파일을 읽어야 하는 유일한 기능이라, run_source만으로는
부족하다 — write_module 픽스처로 tmp_path에 실제 .txt 파일을 만들고,
그 절대 경로를 import문에 그대로 박아 넣는다(상대 경로 해석은
test_nested_import_resolves_relative_path_against_importing_file에서
따로 확인한다).
"""

import pytest


@pytest.fixture
def write_module(tmp_path):
    def _write(name: str, text: str) -> str:
        path = tmp_path / name
        path.write_text(text, encoding="utf-8")
        return str(path)

    return _write


def test_import_function_and_call_via_alias(run_source, write_module):
    sum_path = write_module("sum.txt", "Func add(a, b) { return a + b; }\n")
    output = run_source(f'import "{sum_path}" alias sum;\nprint sum.add(1, 2);')
    assert output == "3\n"


def test_import_variable_via_alias(run_source, write_module):
    consts_path = write_module("consts.txt", "var PI = 3.14;\n")
    output = run_source(f'import "{consts_path}" alias consts;\nprint consts.PI;')
    assert output == "3.14\n"


def test_import_variable_reflects_mutation_from_module_function(run_source, write_module):
    """alias.name으로 모듈 변수에 직접 접근할 때, 모듈 안 함수 호출로 바뀐
    최신 값을 봐야 한다 (namespace.fields가 import 시점 스냅샷이 아니라
    모듈의 실제 전역 스코프를 그대로 공유해야 함).
    """
    lib_path = write_module(
        "lib.txt", "var counter = 0;\nFunc inc() { counter = counter + 1; }\n"
    )
    output = run_source(
        f"""
        import "{lib_path}" alias lib;
        lib.inc();
        lib.inc();
        print lib.counter;
        """
    )
    assert output == "2\n"


def test_import_recursive_function(run_source, write_module):
    fact_path = write_module(
        "fact.txt", "Func fact(n) { if (n <= 1) return 1; return n * fact(n - 1); }\n"
    )
    output = run_source(f'import "{fact_path}" alias m;\nprint m.fact(5);')
    assert output == "120\n"


def test_class_method_calls_function_from_imported_module(run_source, write_module):
    sum_path = write_module("sum.txt", "Func add(a, b) { return a + b; }\n")
    output = run_source(
        f"""
        import "{sum_path}" alias sum;
        Class Calc {{ total(a, b) {{ return sum.add(a, b); }} }}
        var c = Calc();
        print c.total(4, 5);
        """
    )
    assert output == "9\n"


def test_import_inside_function_scope_is_allowed(run_source, write_module):
    """import문은 반복문 내부만 금지되고, 함수 본문 등 다른 곳에서는 허용된다."""
    sum_path = write_module("sum.txt", "Func add(a, b) { return a + b; }\n")
    output = run_source(
        f"""
        Func f() {{
          import "{sum_path}" alias sum;
          return sum.add(2, 3);
        }}
        print f();
        """
    )
    assert output == "5\n"


def test_nested_import_resolves_relative_path_against_importing_file(run_source, write_module):
    """a.txt가 상대 경로("b.txt")로 import하면, a.txt가 있는 디렉터리
    기준으로 풀려야 한다 (프로세스의 작업 디렉터리 기준이 아니라).
    """
    write_module("b.txt", "var y = 2;\n")
    a_path = write_module("a.txt", 'import "b.txt" alias b;\nvar x = b.y + 1;\n')
    output = run_source(f'import "{a_path}" alias a;\nprint a.x;')
    assert output == "3\n"


def test_nested_alias_is_reachable_through_outer_namespace(run_source, write_module):
    """a.txt 안에서 만든 별칭(b)도 a의 최상위 선언이므로, a를 import한
    쪽에서 a.b.y처럼 체이닝해서 접근할 수 있어야 한다.
    """
    write_module("b.txt", "var y = 2;\n")
    a_path = write_module("a.txt", 'import "b.txt" alias b;\nvar x = b.y + 1;\n')
    output = run_source(f'import "{a_path}" alias a;\nprint a.b.y;')
    assert output == "2\n"


def test_accessing_undefined_name_on_namespace_raises_executor_error(run_source, write_module):
    sum_path = write_module("sum.txt", "Func add(a, b) { return a + b; }\n")
    output = run_source(f'import "{sum_path}" alias sum;\nprint sum.missing;')
    assert output == "[Executor] Line 2: Undefined property 'missing'\n"


def test_writing_to_namespace_field_raises_executor_error(run_source, write_module):
    """네임스페이스는 읽기 전용이라 alias.name = value 형태의 대입은 허용되지 않는다."""
    sum_path = write_module("sum.txt", "Func add(a, b) { return a + b; }\n")
    output = run_source(f'import "{sum_path}" alias sum;\nsum.add = 5;')
    assert output == "[Executor] Line 2: 필드 접근은 인스턴스에만 사용할 수 있습니다.\n"


def test_importing_missing_file_reports_error_without_crashing(run_source):
    """대상 파일이 없으면 Import 오류로 깔끔하게 보고되어야 한다 (예외가
    그대로 터져 나와 프로그램이 죽으면 안 된다).
    """
    output = run_source('import "definitely_missing_file.txt" alias m;')
    assert output == "[Import] Line 1: Import target file not found: definitely_missing_file.txt\n"


def test_importing_file_with_syntax_error_reports_import_error(run_source, write_module):
    broken_path = write_module("broken.txt", "var x = ;\n")
    output = run_source(f'import "{broken_path}" alias b;')
    assert output == f"[Import] Line 1: Imported file failed to import: {broken_path}\n"


def test_importing_file_that_fails_static_checks_reports_import_error(run_source, write_module):
    """import 대상 파일 자체는 문법이 맞아도, Checker의 정적 검사(여기서는
    최상위 return)를 통과하지 못하면 같은 Import 오류로 알려야 한다.
    """
    bad_path = write_module("bad.txt", "return 5;\n")
    output = run_source(f'import "{bad_path}" alias b;')
    assert output == f"[Import] Line 1: Imported file failed to import: {bad_path}\n"


def test_circular_import_reports_error_without_crashing(run_source, write_module, tmp_path):
    a_path = str(tmp_path / "cyc_a.txt")
    write_module("cyc_b.txt", f'import "{a_path}" alias a;\n')
    write_module("cyc_a.txt", 'import "cyc_b.txt" alias b;\n')

    output = run_source(f'import "{a_path}" alias a;')
    assert "Circular import detected" in output
    assert "cyc_a.txt" in output
    assert "cyc_b.txt" in output


# --- 정적 오류 (요구사항_정리/import.md: Checker 담당분) ---
# 실제 파일이 없어도 Checker 단계에서 먼저 걸러지므로 write_module 없이도 검증 가능하다.

def test_duplicate_import_in_same_scope_raises_checker_error(run_source):
    output = run_source('import "x.txt" alias a;\nimport "x.txt" alias b;')
    assert output == "[Checker] Line 2: Already imported this file in this scope.\n"


def test_import_alias_colliding_with_existing_name_raises_checker_error(run_source):
    output = run_source('var sum = 1;\nimport "x.txt" alias sum;')
    assert output == "[Checker] Line 2: Already a variable with this name in this scope.\n"


def test_import_inside_loop_raises_checker_error(run_source):
    output = run_source('for (var i = 0; i < 1; i = i + 1) { import "x.txt" alias x; }')
    assert output == "[Checker] Line 1: Can't use import statement inside a loop.\n"


# --- import 런타임 오류가 세션을 죽이지 않고 보고되는지 (깊게 중첩된 상황) ---
# import 오류(ImportedFileNotFoundError 등)는 ExecutionError의 형제가 아니라
# 하위 타입이라, Pipeline/Debugger가 이미 갖고 있는 "except ExecutionError"
# 절에 자연스럽게 걸린다. 이 성질은 import가 얼마나 깊이 중첩된 호출
# 안에서 실행되든 똑같이 성립해야 한다.

def test_import_error_deep_inside_function_call_reports_cleanly(run_source):
    output = run_source(
        """\
        Func loadIt() {
          import "does_not_exist_xyz.txt" alias m;
          return m;
        }
        Func wrapper() { return loadIt(); }
        print wrapper();
        """
    )
    assert output == "[Import] Line 2: Import target file not found: does_not_exist_xyz.txt\n"


def test_import_error_inside_class_method_reports_cleanly(run_source):
    output = run_source(
        """\
        Class Loader {
          load() {
            import "does_not_exist_xyz.txt" alias m;
            return m;
          }
        }
        var l = Loader();
        l.load();
        """
    )
    assert output == "[Import] Line 3: Import target file not found: does_not_exist_xyz.txt\n"
