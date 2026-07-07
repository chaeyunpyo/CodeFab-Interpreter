"""Storage TDD 테스트.

RED → GREEN 순서로 작성됨.
모든 테스트는 src/storage.py 구현 전 먼저 실패해야 한다.
"""
import pytest
from storage import Storage, UndefinedVariableError


# ── 기본 CRUD ─────────────────────────────────────────────────────────────────

class TestStorageBasicSet:
    def test_변수를_저장할_수_있다(self):
        storage = Storage()
        storage.define("x", 42)
        assert storage.get("x") == 42

    def test_문자열_변수를_저장할_수_있다(self):
        storage = Storage()
        storage.define("name", "hello")
        assert storage.get("name") == "hello"

    def test_None_값을_저장할_수_있다(self):
        storage = Storage()
        storage.define("x", None)
        assert storage.get("x") is None


class TestStorageGet:
    def test_저장된_변수를_조회할_수_있다(self):
        storage = Storage()
        storage.define("y", 99)
        assert storage.get("y") == 99

    def test_정의되지_않은_변수_조회시_예외를_발생시킨다(self):
        storage = Storage()
        with pytest.raises(UndefinedVariableError):
            storage.get("undefined_var")

    def test_예외_메시지에_변수명이_포함된다(self):
        storage = Storage()
        with pytest.raises(UndefinedVariableError) as exc_info:
            storage.get("missing")
        assert "missing" in str(exc_info.value)


class TestStorageUpdate:
    def test_기존_변수를_set으로_업데이트할_수_있다(self):
        storage = Storage()
        storage.define("x", 1)
        storage.set("x", 2)
        assert storage.get("x") == 2

    def test_define을_두_번_호출하면_현재_스코프에서_덮어쓴다(self):
        storage = Storage()
        storage.define("x", 1)
        storage.define("x", 99)
        assert storage.get("x") == 99

    def test_미정의_변수에_set_호출시_예외를_발생시킨다(self):
        storage = Storage()
        with pytest.raises(UndefinedVariableError):
            storage.set("not_defined", 10)


class TestStorageExists:
    def test_정의된_변수는_exists가_True를_반환한다(self):
        storage = Storage()
        storage.define("x", 1)
        assert storage.exists("x") is True

    def test_정의되지_않은_변수는_exists가_False를_반환한다(self):
        storage = Storage()
        assert storage.exists("y") is False


# ── 스코프 관리 ───────────────────────────────────────────────────────────────

class TestStorageScope:
    def test_내부_스코프에서_외부_변수를_읽을_수_있다(self):
        storage = Storage()
        storage.define("x", 10)
        storage.push_scope()
        assert storage.get("x") == 10

    def test_pop_이후_내부_스코프_변수는_접근_불가하다(self):
        storage = Storage()
        storage.push_scope()
        storage.define("inner", 5)
        storage.pop_scope()
        with pytest.raises(UndefinedVariableError):
            storage.get("inner")

    def test_set은_스코프_체인을_따라_외부_변수를_업데이트한다(self):
        storage = Storage()
        storage.define("x", 1)
        storage.push_scope()
        storage.set("x", 99)
        storage.pop_scope()
        assert storage.get("x") == 99

    def test_내부_스코프에서_define하면_외부_변수를_가린다(self):
        storage = Storage()
        storage.define("x", 1)
        storage.push_scope()
        storage.define("x", 2)
        assert storage.get("x") == 2
        storage.pop_scope()
        assert storage.get("x") == 1

    def test_전역_스코프를_pop하면_RuntimeError를_발생시킨다(self):
        storage = Storage()
        with pytest.raises(RuntimeError):
            storage.pop_scope()

    def test_중첩_스코프에서_모든_계층_변수를_읽을_수_있다(self):
        storage = Storage()
        storage.define("a", 1)
        storage.push_scope()
        storage.define("b", 2)
        storage.push_scope()
        storage.define("c", 3)
        assert storage.get("a") == 1
        assert storage.get("b") == 2
        assert storage.get("c") == 3
        storage.pop_scope()
        assert storage.exists("c") is False
        assert storage.exists("b") is True


class TestStorageForLoopIntegration:
    def test_for_loop_변수가_저장소에_반영된다(self):
        """for 루프 변수 흉내: define → set 반복으로 storage에 반영됨을 확인."""
        storage = Storage()
        storage.define("i", 0)
        for val in range(3):
            storage.set("i", val)
        assert storage.get("i") == 2

    def test_중첩_스코프에서_loop_variable이_외부_스코프_변수를_업데이트한다(self):
        storage = Storage()
        storage.define("total", 0)
        storage.define("i", 0)
        for val in [10, 20, 30]:
            storage.push_scope()
            storage.set("i", val)
            storage.set("total", storage.get("total") + storage.get("i"))
            storage.pop_scope()
        assert storage.get("total") == 60
        assert storage.get("i") == 30
