import pytest

from executor import DivideByZeroError, TypeMismatchError, UndefinedVariableError, evaluate, stringify
from nodes.expr import (
    AssignExpr,
    BinaryExpr,
    Expr,
    GroupingExpr,
    LiteralExpr,
    LogicalExpr,
    UnaryExpr,
    VariableExpr,
)
from nodes.token_type import TokenType

from helpers import tok


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

    def test_양수_부호는_숫자를_그대로_반환한다(self, storage):
        expr = UnaryExpr(tok(TokenType.PLUS, "+"), LiteralExpr(5.0))
        assert evaluate(expr, storage) == 5.0

    def test_숫자가_아닌_값에_양수_부호를_쓰면_타입_오류가_발생한다(self, storage):
        expr = UnaryExpr(tok(TokenType.PLUS, "+"), LiteralExpr("hi"))
        with pytest.raises(TypeMismatchError):
            evaluate(expr, storage)

    def test_지원하지_않는_단항_연산자는_타입_오류를_발생시킨다(self, storage):
        expr = UnaryExpr(tok(TokenType.SLASH, "/"), LiteralExpr(5.0))
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
            (TokenType.PERCENT, "%", 10.0, 3.0, 1.0),
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

    def test_0으로_나머지를_구하면_예외를_발생시킨다(self, storage):
        expr = BinaryExpr(LiteralExpr(3.0), tok(TokenType.PERCENT, "%"), LiteralExpr(0.0))
        with pytest.raises(DivideByZeroError):
            evaluate(expr, storage)

    def test_나머지_연산에_문자열_피연산자를_쓰면_타입_오류가_발생한다(self, storage):
        expr = BinaryExpr(LiteralExpr("hi"), tok(TokenType.PERCENT, "%"), LiteralExpr(2.0))
        with pytest.raises(TypeMismatchError):
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

    def test_문자열끼리_더하면_이어붙인다(self, storage):
        # print "Hello, " + "CodeFab!"; // expect: Hello, CodeFab!
        expr = BinaryExpr(LiteralExpr("Hello, "), tok(TokenType.PLUS, "+"), LiteralExpr("CodeFab!"))
        assert evaluate(expr, storage) == "Hello, CodeFab!"

    def test_문자열과_숫자를_더하면_타입_오류가_발생한다(self, storage):
        expr = BinaryExpr(LiteralExpr("hello"), tok(TokenType.PLUS, "+"), LiteralExpr(3.0))
        with pytest.raises(TypeMismatchError):
            evaluate(expr, storage)

    def test_지원하지_않는_이항_연산자는_타입_오류를_발생시킨다(self, storage):
        expr = BinaryExpr(LiteralExpr(1.0), tok(TokenType.AND, "and"), LiteralExpr(2.0))
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

    def test_문자열_같은_비교는_TypeMismatchError_없이_참을_반환한다(self, storage):
        # ==/!=는 숫자 전용이 아니라 어떤 타입이든 비교 가능해야 한다.
        expr = BinaryExpr(LiteralExpr("hi"), tok(TokenType.EQUAL_EQUAL, "=="), LiteralExpr("hi"))
        assert evaluate(expr, storage) is True

    def test_문자열_같은_비교가_거짓인_경우(self, storage):
        expr = BinaryExpr(LiteralExpr("hi"), tok(TokenType.EQUAL_EQUAL, "=="), LiteralExpr("bye"))
        assert evaluate(expr, storage) is False

    def test_불리언_같은_비교는_TypeMismatchError_없이_동작한다(self, storage):
        expr = BinaryExpr(LiteralExpr(True), tok(TokenType.EQUAL_EQUAL, "=="), LiteralExpr(True))
        assert evaluate(expr, storage) is True

    def test_문자열_같지_않은_비교가_참인_경우(self, storage):
        expr = BinaryExpr(LiteralExpr("hi"), tok(TokenType.BANG_EQUAL, "!="), LiteralExpr("bye"))
        assert evaluate(expr, storage) is True

    def test_타입이_다르면_같은_비교는_오류_없이_거짓을_반환한다(self, storage):
        expr = BinaryExpr(LiteralExpr(1.0), tok(TokenType.EQUAL_EQUAL, "=="), LiteralExpr("1"))
        assert evaluate(expr, storage) is False


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


class TestEvaluateUnknownNode:
    def test_등록되지_않은_노드_타입을_평가하면_NotImplementedError가_발생한다(self, storage):
        class UnregisteredExpr(Expr):
            pass

        with pytest.raises(NotImplementedError):
            evaluate(UnregisteredExpr(), storage)


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
