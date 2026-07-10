"""ImportStmt 실행 테스트. (요구사항_정리/import.md)

실제 파일 I/O가 필요한 테스트는 tmp_path 픽스처로 임시 파일을 만들어 진행한다.
순환 import / 파일 없음 등 오류 경로는 Importer가 담당하므로 여기서는
오류가 Executor까지 전파되는지(bubbles-up)만 확인한다.
"""

import pytest

from assembler import Assembler
from executor import Storage, execute
from executor._namespace import LiveModuleScope, LoxNamespace
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


# ── LiveModuleScope 단위 테스트 ────────────────────────────────────────────────

class TestLiveModuleScope:
    def test_원본_dict_변경이_그대로_보인다(self):
        """namespace.fields가 스냅샷 복사가 아니라 원본 dict를 그대로 공유해야 한다."""
        scope = {"counter": 0}
        view = LiveModuleScope(scope, excluded_names=())

        scope["counter"] = 5

        assert view["counter"] == 5

    def test_제외된_이름은_보이지_않는다(self):
        scope = {"Array": "builtin", "x": 1}
        view = LiveModuleScope(scope, excluded_names={"Array"})

        assert "Array" not in view
        assert list(view) == ["x"]

    def test_쓰기는_원본_dict로_그대로_전달된다(self):
        scope = {}
        view = LiveModuleScope(scope, excluded_names=())

        view["y"] = 10

        assert scope["y"] == 10

    def test_삭제는_원본_dict에서_그대로_지워진다(self):
        scope = {"y": 10}
        view = LiveModuleScope(scope, excluded_names=())

        del view["y"]

        assert "y" not in scope


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


# ── 정적 바인딩 (요구사항_정리/실행전_최적화.md) ─────────────────────────────────

class TestImportedModuleUsesStaticBinding:
    def test_모듈_내부_지역_변수_조회는_이름_기반_체인_탐색을_거치지_않는다(self, tmp_path, mocker):
        """import된 모듈 실행용 Storage에도 checker.locals가 전달되어야
        모듈 안의 지역 변수(파라미터/블록 변수) 조회가 Storage.get()의 이름
        기반 스코프 체인 탐색이 아니라 get_resolved()의 O(1) 경로를 탄다.

        locals를 안 넘기면(과거 버그) checker.locals가 계산되고도 버려져서
        모듈 안의 모든 지역 변수 조회가 매번 Storage.get()으로 폴백한다.
        """
        mod = tmp_path / "mod.txt"
        mod.write_text(
            "Func add(a, b) { { var result = a + b; return result; } }",
            encoding="utf-8",
        )

        spy = mocker.patch.object(Storage, "get", wraps=Storage.get, autospec=True)
        storage = _run(f'import "{mod}" alias sum; var r = sum.add(3, 4);')

        module_local_lookups = [call for call in spy.call_args_list if call.args[1] in ("a", "b", "result")]
        assert module_local_lookups == []
        assert storage.get("r") == 7


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

    def test_같은_파일_두번_import하면_동일_namespace_객체를_공유한다(self, tmp_path):
        """AST뿐 아니라 실행 결과(namespace)도 경로별로 캐싱해서 한 번만
        실행해야 한다 - 안 그러면 각 import 지점마다 독립된 전역 상태를
        갖게 되어, 한쪽에서 바꾼 값을 다른 쪽에서 못 보는 문제가 생긴다.
        """
        mod = tmp_path / "mod.txt"
        mod.write_text("var counter = 0;\nFunc inc() { counter = counter + 1; }", encoding="utf-8")
        storage = _run(f'import "{mod}" alias a; import "{mod}" alias b;')
        ns_a = storage.get("a")
        ns_b = storage.get("b")

        assert ns_a is ns_b

        from executor import evaluate
        from nodes.expr import CallExpr, FieldGetExpr, VariableExpr
        from nodes.tokens import Token
        from nodes.token_type import TokenType

        inc_call = CallExpr(
            callee=FieldGetExpr(object=VariableExpr(Token(TokenType.IDENTIFIER, "a")), name=Token(TokenType.IDENTIFIER, "inc")),
            paren=Token(TokenType.LEFT_PAREN, "("),
            arguments=[],
        )
        evaluate(inc_call, storage)
        assert ns_b.fields["counter"] == 1.0


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

    def test_if_블록_안에_숨은_순환_import도_CircularImportError(self, tmp_path):
        """import는 반복문만 금지고 if는 허용되는데, 사전 순회가 최상위
        문장만 훑으면 if 블록 속 import는 못 찾아 순환 감지를 놓치고
        실행 시점에 RecursionError로 죽는다 (a -> b -> a 반복).
        """
        a = tmp_path / "a.txt"
        b = tmp_path / "b.txt"
        a.write_text(f'if (true) {{ import "{b}" alias b_alias; }}', encoding="utf-8")
        b.write_text(f'import "{a}" alias a_alias;', encoding="utf-8")
        with pytest.raises(CircularImportError):
            _run(f'import "{a}" alias a_alias;')

    def test_함수_호출로_실행_중에만_드러나는_순환_import도_CircularImportError(self, tmp_path):
        """Func 본문 속 import는 호출 시점에야 실행되므로 정적 사전 순회가
        의도적으로 건너뛴다. 그 함수가 모듈 최상위에서 곧바로 호출되어
        원래 import가 아직 실행 중인 채로 순환이 닫히면, 실행 단계
        안전망(Importer.executing)이 대신 잡아야 한다.

        import 대상 파일 최상위에는 선언만 허용되므로(요구사항_정리/
        import.md), 곧바로 호출하는 부수효과는 bare 문장이 아니라 변수
        선언의 초기화식 자리에 담아서 표현한다.
        """
        a = tmp_path / "a.txt"
        b = tmp_path / "b.txt"
        a.write_text(f'Func f() {{ import "{b}" alias b_alias; }} var _f_result = f();', encoding="utf-8")
        b.write_text(f'Func g() {{ import "{a}" alias a_alias; }} var _g_result = g();', encoding="utf-8")
        with pytest.raises(CircularImportError):
            _run(f'import "{a}" alias a_alias;')
