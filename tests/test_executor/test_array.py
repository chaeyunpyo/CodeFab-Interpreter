"""정적 배열 실행 테스트 (요구사항_정리/정적배열.md)"""

import pytest

from executor import (
    ArityMismatchError,
    FabArray,
    IndexOutOfRangeError,
    InvalidArraySizeError,
    InvalidIndexTypeError,
    NotAnArrayError,
    Storage,
    evaluate,
    stringify,
)
from nodes.expr import (
    CallExpr,
    IndexGetExpr,
    IndexSetExpr,
    LiteralExpr,
    VariableExpr,
)
from nodes.token_type import TokenType

from helpers import tok


# ── 헬퍼 ──────────────────────────────────────────────────────────────────────

def array_call(size_val):
    """Array(size_val) CallExpr를 만드는 헬퍼."""
    return CallExpr(
        callee=VariableExpr(tok(TokenType.IDENTIFIER, "Array")),
        paren=tok(TokenType.LEFT_PAREN, "("),
        arguments=[LiteralExpr(size_val)],
    )


def index_get(arr_name: str, idx_val):
    """arr_name[idx_val] IndexGetExpr를 만드는 헬퍼."""
    return IndexGetExpr(
        object=VariableExpr(tok(TokenType.IDENTIFIER, arr_name)),
        bracket=tok(TokenType.LEFT_BRACKET, "["),
        index=LiteralExpr(idx_val),
    )


def index_set(arr_name: str, idx_val, value_val):
    """arr_name[idx_val] = value_val IndexSetExpr를 만드는 헬퍼."""
    return IndexSetExpr(
        object=VariableExpr(tok(TokenType.IDENTIFIER, arr_name)),
        bracket=tok(TokenType.LEFT_BRACKET, "["),
        index=LiteralExpr(idx_val),
        value=LiteralExpr(value_val),
    )


# ── Array 생성 ────────────────────────────────────────────────────────────────

class TestArrayCreation:
    def test_정수_크기로_배열을_생성한다(self, storage):
        result = evaluate(array_call(3.0), storage)
        assert isinstance(result, FabArray)
        assert len(result) == 3

    def test_생성된_배열의_각_칸은_null이다(self, storage):
        result = evaluate(array_call(3.0), storage)
        for i in range(3):
            assert result.get(i) is None

    def test_크기_0인_배열을_생성할_수_있다(self, storage):
        result = evaluate(array_call(0.0), storage)
        assert isinstance(result, FabArray)
        assert len(result) == 0

    def test_크기가_문자열이면_InvalidArraySizeError를_발생시킨다(self, storage):
        with pytest.raises(InvalidArraySizeError):
            evaluate(array_call("hi"), storage)

    def test_크기가_불리언이면_InvalidArraySizeError를_발생시킨다(self, storage):
        with pytest.raises(InvalidArraySizeError):
            evaluate(array_call(True), storage)

    def test_크기가_음수이면_InvalidArraySizeError를_발생시킨다(self, storage):
        with pytest.raises(InvalidArraySizeError):
            evaluate(array_call(-1.0), storage)

    def test_크기가_소수이면_InvalidArraySizeError를_발생시킨다(self, storage):
        with pytest.raises(InvalidArraySizeError):
            evaluate(array_call(2.5), storage)

    def test_잘못된_크기_오류에_호출_위치_토큰이_붙는다(self, storage):
        # Array("hi") 같은 호출에서 InvalidArraySizeError.token이 None이면
        # 오류 메시지가 "Line ?"로 나온다 — expr.paren이 반드시 붙어야 한다.
        paren = tok(TokenType.LEFT_PAREN, "(")
        expr = CallExpr(
            callee=VariableExpr(tok(TokenType.IDENTIFIER, "Array")),
            paren=paren,
            arguments=[LiteralExpr("hi")],
        )
        with pytest.raises(InvalidArraySizeError) as exc_info:
            evaluate(expr, storage)
        assert exc_info.value.token is paren

    def test_음수_크기_오류에_호출_위치_토큰이_붙는다(self, storage):
        paren = tok(TokenType.LEFT_PAREN, "(")
        expr = CallExpr(
            callee=VariableExpr(tok(TokenType.IDENTIFIER, "Array")),
            paren=paren,
            arguments=[LiteralExpr(-1.0)],
        )
        with pytest.raises(InvalidArraySizeError) as exc_info:
            evaluate(expr, storage)
        assert exc_info.value.token is paren

    def test_인자_없이_호출하면_ArityMismatchError를_발생시킨다(self, storage):
        expr = CallExpr(
            callee=VariableExpr(tok(TokenType.IDENTIFIER, "Array")),
            paren=tok(TokenType.LEFT_PAREN, "("),
            arguments=[],
        )
        with pytest.raises(ArityMismatchError):
            evaluate(expr, storage)


# ── 인덱스 읽기 ───────────────────────────────────────────────────────────────

class TestIndexGet:
    def setup_method(self):
        """각 테스트 메서드 전에 공통 배열을 준비한다."""

    def test_배열_인덱스_읽기가_올바르다(self, storage):
        storage.define("arr", evaluate(array_call(3.0), storage))
        # 직접 값 세팅 후 읽기
        arr = storage.get("arr")
        arr.set(0, 10.0)
        arr.set(1, 20.0)
        arr.set(2, 30.0)
        assert evaluate(index_get("arr", 0.0), storage) == 10.0
        assert evaluate(index_get("arr", 1.0), storage) == 20.0
        assert evaluate(index_get("arr", 2.0), storage) == 30.0

    def test_초기화_직후_null을_반환한다(self, storage):
        storage.define("arr", evaluate(array_call(2.0), storage))
        assert evaluate(index_get("arr", 0.0), storage) is None

    def test_인덱스_범위_초과시_IndexOutOfRangeError를_발생시킨다(self, storage):
        storage.define("arr", evaluate(array_call(3.0), storage))
        with pytest.raises(IndexOutOfRangeError):
            evaluate(index_get("arr", 5.0), storage)

    def test_음수_인덱스는_IndexOutOfRangeError를_발생시킨다(self, storage):
        storage.define("arr", evaluate(array_call(3.0), storage))
        with pytest.raises(IndexOutOfRangeError):
            evaluate(index_get("arr", -1.0), storage)

    def test_인덱스가_문자열이면_InvalidIndexTypeError를_발생시킨다(self, storage):
        storage.define("arr", evaluate(array_call(3.0), storage))
        with pytest.raises(InvalidIndexTypeError):
            evaluate(index_get("arr", "hello"), storage)

    def test_인덱스가_불리언이면_InvalidIndexTypeError를_발생시킨다(self, storage):
        storage.define("arr", evaluate(array_call(3.0), storage))
        with pytest.raises(InvalidIndexTypeError):
            evaluate(index_get("arr", True), storage)

    def test_대상이_배열이_아니면_NotAnArrayError를_발생시킨다(self, storage):
        storage.define("x", 10.0)
        with pytest.raises(NotAnArrayError):
            evaluate(index_get("x", 0.0), storage)

    def test_대상이_인스턴스면_오류_메시지가_전체_repr을_덤프하지_않는다(self, storage):
        """LoxInstance/LoxClass는 커스텀 __repr__이 있어야 한다 - 기본
        dataclass repr은 methods/필드까지 전부 펼쳐서 오류 메시지가
        읽을 수 없을 정도로 길어진다.
        """
        from executor._class import LoxClass, LoxInstance

        instance = LoxInstance(LoxClass("Robot"))
        storage.define("r", instance)
        with pytest.raises(NotAnArrayError) as excinfo:
            evaluate(index_get("r", 0.0), storage)
        assert "Robot instance" in str(excinfo.value)
        assert "fields=" not in str(excinfo.value)


# ── 인덱스 쓰기 ───────────────────────────────────────────────────────────────

class TestIndexSet:
    def test_배열_인덱스_쓰기가_올바르다(self, storage):
        storage.define("arr", evaluate(array_call(3.0), storage))
        evaluate(index_set("arr", 0.0, 42.0), storage)
        assert storage.get("arr").get(0) == 42.0

    def test_쓰기_후_읽기로_값이_유지된다(self, storage):
        storage.define("arr", evaluate(array_call(3.0), storage))
        evaluate(index_set("arr", 1.0, 99.0), storage)
        assert evaluate(index_get("arr", 1.0), storage) == 99.0

    def test_쓰기는_대입한_값을_반환한다(self, storage):
        storage.define("arr", evaluate(array_call(3.0), storage))
        result = evaluate(index_set("arr", 0.0, 7.0), storage)
        assert result == 7.0

    def test_인덱스_범위_초과시_IndexOutOfRangeError를_발생시킨다(self, storage):
        storage.define("arr", evaluate(array_call(3.0), storage))
        with pytest.raises(IndexOutOfRangeError):
            evaluate(index_set("arr", 10.0, 1.0), storage)

    def test_인덱스가_문자열이면_InvalidIndexTypeError를_발생시킨다(self, storage):
        storage.define("arr", evaluate(array_call(3.0), storage))
        with pytest.raises(InvalidIndexTypeError):
            evaluate(index_set("arr", "idx", 1.0), storage)

    def test_대상이_배열이_아니면_NotAnArrayError를_발생시킨다(self, storage):
        storage.define("x", "hello")
        with pytest.raises(NotAnArrayError):
            evaluate(index_set("x", 0.0, 1.0), storage)


# ── stringify ─────────────────────────────────────────────────────────────────

class TestStringifyArray:
    def test_null로_초기화된_배열을_문자열로_변환한다(self):
        arr = FabArray(3)
        assert stringify(arr) == "[null, null, null]"

    def test_값이_채워진_배열을_문자열로_변환한다(self):
        arr = FabArray(3)
        arr.set(0, 10.0)
        arr.set(1, 20.0)
        arr.set(2, 30.0)
        assert stringify(arr) == "[10, 20, 30]"

    def test_빈_배열을_문자열로_변환한다(self):
        arr = FabArray(0)
        assert stringify(arr) == "[]"
