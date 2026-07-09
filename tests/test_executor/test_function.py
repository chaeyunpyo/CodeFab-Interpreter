import pytest

from executor import (
    ArityMismatchError,
    Function,
    LoxCallable,
    NotCallableError,
    StackOverflowError,
    UndefinedVariableError,
    evaluate,
    execute,
)
from nodes.expr import AssignExpr, BinaryExpr, CallExpr, LiteralExpr, VariableExpr
from nodes.stmt import ExpressionStmt, FunctionStmt, IfStmt, ReturnStmt
from nodes.token_type import TokenType

from helpers import tok


# ── 테스트용 AST 조립 헬퍼 ────────────────────────────────────────────────────

def declare_function(name: str, params: list, body: list) -> FunctionStmt:
    return FunctionStmt(
        tok(TokenType.IDENTIFIER, name),
        [tok(TokenType.IDENTIFIER, p) for p in params],
        body,
    )


def call(name: str, *arguments) -> CallExpr:
    return CallExpr(
        VariableExpr(tok(TokenType.IDENTIFIER, name)),
        tok(TokenType.LEFT_PAREN, "("),
        list(arguments),
    )


def var_expr(name: str) -> VariableExpr:
    return VariableExpr(tok(TokenType.IDENTIFIER, name))


def ret(value=None) -> ReturnStmt:
    return ReturnStmt(tok(TokenType.RETURN, "return"), value)


# ── 함수 선언 ─────────────────────────────────────────────────────────────────

class TestExecuteFunctionStmt:
    def test_함수를_선언하면_저장소에_Function_값으로_등록된다(self, storage):
        execute(declare_function("noop", [], []), storage)
        assert isinstance(storage.get("noop"), Function)

    def test_Function은_LoxCallable_인터페이스를_구현한다(self, storage):
        # CallExpr가 Function의 내부 구조 대신 이 인터페이스만 보고 호출할 수 있어야 한다.
        execute(declare_function("noop", [], []), storage)
        assert isinstance(storage.get("noop"), LoxCallable)


# ── 함수 호출 ─────────────────────────────────────────────────────────────────

class TestEvaluateCallExpr:
    def test_인자를_받아_파라미터에_바인딩하고_반환값을_돌려준다(self, storage):
        # Func add(a, b) { return a + b; }
        body = [ret(BinaryExpr(var_expr("a"), tok(TokenType.PLUS, "+"), var_expr("b")))]
        execute(declare_function("add", ["a", "b"], body), storage)
        result = evaluate(call("add", LiteralExpr(1.0), LiteralExpr(2.0)), storage)
        assert result == 3.0

    def test_return이_없으면_None을_반환한다(self, storage):
        execute(declare_function("noop", [], []), storage)
        assert evaluate(call("noop"), storage) is None

    def test_값_없는_return은_None을_반환한다(self, storage):
        execute(declare_function("early", [], [ret()]), storage)
        assert evaluate(call("early"), storage) is None

    def test_블록_중간에서_return하면_이후_문장이_실행되지_않는다(self, storage):
        storage.define("ran_after_return", 0.0)
        body = [
            ret(LiteralExpr(1.0)),
            ExpressionStmt(AssignExpr(tok(TokenType.IDENTIFIER, "ran_after_return"), LiteralExpr(1.0))),
        ]
        execute(declare_function("f", [], body), storage)
        evaluate(call("f"), storage)
        assert storage.get("ran_after_return") == 0.0

    def test_if_안에서_return해도_함수_호출까지_전파된다(self, storage):
        # Func abs(n) { if (n < 0) return 0 - n; return n; }
        body = [
            IfStmt(
                BinaryExpr(var_expr("n"), tok(TokenType.LESS, "<"), LiteralExpr(0.0)),
                ret(BinaryExpr(LiteralExpr(0.0), tok(TokenType.MINUS, "-"), var_expr("n"))),
            ),
            ret(var_expr("n")),
        ]
        execute(declare_function("abs", ["n"], body), storage)
        assert evaluate(call("abs", LiteralExpr(-5.0)), storage) == 5.0
        assert evaluate(call("abs", LiteralExpr(5.0)), storage) == 5.0

    def test_함수는_호출부의_지역_변수를_보지_못한다(self, storage):
        # 호출 프레임 격리 확인: 함수 밖 블록의 지역 변수는 함수 본문에서 안 보여야 한다.
        execute(declare_function("f", [], [ret(var_expr("outer"))]), storage)
        storage.push_scope()
        storage.define("outer", 42.0)
        with pytest.raises(UndefinedVariableError):
            evaluate(call("f"), storage)
        storage.pop_scope()

    def test_전역에_선언한_함수는_전역_변수를_볼_수_있다(self, storage):
        storage.define("g", 100.0)
        execute(declare_function("f", [], [ret(var_expr("g"))]), storage)
        assert evaluate(call("f"), storage) == 100.0

    def test_함수_안에서_전역_변수_대입은_호출이_끝난_뒤에도_유지된다(self, storage):
        # count = count + 1;  -- 전역은 진짜 "전역"이라 함수 호출이 끝나도
        # 대입한 값이 사라지지 않아야 한다 (클로저 없음과는 별개 - 클로저는
        # 지역 스코프 체인 얘기고, 전역 dict 자체는 항상 공유된다).
        storage.define("count", 0.0)
        increment = AssignExpr(
            name=tok(TokenType.IDENTIFIER, "count"),
            value=BinaryExpr(var_expr("count"), tok(TokenType.PLUS, "+"), LiteralExpr(1.0)),
        )
        execute(declare_function("inc", [], [ExpressionStmt(expression=increment)]), storage)

        evaluate(call("inc"), storage)
        evaluate(call("inc"), storage)

        assert storage.get("count") == 2.0

    def test_호출_종료_후_호출부_스코프가_그대로_복원된다(self, storage):
        execute(declare_function("f", [], []), storage)
        storage.push_scope()
        storage.define("local", 1.0)
        evaluate(call("f"), storage)
        assert storage.get("local") == 1.0
        storage.pop_scope()


class TestRecursion:
    def test_재귀_호출로_팩토리얼을_계산한다(self, storage):
        # Func fact(n) { if (n <= 1) return 1; return n * fact(n - 1); }
        body = [
            IfStmt(
                BinaryExpr(var_expr("n"), tok(TokenType.LESS_EQUAL, "<="), LiteralExpr(1.0)),
                ret(LiteralExpr(1.0)),
            ),
            ret(
                BinaryExpr(
                    var_expr("n"),
                    tok(TokenType.STAR, "*"),
                    call("fact", BinaryExpr(var_expr("n"), tok(TokenType.MINUS, "-"), LiteralExpr(1.0))),
                )
            ),
        ]
        execute(declare_function("fact", ["n"], body), storage)
        assert evaluate(call("fact", LiteralExpr(5.0)), storage) == 120.0

    def test_재귀가_너무_깊으면_StackOverflowError를_내고_파이썬_RecursionError로_죽지_않는다(self, storage):
        # Func count(n) { if (n <= 0) return 0; return 1 + count(n - 1); }
        body = [
            IfStmt(
                BinaryExpr(var_expr("n"), tok(TokenType.LESS_EQUAL, "<="), LiteralExpr(0.0)),
                ret(LiteralExpr(0.0)),
            ),
            ret(
                BinaryExpr(
                    LiteralExpr(1.0),
                    tok(TokenType.PLUS, "+"),
                    call("count", BinaryExpr(var_expr("n"), tok(TokenType.MINUS, "-"), LiteralExpr(1.0))),
                )
            ),
        ]
        execute(declare_function("count", ["n"], body), storage)
        with pytest.raises(StackOverflowError):
            evaluate(call("count", LiteralExpr(5000.0)), storage)


# ── 런타임 오류 ────────────────────────────────────────────────────────────────

class TestCallRuntimeErrors:
    def test_함수가_아닌_값을_호출하면_오류(self, storage):
        storage.define("x", "hello")
        with pytest.raises(NotCallableError):
            evaluate(call("x"), storage)

    def test_인자_개수가_적으면_오류(self, storage):
        execute(declare_function("f", ["a", "b"], []), storage)
        with pytest.raises(ArityMismatchError):
            evaluate(call("f", LiteralExpr(1.0)), storage)

    def test_인자_개수가_많으면_오류(self, storage):
        execute(declare_function("f", ["a"], []), storage)
        with pytest.raises(ArityMismatchError):
            evaluate(call("f", LiteralExpr(1.0), LiteralExpr(2.0)), storage)
