import pytest

from executor import ReturnSignal, UndefinedVariableError, evaluate, execute
from nodes.expr import AssignExpr, BinaryExpr, LiteralExpr, VariableExpr
from nodes.stmt import (
    BlockStmt,
    ExpressionStmt,
    ForStmt,
    IfStmt,
    PrintStmt,
    ReturnStmt,
    Stmt,
    VarDeclStmt,
)
from nodes.token_type import TokenType

from helpers import tok


# ── 테스트용 AST 조립 헬퍼 ────────────────────────────────────────────────────

def assign_expr_stmt(name: str, expr) -> ExpressionStmt:
    return ExpressionStmt(AssignExpr(tok(TokenType.IDENTIFIER, name), expr))


def add_to(name: str, amount: float) -> ExpressionStmt:
    """name = name + amount"""
    return assign_expr_stmt(name, BinaryExpr(
        VariableExpr(tok(TokenType.IDENTIFIER, name)),
        tok(TokenType.PLUS, "+"),
        LiteralExpr(amount),
    ))


def assign_stmt(name: str, value: float) -> ExpressionStmt:
    return ExpressionStmt(AssignExpr(tok(TokenType.IDENTIFIER, name), LiteralExpr(value)))


def greater_than(name: str, literal: float) -> BinaryExpr:
    return BinaryExpr(
        VariableExpr(tok(TokenType.IDENTIFIER, name)),
        tok(TokenType.GREATER, ">"),
        LiteralExpr(literal),
    )


def make_for(var: str, start: float, limit: float, body_stmts: list) -> ForStmt:
    """for (var {var} = {start}; {var} < {limit}; {var} = {var} + 1.0) { body }"""
    return ForStmt(
        initializer=VarDeclStmt(tok(TokenType.IDENTIFIER, var), LiteralExpr(start)),
        condition=BinaryExpr(
            VariableExpr(tok(TokenType.IDENTIFIER, var)),
            tok(TokenType.LESS, "<"),
            LiteralExpr(limit),
        ),
        increment=AssignExpr(
            tok(TokenType.IDENTIFIER, var),
            BinaryExpr(
                VariableExpr(tok(TokenType.IDENTIFIER, var)),
                tok(TokenType.PLUS, "+"),
                LiteralExpr(1.0),
            ),
        ),
        body=BlockStmt(statements=body_stmts),
    )


# ── Statement 실행 : 표현식문 / 변수 선언 / 블록 ────────────────────────────────

class TestExecuteExpressionStmt:
    def test_표현식문을_실행하면_부수효과가_반영된다(self, storage):
        storage.define("a", 1.0)
        stmt = ExpressionStmt(AssignExpr(tok(TokenType.IDENTIFIER, "a"), LiteralExpr(9.0)))
        execute(stmt, storage)
        assert storage.get("a") == 9.0


class TestExecuteVarDeclStmt:
    def test_초기값과_함께_변수를_선언한다(self, storage):
        execute(VarDeclStmt(tok(TokenType.IDENTIFIER, "a"), LiteralExpr(3.0)), storage)
        assert storage.get("a") == 3.0

    def test_초기값_없이_선언하면_None으로_저장된다(self, storage):
        execute(VarDeclStmt(tok(TokenType.IDENTIFIER, "a"), None), storage)
        assert storage.get("a") is None


class TestExecuteBlockStmt:
    def test_블록_안_문장들을_순서대로_실행한다(self, storage):
        storage.define("a", 0.0)
        block = BlockStmt(
            [
                ExpressionStmt(AssignExpr(tok(TokenType.IDENTIFIER, "a"), LiteralExpr(1.0))),
                ExpressionStmt(AssignExpr(tok(TokenType.IDENTIFIER, "a"), LiteralExpr(2.0))),
            ]
        )
        execute(block, storage)
        assert storage.get("a") == 2.0

    def test_블록_안에서_바깥_스코프_변수를_읽고_쓸_수_있다(self, storage):
        storage.define("a", 1.0)
        block = BlockStmt(
            [ExpressionStmt(AssignExpr(tok(TokenType.IDENTIFIER, "a"), LiteralExpr(9.0)))]
        )
        execute(block, storage)
        assert storage.get("a") == 9.0

    def test_블록_안에서_선언한_변수는_블록_밖에서_보이지_않는다(self, storage):
        # PDF p.82-83 : 블록 진입 시 새 로컬 저장소 생성, 종료 시 소멸
        block = BlockStmt([VarDeclStmt(tok(TokenType.IDENTIFIER, "b"), LiteralExpr(2.0))])
        execute(block, storage)
        with pytest.raises(UndefinedVariableError):
            storage.get("b")

    def test_빈_블록은_아무_일도_하지_않는다(self, storage):
        execute(BlockStmt([]), storage)  # 예외 없이 끝나야 한다


# ── Statement 실행 : return ──────────────────────────────────────────────────

class TestExecuteReturnStmt:
    def test_값이_있으면_ReturnSignal에_평가된_값을_담아_던진다(self, storage):
        storage.define("a", 3.0)
        stmt = ReturnStmt(
            tok(TokenType.RETURN, "return"),
            BinaryExpr(VariableExpr(tok(TokenType.IDENTIFIER, "a")), tok(TokenType.PLUS, "+"), LiteralExpr(1.0)),
        )
        with pytest.raises(ReturnSignal) as exc_info:
            execute(stmt, storage)
        assert exc_info.value.value == 4.0

    def test_값이_없으면_ReturnSignal의_value가_None이다(self, storage):
        stmt = ReturnStmt(tok(TokenType.RETURN, "return"), None)
        with pytest.raises(ReturnSignal) as exc_info:
            execute(stmt, storage)
        assert exc_info.value.value is None

    def test_블록_안_return이_이후_문장을_건너뛰고_밖으로_전파된다(self, storage):
        storage.define("ran", 0.0)
        block = BlockStmt(
            [
                ReturnStmt(tok(TokenType.RETURN, "return"), LiteralExpr(1.0)),
                ExpressionStmt(AssignExpr(tok(TokenType.IDENTIFIER, "ran"), LiteralExpr(1.0))),
            ]
        )
        with pytest.raises(ReturnSignal) as exc_info:
            execute(block, storage)
        assert exc_info.value.value == 1.0
        assert storage.get("ran") == 0.0


class _지원하지_않는_Stmt(Stmt):
    """executor 가 모르는 임의의 Stmt 타입 (파서 버그 상황을 흉내낸다)."""


class TestExecuteUnsupportedStatement:
    def test_알_수_없는_Stmt_타입은_예외를_발생시킨다(self, storage):
        with pytest.raises(Exception):
            execute(_지원하지_않는_Stmt(), storage)


# ── Statement 실행 : print ──────────────────────────────────────────────────

class TestExecutePrintStmt:
    def test_산술_결과를_출력한다(self, storage, capsys):
        # PDF p.77 : print 3 + 2; -> stdout 에 5 출력
        expr = BinaryExpr(LiteralExpr(3.0), tok(TokenType.PLUS, "+"), LiteralExpr(2.0))
        execute(PrintStmt(expr), storage)
        assert capsys.readouterr().out == "5\n"

    def test_문자열_리터럴을_출력한다(self, storage, capsys):
        execute(PrintStmt(LiteralExpr("hello")), storage)
        assert capsys.readouterr().out == "hello\n"

    def test_true를_출력한다(self, storage, capsys):
        execute(PrintStmt(LiteralExpr(True)), storage)
        assert capsys.readouterr().out == "true\n"

    def test_false를_출력한다(self, storage, capsys):
        execute(PrintStmt(LiteralExpr(False)), storage)
        assert capsys.readouterr().out == "false\n"

    def test_소수점이_있는_숫자를_출력한다(self, storage, capsys):
        execute(PrintStmt(LiteralExpr(3.14)), storage)
        assert capsys.readouterr().out == "3.14\n"

    def test_변수_값을_출력한다(self, storage, capsys):
        storage.define("a", 7.0)
        execute(PrintStmt(VariableExpr(tok(TokenType.IDENTIFIER, "a"))), storage)
        assert capsys.readouterr().out == "7\n"


# ── Statement 실행 : if / 중첩 if ────────────────────────────────────────────

class TestExecuteIfStmt:
    def test_조건이_참이면_then_branch를_실행한다(self, storage):
        # PDF p.48 : if (x > 0) y = 1;
        storage.define("x", 10.0)
        storage.define("y", 0.0)
        execute(IfStmt(greater_than("x", 0.0), assign_stmt("y", 1.0)), storage)
        assert storage.get("y") == 1.0

    def test_조건이_거짓이면_then_branch를_건너뛴다(self, storage):
        storage.define("x", -1.0)
        storage.define("y", 0.0)
        execute(IfStmt(greater_than("x", 0.0), assign_stmt("y", 1.0)), storage)
        assert storage.get("y") == 0.0

    def test_조건이_거짓이면_else_branch를_실행한다(self, storage):
        # PDF p.49 : if (x > 0) y = 1; else y = 2;
        storage.define("x", -1.0)
        storage.define("y", 0.0)
        stmt = IfStmt(greater_than("x", 0.0), assign_stmt("y", 1.0), assign_stmt("y", 2.0))
        execute(stmt, storage)
        assert storage.get("y") == 2.0

    def test_조건이_참이면_else_branch를_실행하지_않는다(self, storage):
        storage.define("x", 10.0)
        storage.define("y", 0.0)
        stmt = IfStmt(greater_than("x", 0.0), assign_stmt("y", 1.0), assign_stmt("y", 2.0))
        execute(stmt, storage)
        assert storage.get("y") == 1.0

    def test_else가_없고_조건이_거짓이면_아무_일도_하지_않는다(self, storage):
        storage.define("x", -1.0)
        storage.define("y", 0.0)
        execute(IfStmt(greater_than("x", 0.0), assign_stmt("y", 1.0), None), storage)
        assert storage.get("y") == 0.0


class TestExecuteNestedIfStmt:
    def test_중첩된_조건이_모두_참인_경우(self, storage):
        # PDF p.14 : if(a>3) { if(b>3) { ... } }
        storage.define("a", 10.0)
        storage.define("b", 10.0)
        storage.define("y", 0.0)
        inner = IfStmt(greater_than("b", 3.0), assign_stmt("y", 1.0))
        outer = IfStmt(greater_than("a", 3.0), inner)
        execute(outer, storage)
        assert storage.get("y") == 1.0

    def test_바깥은_참이고_안쪽은_거짓인_경우(self, storage):
        storage.define("a", 10.0)
        storage.define("b", 1.0)
        storage.define("y", 0.0)
        inner = IfStmt(greater_than("b", 3.0), assign_stmt("y", 1.0))
        outer = IfStmt(greater_than("a", 3.0), inner)
        execute(outer, storage)
        assert storage.get("y") == 0.0

    def test_바깥이_거짓이면_안쪽은_실행되지_않는다(self, storage):
        storage.define("a", 1.0)
        storage.define("b", 10.0)
        storage.define("y", 0.0)
        inner = IfStmt(greater_than("b", 3.0), assign_stmt("y", 1.0))
        outer = IfStmt(greater_than("a", 3.0), inner)
        execute(outer, storage)
        assert storage.get("y") == 0.0

    def test_중첩된_if_else_체인(self, storage):
        # if (a>3) { if (b>3) y=1; else y=2; } else { y=3; }
        storage.define("a", 10.0)
        storage.define("b", 1.0)
        storage.define("y", 0.0)
        inner = IfStmt(greater_than("b", 3.0), assign_stmt("y", 1.0), assign_stmt("y", 2.0))
        outer = IfStmt(greater_than("a", 3.0), inner, assign_stmt("y", 3.0))
        execute(outer, storage)
        assert storage.get("y") == 2.0


# ── Statement 실행 : for ──────────────────────────────────────────────────────

class TestExecuteForStmt:
    def test_루프가_정해진_횟수만큼_실행된다(self, storage):
        execute(make_for("i", 0.0, 5.0, []), storage)
        assert storage.get("i") == 5.0

    def test_조건이_처음부터_false이면_body가_실행되지_않는다(self, storage):
        storage.define("executed", 0.0)
        execute(make_for("i", 0.0, 0.0, [add_to("executed", 1.0)]), storage)
        assert storage.get("executed") == 0.0

    def test_loop_variable이_매_iteration마다_업데이트된다(self, storage):
        storage.define("sum", 0.0)
        body = [assign_expr_stmt("sum", BinaryExpr(
            VariableExpr(tok(TokenType.IDENTIFIER, "sum")),
            tok(TokenType.PLUS, "+"),
            VariableExpr(tok(TokenType.IDENTIFIER, "i")),
        ))]
        execute(make_for("i", 0.0, 3.0, body), storage)
        assert storage.get("sum") == pytest.approx(3.0)  # 0 + 1 + 2

    def test_for_종료_후_loop_variable의_마지막_값이_유지된다(self, storage):
        execute(make_for("i", 0.0, 3.0, []), storage)
        assert storage.get("i") == 3.0

    def test_body에서_외부_변수에_assignment를_실행할_수_있다(self, storage):
        storage.define("last", -1.0)
        body = [assign_expr_stmt("last", VariableExpr(tok(TokenType.IDENTIFIER, "i")))]
        execute(make_for("i", 0.0, 3.0, body), storage)
        assert storage.get("last") == 2.0

    def test_body_실행_횟수가_range_길이와_일치한다(self, storage):
        storage.define("count", 0.0)
        execute(make_for("i", 0.0, 4.0, [add_to("count", 1.0)]), storage)
        assert storage.get("count") == 4.0

    def test_initializer_없이도_동작한다(self, storage):
        storage.define("i", 0.0)
        for_stmt = ForStmt(
            initializer=None,
            condition=BinaryExpr(
                VariableExpr(tok(TokenType.IDENTIFIER, "i")),
                tok(TokenType.LESS, "<"),
                LiteralExpr(3.0),
            ),
            increment=AssignExpr(
                tok(TokenType.IDENTIFIER, "i"),
                BinaryExpr(
                    VariableExpr(tok(TokenType.IDENTIFIER, "i")),
                    tok(TokenType.PLUS, "+"),
                    LiteralExpr(1.0),
                ),
            ),
            body=BlockStmt(statements=[]),
        )
        execute(for_stmt, storage)
        assert storage.get("i") == 3.0

    def test_increment_없이_조건이_처음부터_false이면_body가_실행되지_않는다(self, storage):
        storage.define("ran", 0.0)
        for_stmt = ForStmt(
            initializer=VarDeclStmt(tok(TokenType.IDENTIFIER, "i"), LiteralExpr(5.0)),
            condition=BinaryExpr(
                VariableExpr(tok(TokenType.IDENTIFIER, "i")),
                tok(TokenType.LESS, "<"),
                LiteralExpr(3.0),
            ),
            increment=None,
            body=BlockStmt(statements=[add_to("ran", 1.0)]),
        )
        execute(for_stmt, storage)
        assert storage.get("ran") == 0.0

    def test_body_내부에서_var_선언이_블록_스코프에서_실행된다(self, storage):
        storage.define("total", 0.0)
        body = [
            VarDeclStmt(tok(TokenType.IDENTIFIER, "tmp"), LiteralExpr(10.0)),
            assign_expr_stmt("total", BinaryExpr(
                VariableExpr(tok(TokenType.IDENTIFIER, "total")),
                tok(TokenType.PLUS, "+"),
                VariableExpr(tok(TokenType.IDENTIFIER, "tmp")),
            )),
        ]
        execute(make_for("i", 0.0, 3.0, body), storage)
        assert storage.get("total") == 30.0

    def test_body_내부에서_print가_실행된다(self, storage, capsys):
        body = [PrintStmt(VariableExpr(tok(TokenType.IDENTIFIER, "i")))]
        execute(make_for("i", 0.0, 3.0, body), storage)
        assert capsys.readouterr().out == "0\n1\n2\n"


class TestExecuteNestedForStmt:
    def test_nested_for_loop이_가능하다(self, storage):
        storage.define("count", 0.0)
        inner_for = make_for("j", 0.0, 3.0, [add_to("count", 1.0)])
        execute(make_for("i", 0.0, 3.0, [inner_for]), storage)
        assert storage.get("count") == 9.0

    def test_outer_loop_variable이_유지된다(self, storage):
        storage.define("count", 0.0)
        inner_for = make_for("j", 0.0, 2.0, [add_to("count", 1.0)])
        execute(make_for("i", 0.0, 2.0, [inner_for]), storage)
        assert storage.get("i") == 2.0
        assert storage.get("count") == 4.0

    def test_inner_loop_variable이_매_outer_iteration마다_재시작된다(self, storage):
        storage.define("sum_j", 0.0)
        inner_body = [assign_expr_stmt("sum_j", BinaryExpr(
            VariableExpr(tok(TokenType.IDENTIFIER, "sum_j")),
            tok(TokenType.PLUS, "+"),
            VariableExpr(tok(TokenType.IDENTIFIER, "j")),
        ))]
        execute(make_for("i", 0.0, 3.0, [make_for("j", 0.0, 3.0, inner_body)]), storage)
        assert storage.get("sum_j") == pytest.approx(9.0)  # 3 * (0+1+2)


# ── 통합 테스트 : for → if → print ────────────────────────────────────────────

class TestExecuteForIfPrintIntegration:
    def test_for_안에서_if_조건을_만족할_때만_print가_실행된다(self, storage, capsys):
        # for (i=0; i<5; i=i+1) { if (i > 2) print i; }
        body = [IfStmt(greater_than("i", 2.0), PrintStmt(VariableExpr(tok(TokenType.IDENTIFIER, "i"))))]
        execute(make_for("i", 0.0, 5.0, body), storage)
        assert capsys.readouterr().out == "3\n4\n"

    def test_for_안의_if_else_분기가_매_iteration마다_동작한다(self, storage, capsys):
        # for (i=0; i<3; i=i+1) { if (i > 0) print i; else print "zero"; }
        then_branch = PrintStmt(VariableExpr(tok(TokenType.IDENTIFIER, "i")))
        else_branch = PrintStmt(LiteralExpr("zero"))
        body = [IfStmt(greater_than("i", 0.0), then_branch, else_branch)]
        execute(make_for("i", 0.0, 3.0, body), storage)
        assert capsys.readouterr().out == "zero\n1\n2\n"

    def test_if_조건이_한번도_참이_아니면_아무것도_출력되지_않는다(self, storage, capsys):
        body = [IfStmt(greater_than("i", 10.0), PrintStmt(VariableExpr(tok(TokenType.IDENTIFIER, "i"))))]
        execute(make_for("i", 0.0, 3.0, body), storage)
        assert capsys.readouterr().out == ""

    def test_for_안의_if_내부에서_바깥_스코프_변수를_누적한다(self, storage):
        # for (i=0; i<5; i=i+1) { if (i > 2) count = count + 1; }
        storage.define("count", 0.0)
        body = [IfStmt(greater_than("i", 2.0), add_to("count", 1.0))]
        execute(make_for("i", 0.0, 5.0, body), storage)
        assert storage.get("count") == 2.0  # i=3, i=4 두 번


# ── 통합 테스트 : if → for → print ────────────────────────────────────────────

class TestExecuteIfForPrintIntegration:
    def test_조건이_참이면_then_branch의_for_루프가_실행되어_print한다(self, storage, capsys):
        # if (x > 0) { for (i=0; i<3; i=i+1) print i; }
        storage.define("x", 10.0)
        then_branch = BlockStmt([make_for("i", 0.0, 3.0, [PrintStmt(VariableExpr(tok(TokenType.IDENTIFIER, "i")))])])
        execute(IfStmt(greater_than("x", 0.0), then_branch), storage)
        assert capsys.readouterr().out == "0\n1\n2\n"

    def test_조건이_거짓이고_else가_없으면_for_루프가_실행되지_않는다(self, storage, capsys):
        storage.define("x", -1.0)
        then_branch = BlockStmt([make_for("i", 0.0, 3.0, [PrintStmt(VariableExpr(tok(TokenType.IDENTIFIER, "i")))])])
        execute(IfStmt(greater_than("x", 0.0), then_branch), storage)
        assert capsys.readouterr().out == ""

    def test_조건이_거짓이면_else_branch의_for_루프가_대신_실행된다(self, storage, capsys):
        # if (x > 0) print "positive"; else { for (i=0; i<2; i=i+1) print i; }
        storage.define("x", -1.0)
        then_branch = PrintStmt(LiteralExpr("positive"))
        else_branch = BlockStmt([make_for("i", 0.0, 2.0, [PrintStmt(VariableExpr(tok(TokenType.IDENTIFIER, "i")))])])
        execute(IfStmt(greater_than("x", 0.0), then_branch, else_branch), storage)
        assert capsys.readouterr().out == "0\n1\n"

    def test_if_안의_for_루프가_바깥_스코프_변수를_누적한다(self, storage):
        # if (x > 0) { for (i=0; i<5; i=i+1) count = count + 1; }
        storage.define("x", 10.0)
        storage.define("count", 0.0)
        then_branch = BlockStmt([make_for("i", 0.0, 5.0, [add_to("count", 1.0)])])
        execute(IfStmt(greater_than("x", 0.0), then_branch), storage)
        assert storage.get("count") == 5.0
