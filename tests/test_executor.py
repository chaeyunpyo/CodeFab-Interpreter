"""Executor TDD 테스트.

RED -> GREEN 순서로 작성됨.
모든 테스트는 src/executor.py 구현 전 먼저 실패해야 한다.

Expression 평가(evaluate)와 Statement 실행(execute)을 한 파일(src/executor.py)에서
처리하며, 변수 저장은 storage.Storage 를 그대로 사용한다.

가정한 계약 (팀 합의에 따라 조정 가능):
- evaluate(expr, storage) -> Any
- execute(stmt, storage) -> None
- 연산자 판별은 Token.type 으로 하고, Token.lexeme 은 오류 메시지용으로만 쓴다.
- 숫자는 내부적으로 항상 float 로 다룬다. (Tokenizer의 NUMBER 규칙과 동일)
- and/or 는 단축 평가(short-circuit)를 하며, 스스로 값을 True/False로
  강제 변환하지 않고 "판단에 쓰인 피연산자의 평가값"을 그대로 반환한다.
"""

import pytest

from executor import DivideByZeroError, TypeMismatchError, evaluate, execute, stringify
from nodes.expr import (
    AssignExpr,
    BinaryExpr,
    GroupingExpr,
    LiteralExpr,
    LogicalExpr,
    UnaryExpr,
    VariableExpr,
)
from nodes.stmt import BlockStmt, ExpressionStmt, ForStmt, IfStmt, PrintStmt, Stmt, VarDeclStmt
from nodes.token_type import TokenType
from nodes.tokens import Token
from storage import Storage, UndefinedVariableError


def tok(token_type: TokenType, lexeme: str) -> Token:
    """이름/연산자 토큰을 짧게 만들기 위한 헬퍼. literal/line은 테스트에 불필요."""
    return Token(token_type, lexeme)


@pytest.fixture
def storage() -> Storage:
    return Storage()


# ── Expression 평가 : 리터럴 / 변수 / 대입 ──────────────────────────────────────

class TestEvaluateLiteral:
    def test_숫자_리터럴을_평가하면_값을_반환한다(self, storage):
        assert evaluate(LiteralExpr(3.0), storage) == 3.0

    def test_문자열_리터럴을_평가하면_값을_반환한다(self, storage):
        assert evaluate(LiteralExpr("hello"), storage) == "hello"

    def test_불리언_리터럴을_평가하면_값을_반환한다(self, storage):
        assert evaluate(LiteralExpr(True), storage) is True


class TestEvaluateVariable:
    def test_정의된_변수를_평가하면_저장된_값을_반환한다(self, storage):
        storage.define("a", 10.0)
        assert evaluate(VariableExpr(tok(TokenType.IDENTIFIER, "a")), storage) == 10.0

    def test_정의되지_않은_변수를_평가하면_예외를_발생시킨다(self, storage):
        with pytest.raises(UndefinedVariableError):
            evaluate(VariableExpr(tok(TokenType.IDENTIFIER, "x")), storage)


class TestEvaluateAssign:
    def test_대입식을_평가하면_저장소_값이_갱신되고_그_값을_반환한다(self, storage):
        storage.define("a", 1.0)
        result = evaluate(AssignExpr(tok(TokenType.IDENTIFIER, "a"), LiteralExpr(5.0)), storage)
        assert result == 5.0
        assert storage.get("a") == 5.0

    def test_정의되지_않은_변수에_대입하면_예외를_발생시킨다(self, storage):
        with pytest.raises(UndefinedVariableError):
            evaluate(AssignExpr(tok(TokenType.IDENTIFIER, "x"), LiteralExpr(1.0)), storage)


# ── Expression 평가 : 단항 / 이항 / 논리 / 그룹 ────────────────────────────────

class TestEvaluateUnary:
    def test_음수_부호는_숫자를_반전한다(self, storage):
        expr = UnaryExpr(tok(TokenType.MINUS, "-"), LiteralExpr(5.0))
        assert evaluate(expr, storage) == -5.0

    def test_느낌표는_true를_false로_반전한다(self, storage):
        expr = UnaryExpr(tok(TokenType.BANG, "!"), LiteralExpr(True))
        assert evaluate(expr, storage) is False

    def test_느낌표는_false를_true로_반전한다(self, storage):
        expr = UnaryExpr(tok(TokenType.BANG, "!"), LiteralExpr(False))
        assert evaluate(expr, storage) is True

    def test_숫자가_아닌_값에_음수_부호를_쓰면_타입_오류가_발생한다(self, storage):
        expr = UnaryExpr(tok(TokenType.MINUS, "-"), LiteralExpr("hi"))
        with pytest.raises(TypeMismatchError):
            evaluate(expr, storage)


class TestEvaluateBinaryArithmetic:
    @pytest.mark.parametrize(
        "op_type, op_lexeme, left, right, expected",
        [
            (TokenType.PLUS, "+", 3.0, 7.0, 10.0),
            (TokenType.MINUS, "-", 7.0, 3.0, 4.0),
            (TokenType.STAR, "*", 4.0, 5.0, 20.0),
            (TokenType.SLASH, "/", 10.0, 2.0, 5.0),
        ],
    )
    def test_사칙연산_결과가_올바르다(self, storage, op_type, op_lexeme, left, right, expected):
        expr = BinaryExpr(LiteralExpr(left), tok(op_type, op_lexeme), LiteralExpr(right))
        assert evaluate(expr, storage) == pytest.approx(expected)

    def test_0으로_나누면_예외를_발생시킨다(self, storage):
        # PDF p.88 : a = 3 / 0;
        expr = BinaryExpr(LiteralExpr(3.0), tok(TokenType.SLASH, "/"), LiteralExpr(0.0))
        with pytest.raises(DivideByZeroError):
            evaluate(expr, storage)

    def test_숫자에서_문자열을_빼면_타입_오류가_발생한다(self, storage):
        # PDF p.86 : 3 - "hello"
        expr = BinaryExpr(LiteralExpr(3.0), tok(TokenType.MINUS, "-"), LiteralExpr("hello"))
        with pytest.raises(TypeMismatchError):
            evaluate(expr, storage)

    def test_불리언끼리_곱하면_타입_오류가_발생한다(self, storage):
        # PDF p.86 : true * false
        expr = BinaryExpr(LiteralExpr(True), tok(TokenType.STAR, "*"), LiteralExpr(False))
        with pytest.raises(TypeMismatchError):
            evaluate(expr, storage)


class TestEvaluateBinaryComparison:
    def test_큰_비교가_참인_경우(self, storage):
        expr = BinaryExpr(LiteralExpr(5.0), tok(TokenType.GREATER, ">"), LiteralExpr(3.0))
        assert evaluate(expr, storage) is True

    def test_큰_비교가_거짓인_경우(self, storage):
        expr = BinaryExpr(LiteralExpr(1.0), tok(TokenType.GREATER, ">"), LiteralExpr(3.0))
        assert evaluate(expr, storage) is False

    def test_작은_비교가_참인_경우(self, storage):
        expr = BinaryExpr(LiteralExpr(1.0), tok(TokenType.LESS, "<"), LiteralExpr(3.0))
        assert evaluate(expr, storage) is True

    def test_크거나_같은_비교가_참인_경우(self, storage):
        expr = BinaryExpr(LiteralExpr(5.0), tok(TokenType.GREATER_EQUAL, ">="), LiteralExpr(5.0))
        assert evaluate(expr, storage) is True

    def test_크거나_같은_비교가_거짓인_경우(self, storage):
        expr = BinaryExpr(LiteralExpr(3.0), tok(TokenType.GREATER_EQUAL, ">="), LiteralExpr(5.0))
        assert evaluate(expr, storage) is False

    def test_작거나_같은_비교가_거짓인_경우(self, storage):
        expr = BinaryExpr(LiteralExpr(5.0), tok(TokenType.LESS_EQUAL, "<="), LiteralExpr(3.0))
        assert evaluate(expr, storage) is False

    def test_작거나_같은_비교가_참인_경우(self, storage):
        expr = BinaryExpr(LiteralExpr(3.0), tok(TokenType.LESS_EQUAL, "<="), LiteralExpr(5.0))
        assert evaluate(expr, storage) is True

    def test_같거나_큰_비교가_거짓인_경우(self, storage):
        # EQUAL_GREATER 의 lexeme 은 tokenizer 기준 "=>" 이다 (TWO_CHAR_TOKENS 참고).
        expr = BinaryExpr(LiteralExpr(5.0), tok(TokenType.EQUAL_GREATER, "=>"), LiteralExpr(6.0))
        assert evaluate(expr, storage) is False

    def test_같거나_큰_비교가_참인_경우(self, storage):
        expr = BinaryExpr(LiteralExpr(5.0), tok(TokenType.EQUAL_GREATER, "=>"), LiteralExpr(5.0))
        assert evaluate(expr, storage) is True

    def test_같거나_작은_비교가_참인_경우(self, storage):
        expr = BinaryExpr(LiteralExpr(5.0), tok(TokenType.EQUAL_LESS, "=<"), LiteralExpr(6.0))
        assert evaluate(expr, storage) is True

    def test_같거나_작은_비교가_거짓인_경우(self, storage):
        expr = BinaryExpr(LiteralExpr(6.0), tok(TokenType.EQUAL_LESS, "=<"), LiteralExpr(5.0))
        assert evaluate(expr, storage) is False

    def test_같은_비교가_참인_경우(self, storage):
        expr = BinaryExpr(LiteralExpr(5.0), tok(TokenType.EQUAL_EQUAL, "=="), LiteralExpr(5.0))
        assert evaluate(expr, storage) is True

    def test_같은_비교가_거짓인_경우(self, storage):
        expr = BinaryExpr(LiteralExpr(5.0), tok(TokenType.EQUAL_EQUAL, "=="), LiteralExpr(3.0))
        assert evaluate(expr, storage) is False

    def test_같지_않은_비교가_거짓인_경우(self, storage):
        expr = BinaryExpr(LiteralExpr(5.0), tok(TokenType.BANG_EQUAL, "!="), LiteralExpr(5.0))
        assert evaluate(expr, storage) is False

    def test_같지_않은_비교가_참인_경우(self, storage):
        expr = BinaryExpr(LiteralExpr(5.0), tok(TokenType.BANG_EQUAL, "!="), LiteralExpr(3.0))
        assert evaluate(expr, storage) is True


class TestEvaluateGrouping:
    def test_괄호_안_값을_그대로_반환한다(self, storage):
        assert evaluate(GroupingExpr(LiteralExpr(42.0)), storage) == 42.0

    def test_괄호로_연산_우선순위를_바꿀_수_있다(self, storage):
        # PDF p.41 : (a + b) * 3, a=2, b=3 -> 15
        storage.define("a", 2.0)
        storage.define("b", 3.0)
        inner = BinaryExpr(
            VariableExpr(tok(TokenType.IDENTIFIER, "a")),
            tok(TokenType.PLUS, "+"),
            VariableExpr(tok(TokenType.IDENTIFIER, "b")),
        )
        expr = BinaryExpr(GroupingExpr(inner), tok(TokenType.STAR, "*"), LiteralExpr(3.0))
        assert evaluate(expr, storage) == pytest.approx(15.0)


class TestEvaluateLogical:
    def test_and는_왼쪽이_false면_오른쪽을_평가하지_않는다(self, storage):
        # false and (x = 1) -> x가 미정의라도 오른쪽이 평가되지 않아야 에러가 안 난다.
        right = AssignExpr(tok(TokenType.IDENTIFIER, "x"), LiteralExpr(1.0))
        expr = LogicalExpr(LiteralExpr(False), tok(TokenType.AND, "and"), right)
        assert evaluate(expr, storage) is False

    def test_and는_왼쪽이_true면_오른쪽_값을_반환한다(self, storage):
        expr = LogicalExpr(LiteralExpr(True), tok(TokenType.AND, "and"), LiteralExpr(5.0))
        assert evaluate(expr, storage) == 5.0

    def test_or는_왼쪽이_true면_오른쪽을_평가하지_않는다(self, storage):
        right = AssignExpr(tok(TokenType.IDENTIFIER, "x"), LiteralExpr(1.0))
        expr = LogicalExpr(LiteralExpr(True), tok(TokenType.OR, "or"), right)
        assert evaluate(expr, storage) is True

    def test_or는_왼쪽이_false면_오른쪽_값을_반환한다(self, storage):
        expr = LogicalExpr(LiteralExpr(False), tok(TokenType.OR, "or"), LiteralExpr(5.0))
        assert evaluate(expr, storage) == 5.0


class TestStringify:
    @pytest.mark.parametrize(
        "value, expected",
        [
            (5.0, "5"),
            (3.14, "3.14"),
            ("hello", "hello"),
            (True, "true"),
            (False, "false"),
        ],
    )
    def test_값을_출력용_문자열로_변환한다(self, value, expected):
        assert stringify(value) == expected


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

def assign_expr_stmt(name: str, expr) -> ExpressionStmt:
    return ExpressionStmt(AssignExpr(tok(TokenType.IDENTIFIER, name), expr))


def add_to(name: str, amount: float) -> ExpressionStmt:
    """name = name + amount"""
    return assign_expr_stmt(name, BinaryExpr(
        VariableExpr(tok(TokenType.IDENTIFIER, name)),
        tok(TokenType.PLUS, "+"),
        LiteralExpr(amount),
    ))


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


def assign_stmt(name: str, value: float) -> ExpressionStmt:
    return ExpressionStmt(AssignExpr(tok(TokenType.IDENTIFIER, name), LiteralExpr(value)))


def greater_than(name: str, literal: float) -> BinaryExpr:
    return BinaryExpr(
        VariableExpr(tok(TokenType.IDENTIFIER, name)),
        tok(TokenType.GREATER, ">"),
        LiteralExpr(literal),
    )


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
