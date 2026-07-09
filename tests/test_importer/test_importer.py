import pytest

from assembler import AssemblerError
from checker import CheckerError
from nodes import FunctionStmt, ReturnStmt, VarDeclStmt
from nodes.token_type import TokenType
from importer import CircularImportError, ImportedFileNotFoundError, Importer, ModuleImportError


def _write(path, text):
    path.write_text(text, encoding="utf-8")
    return str(path)


# --- assemble + check (Facade) ---

def test_import_module_assembles_and_checks_valid_file(tmp_path):
    """import 대상 파일을 Assembler로 파싱하고 Checker까지 통과한 Stmt 목록을 반환해야 한다."""
    path = _write(tmp_path / "sum.txt", "Func add(a, b) { return a + b; }\n")

    statements = Importer().import_module(path)

    assert len(statements) == 1
    assert isinstance(statements[0], FunctionStmt)
    assert statements[0].name.lexeme == "add"
    assert isinstance(statements[0].body[0], ReturnStmt)


def test_import_module_wraps_assembler_syntax_errors_in_module_import_error(tmp_path):
    """import 대상 파일 자체에 문법 오류가 있으면 ModuleImportError로 감싸서
    알려야 한다 (그대로 AssemblerError를 흘려보내면, Executor가 "이 오류가
    최상위 프로그램 자체의 문법 오류인지 import한 파일의 문법 오류인지"
    타입만으로 구분할 수 없기 때문이다). 실제 AssemblerError는 .errors에
    단일 원소로 그대로 담겨 있어야 한다.
    """
    path = _write(tmp_path / "broken.txt", "var x = ;\n")

    with pytest.raises(ModuleImportError) as excinfo:
        Importer().import_module(path)

    assert len(excinfo.value.errors) == 1
    assert isinstance(excinfo.value.errors[0], AssemblerError)
    assert excinfo.value.path == path


def test_import_module_raises_module_import_error_for_checker_violations(tmp_path):
    """import 대상 파일이 문법은 맞아도 Checker의 정적 검사(여기서는 최상위
    return)를 통과하지 못하면 (Assembler 실패와 같은 타입인) ModuleImportError로
    알려야 한다.

    이게 바로 Assembler만으로는 부족한 이유다 — 파싱만으로는 이 파일이
    잘못됐다는 걸 알 수 없다.
    """
    path = _write(tmp_path / "bad.txt", "return 5;\n")

    with pytest.raises(ModuleImportError) as excinfo:
        Importer().import_module(path)

    assert excinfo.value.errors
    assert all(isinstance(e, CheckerError) for e in excinfo.value.errors)
    assert "Can't return from top-level code." in str(excinfo.value.errors[0])


# --- 캐싱 (Singleton/Registry) ---

def test_import_module_caches_result_and_does_not_reread_file_on_second_call(tmp_path):
    """같은 경로를 두 번 import_module()해도 두 번째는 캐시를 그대로 반환해야 한다.

    두 번째 호출 전에 파일 내용을 바꿔도 반환값이 바뀌지 않는다는 것으로
    "다시 읽지 않았다"를 검증한다.
    """
    path = _write(tmp_path / "sum.txt", "var count = 1;\n")
    importer = Importer()

    first = importer.import_module(path)
    _write(tmp_path / "sum.txt", "var count = 999;\n")
    second = importer.import_module(path)

    assert second is first
    assert isinstance(second[0], VarDeclStmt)
    assert second[0].initializer.value == 1.0


# --- 재귀 조립 ---

def test_import_module_recursively_assembles_and_checks_nested_imports(tmp_path):
    """a.txt가 b.txt를 import하면, a.txt를 import_module()할 때 b.txt까지
    함께 assemble+check되어야 한다.
    """
    _write(tmp_path / "b.txt", "var y = 2;\n")
    a_path = _write(tmp_path / "a.txt", 'import "b.txt" alias b;\nvar x = 1;\n')

    importer = Importer()
    statements = importer.import_module(a_path)

    assert len(statements) == 2
    assert isinstance(statements[1], VarDeclStmt)
    # b.txt도 재귀적으로 조립되어 캐시에 남아있어야 다시 읽지 않고 재사용된다.
    b_statements = importer.import_module(str(tmp_path / "b.txt"))
    assert isinstance(b_statements[0], VarDeclStmt)
    assert b_statements[0].name.lexeme == "y"


def test_import_module_nested_check_error_propagates_from_the_top_level_import(tmp_path):
    """a.txt가 import하는 b.txt에 정적 오류가 있으면, a.txt를 import할 때도
    ModuleImportError가 나야 한다.
    """
    _write(tmp_path / "b.txt", "return 5;\n")
    a_path = _write(tmp_path / "a.txt", 'import "b.txt" alias b;\n')

    with pytest.raises(ModuleImportError) as excinfo:
        Importer().import_module(a_path)

    assert excinfo.value.path.endswith("b.txt")


def test_import_module_diamond_shaped_imports_do_not_raise_circular_import_error(tmp_path):
    """a.txt가 b.txt와 c.txt를, 그 둘이 각각 d.txt를 import하는 다이아몬드
    구조는 순환이 아니므로 오류 없이 조립되어야 한다.
    """
    _write(tmp_path / "d.txt", "var shared = 0;\n")
    _write(tmp_path / "b.txt", 'import "d.txt" alias d;\n')
    _write(tmp_path / "c.txt", 'import "d.txt" alias d;\n')
    a_path = _write(tmp_path / "a.txt", 'import "b.txt" alias b;\nimport "c.txt" alias c;\n')

    statements = Importer().import_module(a_path)

    assert len(statements) == 2


# --- 파일 없음 ---

def test_import_module_missing_file_raises_imported_file_not_found_error(tmp_path):
    """import 대상 파일 자체가 없으면 ImportedFileNotFoundError가 나야 한다."""
    missing_path = str(tmp_path / "does_not_exist.txt")

    with pytest.raises(ImportedFileNotFoundError) as excinfo:
        Importer().import_module(missing_path)

    assert "does_not_exist.txt" in str(excinfo.value)


def test_import_module_missing_nested_import_raises_imported_file_not_found_error(tmp_path):
    """a.txt가 존재하지 않는 파일을 import하면, a.txt를 import_module()할 때
    ImportedFileNotFoundError가 나야 하고 오류 위치는 그 import문의 키워드여야 한다.
    """
    a_path = _write(tmp_path / "a.txt", 'import "missing.txt" alias m;\n')

    with pytest.raises(ImportedFileNotFoundError) as excinfo:
        Importer().import_module(a_path)

    assert "missing.txt" in str(excinfo.value)
    assert excinfo.value.token is not None
    assert excinfo.value.token.type == TokenType.IMPORT


# --- 순환 import ---

def test_import_module_self_import_raises_circular_import_error(tmp_path):
    """a.txt가 자기 자신을 import하면 CircularImportError가 나야 한다."""
    a_path = _write(tmp_path / "a.txt", 'import "a.txt" alias a;\n')

    with pytest.raises(CircularImportError) as excinfo:
        Importer().import_module(a_path)

    assert "a.txt" in str(excinfo.value)


def test_import_module_indirect_circular_import_raises_circular_import_error(tmp_path):
    """a.txt가 b.txt를, b.txt가 다시 a.txt를 import하면 CircularImportError가 나야 한다."""
    _write(tmp_path / "b.txt", 'import "a.txt" alias a;\n')
    a_path = _write(tmp_path / "a.txt", 'import "b.txt" alias b;\n')

    with pytest.raises(CircularImportError) as excinfo:
        Importer().import_module(a_path)

    message = str(excinfo.value)
    assert "a.txt" in message
    assert "b.txt" in message


def test_import_module_three_file_circular_import_raises_circular_import_error(tmp_path):
    """a.txt가 b.txt를, b.txt가 c.txt를, c.txt가 다시 a.txt를 import하는
    3단계 순환도 감지해야 한다 (2파일 순환의 특수 케이스가 아니라
    일반적인 길이의 순환도 스택으로 정확히 잡는지 확인).
    """
    _write(tmp_path / "c.txt", 'import "a.txt" alias a;\n')
    _write(tmp_path / "b.txt", 'import "c.txt" alias c;\n')
    a_path = _write(tmp_path / "a.txt", 'import "b.txt" alias b;\n')

    with pytest.raises(CircularImportError) as excinfo:
        Importer().import_module(a_path)

    message = str(excinfo.value)
    assert "a.txt" in message
    assert "b.txt" in message
    assert "c.txt" in message
    # 순환이 처음 닫히는 지점(a -> b -> c -> a)까지의 경로 순서가 그대로 드러나야 한다.
    assert message.index("a.txt") < message.index("b.txt") < message.index("c.txt")


def test_import_module_three_file_circular_import_detected_from_middle_of_cycle(tmp_path):
    """순환의 시작점이 어디든(꼭 "맨 처음" 파일이 아니어도) 감지되어야 한다.

    a -> b -> c -> a인 순환에서, a가 아니라 b.txt를 진입점으로 삼아도
    b -> c -> a -> b로 순환이 잡혀야 한다.
    """
    _write(tmp_path / "a.txt", 'import "b.txt" alias b;\n')
    _write(tmp_path / "c.txt", 'import "a.txt" alias a;\n')
    b_path = _write(tmp_path / "b.txt", 'import "c.txt" alias c;\n')

    with pytest.raises(CircularImportError) as excinfo:
        Importer().import_module(b_path)

    message = str(excinfo.value)
    assert "a.txt" in message
    assert "b.txt" in message
    assert "c.txt" in message


def test_import_module_circular_import_hidden_inside_if_block_is_still_detected(tmp_path):
    """import가 if 블록 안에 있어도(반복문만 금지, if는 허용) 순환 감지가
    돼야 한다. 사전 순회가 최상위 문장만 훑으면 이 순환을 놓쳐, 실제
    실행 시점에 무한 재귀(RecursionError)로 죽는다.
    """
    _write(tmp_path / "b.txt", 'import "a.txt" alias a;\n')
    a_path = _write(tmp_path / "a.txt", 'if (true) {\n  import "b.txt" alias b;\n}\n')

    with pytest.raises(CircularImportError) as excinfo:
        Importer().import_module(a_path)

    message = str(excinfo.value)
    assert "a.txt" in message
    assert "b.txt" in message


# --- 경로 정규화 ---

def test_import_module_detects_cycle_across_differently_spelled_relative_paths(tmp_path):
    """서로 다른 상대 경로 표기가 같은 파일을 가리키면 정규화해서 같은
    항목으로 취급해야 한다. a.txt <-> sub/b.txt가 서로를 import하는데,
    b.txt 쪽에서는 "../a.txt"로 되돌아오는 표기를 쓴다.
    """
    sub_dir = tmp_path / "sub"
    sub_dir.mkdir()
    _write(sub_dir / "b.txt", 'import "../a.txt" alias a;\n')
    a_path = _write(tmp_path / "a.txt", 'import "sub/b.txt" alias b;\n')

    with pytest.raises(CircularImportError) as excinfo:
        Importer().import_module(a_path)

    message = str(excinfo.value)
    assert "a.txt" in message
    assert "b.txt" in message


# --- 인스턴스 격리 ---

def test_import_module_cache_is_not_shared_between_importer_instances(tmp_path):
    """서로 다른 Importer 인스턴스는 캐시/순환 감지 상태를 공유하면 안 된다."""
    path = _write(tmp_path / "sum.txt", "var x = 1;\n")

    first_importer = Importer()
    first_importer.import_module(path)

    # 새 인스턴스는 캐시가 비어있어야 하므로, 파일을 바꾸면 그 내용을 읽어야 한다.
    _write(tmp_path / "sum.txt", "var x = 2;\n")
    second_statements = Importer().import_module(path)

    assert second_statements[0].initializer.value == 2.0


# --- 중첩 import의 다른 오류 종류 ---

def test_import_module_nested_syntax_error_raises_module_import_error(tmp_path):
    """a.txt가 import하는 b.txt에 문법 오류가 있으면, a.txt를 import할 때도
    ModuleImportError로 알려야 하고, path는 실제로 문법 오류가 난 b.txt를
    가리켜야 한다.
    """
    _write(tmp_path / "b.txt", "var x = ;\n")
    a_path = _write(tmp_path / "a.txt", 'import "b.txt" alias b;\n')

    with pytest.raises(ModuleImportError) as excinfo:
        Importer().import_module(a_path)

    assert len(excinfo.value.errors) == 1
    assert isinstance(excinfo.value.errors[0], AssemblerError)
    assert excinfo.value.path.endswith("b.txt")
