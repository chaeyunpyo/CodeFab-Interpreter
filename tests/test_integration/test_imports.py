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


def test_diamond_import_shares_state_across_import_sites(run_source, write_module):
    """서로 다른 두 파일(b.txt/c.txt)이 같은 파일(d.txt)을 각각 import하면,
    한쪽에서 d의 상태를 바꾼 게 다른 쪽에서도 보여야 한다 (진짜 모듈처럼
    한 번만 실행되고 상태를 공유해야 함 - 각 import 지점마다 독립적으로
    재실행되면 한쪽의 변경이 다른 쪽에 반영되지 않는다).
    """
    d_path = write_module(
        "d.txt", "var counter = 0;\nFunc inc() { counter = counter + 1; }\n"
    )
    b_path = write_module(
        "b.txt", f'import "{d_path}" alias d;\nFunc bump() {{ d.inc(); }}\n'
    )
    c_path = write_module(
        "c.txt", f'import "{d_path}" alias d;\nFunc peek() {{ return d.counter; }}\n'
    )
    output = run_source(
        f"""
        import "{b_path}" alias b;
        import "{c_path}" alias c;
        b.bump();
        b.bump();
        print c.peek();
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


# --- import 오류의 줄 번호는 "문제의 import문이 실제로 적힌 파일" 기준이다 ---
# 최상위에서 그 파일을 부른 줄도, 오류가 물리적으로 위치한 파일의 다른 줄도 아니다.

def test_import_syntax_error_reports_the_calling_imports_line_not_the_broken_lines(run_source, write_module):
    """broken.txt는 3번째 줄에서 깨지지만, 보고되는 줄 번호는 그 3이 아니라
    최상위에서 broken.txt를 부른 import문의 줄(4번째 줄)이어야 한다.
    """
    broken_path = write_module(
        "broken.txt",
        """\
        Func add(a, b) { return a + b; }
        Func sub(a, b) { return a - b; }
        var x = ;
        """,
    )
    output = run_source(
        f"""\
        print 1;
        print 2;
        print 3;
        import "{broken_path}" alias b;
        """
    )
    assert output == f"1\n2\n3\n[Import] Line 4: Imported file failed to import: {broken_path}\n"


def test_import_error_two_levels_deep_uses_the_middle_files_own_line(run_source, write_module):
    """main -> a.txt -> b.txt -> (없는 파일) 체인에서, 오류는 b.txt 자신의
    import문 줄(3번째 줄)을 기준으로 보고되어야 한다 - main이나 a.txt의
    import문 줄이 아니다. 세 파일의 import문을 서로 다른 줄에 두어
    어느 파일 기준인지 헷갈릴 수 없게 한다.
    """
    b_path = write_module(
        "b.txt",
        """\
        var pad1 = 1;
        var pad2 = 2;
        import "missing.txt" alias m;
        """,
    )
    a_path = write_module(
        "a.txt",
        """\
        var pad = 1;
        import "b.txt" alias b;
        """,
    )
    missing_path = b_path.replace("b.txt", "missing.txt")

    output = run_source(f'import "{a_path}" alias a;')
    assert output == f"[Import] Line 3: Import target file not found: {missing_path}\n"


def test_import_checker_error_deep_in_chain_uses_the_offending_files_own_line(run_source, write_module):
    """문법은 맞지만 Checker 정적 검사(여기서는 최상위 return)를 통과하지
    못하는 bad.txt가 체인 중간에 있어도, 오류는 bad.txt를 직접 import하는
    mid.txt의 import문 줄(1번째 줄) 기준이어야 한다.
    """
    bad_path = write_module(
        "bad.txt",
        """\
        var noop = 1;
        return 5;
        """,
    )
    mid_path = write_module("mid.txt", 'import "bad.txt" alias bad;\n')

    output = run_source(f'import "{mid_path}" alias mid;')
    assert output == f"[Import] Line 1: Imported file failed to import: {bad_path}\n"


# --- import 스트레스 테스트: 깊은 체인/넓은 팬아웃도 RecursionError 없이 끝까지 resolve되어야 한다 ---

def test_deeply_chained_imports_resolve_without_hitting_recursion_limit(run_source, write_module):
    """chain_0 -> chain_1 -> ... -> chain_100 처럼 100단계 깊이의 체인도
    RecursionError 없이 끝까지 resolve되고, 값이 체인을 타고 올바르게 전달되어야 한다.
    """
    depth = 100
    write_module(f"chain_{depth}.txt", f"var value = {depth};\n")
    for i in reversed(range(depth)):
        text = f"""\
        import "chain_{i + 1}.txt" alias next;
        var value = next.value;
        """
        chain_0_path = write_module(f"chain_{i}.txt", text)

    output = run_source(
        f"""\
        import "{chain_0_path}" alias root;
        print root.value;
        """
    )
    assert output == f"{depth}\n"


def test_many_sibling_imports_in_one_file_all_resolve_correctly(run_source, write_module):
    """서로 무관한 30개의 모듈을 한 파일에서 동시에 import해도(순환도
    중복도 아닌 순수 팬아웃) 전부 올바르게 resolve되어야 한다.
    """
    fan = 30
    leaf_paths = [write_module(f"leaf_{i}.txt", f"var value = {i};\n") for i in range(fan)]
    imports = "\n".join(f'import "{path}" alias m{i};' for i, path in enumerate(leaf_paths))
    total = " + ".join(f"m{i}.value" for i in range(fan))

    output = run_source(f"{imports}\nprint {total};")
    assert output == f"{sum(range(fan))}\n"


def test_long_circular_import_chain_is_detected_without_crashing(run_source, write_module, tmp_path):
    """cyc_0 -> cyc_1 -> ... -> cyc_39 -> cyc_0 처럼 40단계를 돌아 순환하는
    체인도 RecursionError로 죽지 않고 CircularImportError로 보고되어야 한다.
    """
    depth = 40
    for i in range(depth):
        write_module(f"cyc_{i}.txt", f'import "cyc_{(i + 1) % depth}.txt" alias next;\n')

    root_path = str(tmp_path / "cyc_0.txt")
    output = run_source(f'import "{root_path}" alias root;')
    assert "Circular import detected" in output
    assert "cyc_0.txt" in output
    assert "cyc_39.txt" in output


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
