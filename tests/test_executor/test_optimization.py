"""실행전 최적화 (요구사항_정리/실행전_최적화.md) - Executor 쪽 Test Double 검증 2종.

Checker가 만들어둔 결과(checker.locals의 거리, 접힌 리터럴)를 Executor가
실제로 활용하는지 pytest-mock(mocker)으로 갈아끼운 스파이로 확인한다
(Strategy 패턴 활용).

- 정적 바인딩 검증: 거리를 알 때 get_resolved/set_resolved가 스코프 체인을
  거슬러 올라가지(reversed) 않고 계산된 위치로 즉시 접근하는지 확인.
- 상수 연산 최적화 검증: 접힌 리터럴 표현식은 반복 실행해도 이항연산 평가가
  0회인지, 반대로 변수가 섞여 안 접힌 표현식은 실행마다 평가되는지 확인.
"""
import executor._expr as expr_module
from checker import CheckerUnit
from executor import Storage, execute
from nodes.expr import AssignExpr, BinaryExpr, LiteralExpr, VariableExpr
from nodes.stmt import BlockStmt, PrintStmt, VarDeclStmt
from nodes.token_type import TokenType

from helpers import tok


def make_var(name: str) -> VariableExpr:
    return VariableExpr(tok(TokenType.IDENTIFIER, name))


def make_block(*statements) -> BlockStmt:
    return BlockStmt(statements=list(statements))


# ── 정적 바인딩 검증 : 조회 경로 검증 ────────────────────────────────────────

class TestStaticBindingSkipsScopeChainWalk:
    def test_거리를_알면_get_resolved가_스코프_체인을_거슬러_올라가지_않는다(self, mocker):
        storage = Storage()
        storage.push_scope()
        storage.push_scope()
        storage._scopes[-2]["a"] = 99  # 안쪽에서 한 단계 위 스코프(distance 1)

        var_expr = make_var("a")
        storage.locals = {id(var_expr): 1}

        spy = mocker.patch("builtins.reversed", wraps=reversed)
        result = storage.get_resolved(var_expr, "a")

        assert result == 99
        spy.assert_not_called()

    def test_거리를_모르면_get_resolved가_기존_체인_탐색으로_폴백한다(self, mocker):
        storage = Storage()
        storage.define("g", 5)
        var_expr = make_var("g")  # locals에 항목 없음 -> 전역/함수경계 참조

        spy = mocker.patch("builtins.reversed", wraps=reversed)
        result = storage.get_resolved(var_expr, "g")

        assert result == 5
        spy.assert_called()

    def test_거리를_알면_set_resolved도_스코프_체인을_거슬러_올라가지_않는다(self, mocker):
        storage = Storage()
        storage.push_scope()
        storage.push_scope()
        storage._scopes[-2]["a"] = 1

        assign_expr = AssignExpr(tok(TokenType.IDENTIFIER, "a"), LiteralExpr(2.0))
        storage.locals = {id(assign_expr): 1}

        spy = mocker.patch("builtins.reversed", wraps=reversed)
        storage.set_resolved(assign_expr, "a", 42)

        spy.assert_not_called()
        assert storage._scopes[-2]["a"] == 42

    def test_실제_체커_거리로_깊이_중첩된_지역변수를_조회해도_체인을_거슬러_올라가지_않는다(self, mocker, capsys):
        # { var a = 1; { { print a; } } }  -- 선언보다 두 블록 안쪽, 거리 2.
        var_expr = make_var("a")
        block = make_block(
            VarDeclStmt(tok(TokenType.IDENTIFIER, "a"), LiteralExpr(1.0)),
            make_block(make_block(PrintStmt(expression=var_expr))),
        )

        checker = CheckerUnit([block])
        checker.check()
        assert checker.locals[id(var_expr)] == 2

        storage = Storage(checker.locals)
        spy = mocker.patch("builtins.reversed", wraps=reversed)
        execute(block, storage)

        spy.assert_not_called()
        assert capsys.readouterr().out == "1\n"


# ── 상수 연산 최적화 검증 : 연산 횟수 검증 ───────────────────────────────────

class TestConstantFoldingSkipsRuntimeBinaryEvaluation:
    def test_접힌_리터럴_표현식은_반복_실행해도_이항연산_평가가_0회다(self, mocker, capsys):
        # print (1 + 2) * 3;  -- checker가 실행 전에 9로 접어둔다.
        folded = BinaryExpr(
            BinaryExpr(LiteralExpr(1.0), tok(TokenType.PLUS, "+"), LiteralExpr(2.0)),
            tok(TokenType.STAR, "*"),
            LiteralExpr(3.0),
        )
        stmt = PrintStmt(expression=folded)
        checker = CheckerUnit([stmt])
        checker.check()
        assert isinstance(stmt.expression, LiteralExpr)  # 리터럴로 접힘 확인

        storage = Storage(checker.locals)
        spy = mocker.spy(expr_module, "_evaluate_binary")
        mocker.patch.dict(expr_module._EXPR_EVALUATORS, {BinaryExpr: spy})

        for _ in range(100):  # 루프 100회를 흉내낸다 (요구사항_정리/실행전_최적화.md의 800만->100만 예시와 동일한 취지).
            execute(stmt, storage)

        assert spy.call_count == 0
        assert capsys.readouterr().out == "9\n" * 100

    def test_변수가_섞인_표현식은_접히지_않아_실행마다_이항연산이_평가된다(self, mocker):
        # print n + 1;  -- 변수가 섞여 있어 접기 대상이 아니다.
        mixed = BinaryExpr(make_var("n"), tok(TokenType.PLUS, "+"), LiteralExpr(1.0))
        stmt = PrintStmt(expression=mixed)
        checker = CheckerUnit([stmt])
        checker.check()
        assert stmt.expression is mixed  # 접히지 않고 원본 그대로

        storage = Storage(checker.locals)
        storage.define("n", 1.0)
        spy = mocker.spy(expr_module, "_evaluate_binary")
        mocker.patch.dict(expr_module._EXPR_EVALUATORS, {BinaryExpr: spy})

        for _ in range(5):
            execute(stmt, storage)

        assert spy.call_count == 5
