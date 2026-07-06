"""ForStmt 실행 TDD 테스트.

for_executor.execute() / execute_for() 의 동작을 검증한다.

test_executor.py 의 인터페이스 컨벤션을 따른다:
    - tok() 헬퍼로 Token 생성
    - pytest.fixture 로 storage 공유
    - 숫자는 float 사용

Assembly / Parser 가 미완성이므로 AST 객체를 직접 생성하여 테스트한다.
ForStmt 는 C-style: for (initializer; condition; increment) body
"""

import pytest

from nodes.expr import AssignExpr, BinaryExpr, LiteralExpr, VariableExpr
from nodes.stmt import BlockStmt, ExpressionStmt, ForStmt, PrintStmt, VarDeclStmt
from nodes.token_type import TokenType
from nodes.tokens import Token
from storage import Storage, UndefinedVariableError
from for_executor import execute, execute_for


def tok(token_type: TokenType, lexeme: str) -> Token:
    return Token(token_type, lexeme)


@pytest.fixture
def storage() -> Storage:
    return Storage()


# ── AST 생성 헬퍼 ─────────────────────────────────────────────────────────────

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


def assign_expr_stmt(name: str, expr) -> ExpressionStmt:
    return ExpressionStmt(AssignExpr(tok(TokenType.IDENTIFIER, name), expr))


def add_to(name: str, amount: float) -> ExpressionStmt:
    """name = name + amount"""
    return assign_expr_stmt(name, BinaryExpr(
        VariableExpr(tok(TokenType.IDENTIFIER, name)),
        tok(TokenType.PLUS, "+"),
        LiteralExpr(amount),
    ))


# ── ForStmt 기본 동작 ──────────────────────────────────────────────────────────

class TestForExecutionBasic:
    def test_루프가_정해진_횟수만큼_실행된다(self, storage):
        """for (var i=0; i<5; i=i+1) {} → i == 5.0"""
        execute_for(make_for("i", 0.0, 5.0, []), storage)
        assert storage.get("i") == 5.0

    def test_빈_iterable이면_body가_실행되지_않는다(self, storage):
        """조건이 처음부터 false → body 0회 실행."""
        storage.define("executed", 0.0)
        execute_for(make_for("i", 0.0, 0.0, [add_to("executed", 1.0)]), storage)
        assert storage.get("executed") == 0.0

    def test_loop_variable이_매_iteration마다_업데이트된다(self, storage):
        """sum = 0+1+2 = 3.0 이면 i 가 0,1,2 순으로 업데이트된 것."""
        storage.define("sum", 0.0)
        body = [assign_expr_stmt("sum", BinaryExpr(
            VariableExpr(tok(TokenType.IDENTIFIER, "sum")),
            tok(TokenType.PLUS, "+"),
            VariableExpr(tok(TokenType.IDENTIFIER, "i")),
        ))]
        execute_for(make_for("i", 0.0, 3.0, body), storage)
        assert storage.get("sum") == pytest.approx(3.0)  # 0 + 1 + 2

    def test_for_종료_후_loop_variable의_마지막_값이_유지된다(self, storage):
        """Python 과 동일: 루프 종료 후 loop variable 은 조건이 거짓이 된 값을 유지한다."""
        execute_for(make_for("i", 0.0, 3.0, []), storage)
        assert storage.get("i") == 3.0

    def test_body에서_assignment를_실행할_수_있다(self, storage):
        """for body 내에서 외부 변수에 assignment 가능."""
        storage.define("last", -1.0)
        body = [assign_expr_stmt("last", VariableExpr(tok(TokenType.IDENTIFIER, "i")))]
        execute_for(make_for("i", 0.0, 3.0, body), storage)
        assert storage.get("last") == 2.0  # 마지막 iteration 의 i 값

    def test_body_실행_횟수가_range_길이와_일치한다(self, storage):
        """for (var i=0; i<4; i++) { count++ } → count == 4.0"""
        storage.define("count", 0.0)
        execute_for(make_for("i", 0.0, 4.0, [add_to("count", 1.0)]), storage)
        assert storage.get("count") == 4.0


class TestForExecutionOptional:
    def test_initializer_없이도_동작한다(self, storage):
        """for (; i<3; i=i+1) {} — i 는 사전에 define 되어 있음."""
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
        execute_for(for_stmt, storage)
        assert storage.get("i") == 3.0

    def test_increment_없이_조건이_처음부터_false면_body가_실행되지_않는다(self, storage):
        """i=5 로 시작, i<3 조건 → 즉시 종료, body 0회 실행."""
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
        execute_for(for_stmt, storage)
        assert storage.get("ran") == 0.0


# ── 중첩 ForStmt ──────────────────────────────────────────────────────────────

class TestNestedForExecution:
    def test_nested_for_loop이_가능하다(self, storage):
        """
        for (var i=0; i<3; i++) {
            for (var j=0; j<3; j++) { count++ }
        }
        → count == 9.0
        """
        storage.define("count", 0.0)
        inner_for = make_for("j", 0.0, 3.0, [add_to("count", 1.0)])
        execute_for(make_for("i", 0.0, 3.0, [inner_for]), storage)
        assert storage.get("count") == 9.0

    def test_nested_for에서_outer_loop_variable이_유지된다(self, storage):
        storage.define("count", 0.0)
        inner_for = make_for("j", 0.0, 2.0, [add_to("count", 1.0)])
        execute_for(make_for("i", 0.0, 2.0, [inner_for]), storage)
        assert storage.get("i") == 2.0
        assert storage.get("count") == 4.0  # 2 * 2

    def test_nested_for에서_inner_loop_variable이_매_outer_iteration마다_재시작된다(self, storage):
        """j 는 outer BlockStmt 내부에서 define → 매 outer iteration 마다 0 부터 재시작."""
        storage.define("sum_j", 0.0)
        inner_body = [assign_expr_stmt("sum_j", BinaryExpr(
            VariableExpr(tok(TokenType.IDENTIFIER, "sum_j")),
            tok(TokenType.PLUS, "+"),
            VariableExpr(tok(TokenType.IDENTIFIER, "j")),
        ))]
        execute_for(make_for("i", 0.0, 3.0, [make_for("j", 0.0, 3.0, inner_body)]), storage)
        assert storage.get("sum_j") == pytest.approx(9.0)  # 3 * (0+1+2)


# ── executor 공통 dispatch 통합 ───────────────────────────────────────────────

class TestForExecutionDispatch:
    def test_execute_래퍼를_통해_ForStmt가_실행된다(self, storage):
        """for_executor.execute() 가 ForStmt 를 올바르게 분기한다."""
        storage.define("result", 0.0)
        execute(make_for("i", 0.0, 3.0, [add_to("result", 1.0)]), storage)
        assert storage.get("result") == 3.0

    def test_for_body_내부에서_var_선언이_가능하다(self, storage):
        """body BlockStmt 안의 VarDeclStmt 가 블록 스코프 내에서 정상 실행된다."""
        storage.define("total", 0.0)
        body = [
            VarDeclStmt(tok(TokenType.IDENTIFIER, "tmp"), LiteralExpr(10.0)),
            assign_expr_stmt("total", BinaryExpr(
                VariableExpr(tok(TokenType.IDENTIFIER, "total")),
                tok(TokenType.PLUS, "+"),
                VariableExpr(tok(TokenType.IDENTIFIER, "tmp")),
            )),
        ]
        execute_for(make_for("i", 0.0, 3.0, body), storage)
        assert storage.get("total") == 30.0  # 10.0 * 3

    def test_for_body_내부에서_print가_실행된다(self, storage, capsys):
        """for body 안에서 PrintStmt 가 executor.execute() 를 통해 정상 실행된다."""
        body = [PrintStmt(VariableExpr(tok(TokenType.IDENTIFIER, "i")))]
        execute_for(make_for("i", 0.0, 3.0, body), storage)
        assert capsys.readouterr().out == "0\n1\n2\n"
