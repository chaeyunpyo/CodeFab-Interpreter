"""ImportStmt 실행 테스트. (요구사항_정리/import.md)

실제 파일 I/O가 필요한 테스트는 tmp_path 픽스처로 임시 파일을 만들어 진행한다.
순환 import / 파일 없음 등 오류 경로는 Importer가 담당하므로 여기서는
오류가 Executor까지 전파되는지(bubbles-up)만 확인한다.
"""

import pytest

from assembler import Assembler
from executor import Storage, execute
from executor._namespace import LoxNamespace
from executor.errors import UndefinedPropertyError
from importer import CircularImportError, ImportedFileNotFoundError


# ── 헬퍼 ─────────────────────────────────────────────────────────────────────

def _assemble(source: str):
    a = Assembler(source)
    a.execute()
    return a.ast


def _run(source: str, storage: Storage = None) -> Storage:
    if storage is None:
        storage = Storage()
    for stmt in _assemble(source):
        execute(stmt, storage)
    return storage


# ── LoxNamespace 단위 테스트 ──────────────────────────────────────────────────

class TestLoxNamespace:
    def test_get_존재하는_필드_반환(self):
        from nodes.tokens import Token
        from nodes.token_type import TokenType
        ns = LoxNamespace("lib")
        ns.fields["x"] = 42
        token = Token(TokenType.IDENTIFIER, "x")
        assert ns.get(token) == 42

    def test_get_없는_필드_UndefinedPropertyError(self):
        from nodes.tokens import Token
        from nodes.token_type import TokenType
        ns = LoxNamespace("lib")
        token = Token(TokenType.IDENTIFIER, "missing")
        with pytest.raises(UndefinedPropertyError):
            ns.get(token)

    def test_repr_포함_alias_이름(self):
        ns = LoxNamespace("mylib")
        assert "mylib" in repr(ns)


# ── 기본 import 실행 ──────────────────────────────────────────────────────────

class TestBasicImport:
    def test_import_후_alias가_LoxNamespace로_바인딩(self, tmp_path):
        mod = tmp_path / "mod.txt"
        mod.write_text("var x = 10;", encoding="utf-8")
        storage = _run(f'import "{mod}" alias lib;')
        ns = storage.get("lib")
        assert isinstance(ns, LoxNamespace)

    def test_모듈_변수_alias로_접근(self, tmp_path):
        mod = tmp_path / "mod.txt"
        mod.write_text("var x = 42;", encoding="utf-8")
        storage = _run(f'import "{mod}" alias lib; var r = lib.x;')
        assert storage.get("r") == 42

    def test_모듈_함수_alias로_호출(self, tmp_path):
        mod = tmp_path / "sum.txt"
        mod.write_text("Func add(a, b) { return a + b; }", encoding="utf-8")
        storage = _run(f'import "{mod}" alias sum; var r = sum.add(3, 4);')
        assert storage.get("r") == 7

    def test_모듈_클래스_alias로_인스턴스_생성(self, tmp_path):
        mod = tmp_path / "mod.txt"
        mod.write_text("Class Point { init(x, y) { This.x = x; This.y = y; } }",
                       encoding="utf-8")
        from executor import LoxInstance
        storage = _run(f'import "{mod}" alias geo; var p = geo.Point(1, 2);')
        p = storage.get("p")
        assert isinstance(p, LoxInstance)
        assert p.fields["x"] == 1
        assert p.fields["y"] == 2

    def test_내장_Array는_namespace에_포함되지_않음(self, tmp_path):
        mod = tmp_path / "mod.txt"
        mod.write_text("var v = 1;", encoding="utf-8")
        storage = _run(f'import "{mod}" alias lib;')
        ns = storage.get("lib")
        assert "Array" not in ns.fields

    def test_alias_변수_현재_스코프에만_정의됨(self, tmp_path):
        mod = tmp_path / "mod.txt"
        mod.write_text("var x = 1;", encoding="utf-8")
        from executor.errors import UndefinedVariableError
        # 블록 안에서 import하면 블록 밖에서 alias 접근 불가
        with pytest.raises(UndefinedVariableError):
            _run(f'{{ import "{mod}" alias lib; }} var r = lib.x;')


# ── 캐시 동작 ─────────────────────────────────────────────────────────────────

class TestImportCache:
    def test_같은_파일_두번_import해도_동일_AST_선언_공유(self, tmp_path):
        mod = tmp_path / "mod.txt"
        mod.write_text("Func f() { return 99; }", encoding="utf-8")
        storage = _run(f'import "{mod}" alias a; import "{mod}" alias b;')
        ns_a = storage.get("a")
        ns_b = storage.get("b")
        # Importer가 AST를 캐싱하므로 declaration(FunctionStmt)은 동일 객체를 가리킨다.
        assert ns_a.fields["f"].declaration is ns_b.fields["f"].declaration


# ── 중첩 import ───────────────────────────────────────────────────────────────

class TestNestedImport:
    def test_모듈이_다른_모듈을_import하면_중첩_실행(self, tmp_path):
        util = tmp_path / "util.txt"
        util.write_text("Func double(n) { return n * 2; }", encoding="utf-8")
        lib = tmp_path / "lib.txt"
        lib.write_text(f'import "{util}" alias u; Func quad(n) {{ return u.double(u.double(n)); }}',
                       encoding="utf-8")
        storage = _run(f'import "{lib}" alias lib; var r = lib.quad(3);')
        assert storage.get("r") == 12


# ── 오류 전파 ─────────────────────────────────────────────────────────────────

class TestImportErrors:
    def test_파일_없으면_ImportedFileNotFoundError(self):
        with pytest.raises(ImportedFileNotFoundError):
            _run('import "없는파일.txt" alias x;')

    def test_순환_import_CircularImportError(self, tmp_path):
        a = tmp_path / "a.txt"
        b = tmp_path / "b.txt"
        a.write_text(f'import "{b}" alias b_alias;', encoding="utf-8")
        b.write_text(f'import "{a}" alias a_alias;', encoding="utf-8")
        with pytest.raises(CircularImportError):
            _run(f'import "{a}" alias a_alias;')

    def test_namespace_없는_필드_접근_UndefinedPropertyError(self, tmp_path):
        mod = tmp_path / "mod.txt"
        mod.write_text("var x = 1;", encoding="utf-8")
        with pytest.raises(UndefinedPropertyError):
            _run(f'import "{mod}" alias lib; var r = lib.nonexistent;')
