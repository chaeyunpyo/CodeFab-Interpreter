"""실행전 최적화 (요구사항_정리/실행전_최적화.md) - 정적 바인딩 + 상수 연산 최적화.

src/checker/_checker_unit.py에 구현되어 있다. 아래는 그 설계 계약이다.

## 정적 바인딩(변수 거리 계산) 계약
- `CheckerUnit.check()`를 호출하면 `checker.locals` 딕셔너리가 채워진다.
  `id(VariableExpr 또는 AssignExpr 노드) -> distance(int)` 형태다.
- distance는 "가장 안쪽 지역 스코프"를 0으로 두고, 선언을 찾을 때까지
  거슬러 올라간 지역 스코프(블록/함수 파라미터 스코프) 개수다.
- 최상위(전역) 스코프에서 선언되고 참조되는 변수는 `checker.locals`에
  항목이 없다 (전역은 이름으로 직접 조회하기 때문).
- 함수 안에서 함수 "바깥"을 참조하는 경우도 `checker.locals`에 항목이
  없다. Storage.push_call_frame()이 호출마다 전역 스코프만 남기고 지역
  스코프 체인은 초기화하므로(클로저 없음, `src/executor/_function.py`
  참고), 함수 내부에서는 자기 자신의 파라미터/블록 스코프만 지역으로
  취급한다.

## 상수 연산 최적화 계약
- `CheckerUnit.check()`를 호출하면, 값이 100% 확정되는 리터럴끼리의
  연산(Binary/Unary/Grouping)을 AST에서 직접 `LiteralExpr`로 치환한다
  (원본 노드의 필드를 in-place로 바꾼다).
- 변수가 하나라도 섞여 있으면 접기 대상이 아니다.
- 접었을 때 런타임 오류가 나는 조합(예: 0으로 나누기)은 접지 않고 원본
  그대로 둔다 (Executor의 오류 발생 경로를 그대로 보존).
"""

from checker import CheckerUnit
from checker._constant_folder import _NOT_FOLDABLE, ConstantFolder, _fold_unary_value
from nodes.expr import AssignExpr, BinaryExpr, GroupingExpr, LiteralExpr, UnaryExpr, VariableExpr
from nodes.stmt import BlockStmt, ExpressionStmt, ForStmt, PrintStmt
from nodes.tokens import Token
from nodes.token_type import TokenType

from checker_helpers import make_function, make_param, make_var_decl


def make_var(name):
    return VariableExpr(Token(TokenType.IDENTIFIER, name))


def make_assign(name, value):
    return AssignExpr(name=Token(TokenType.IDENTIFIER, name), value=value)


def make_binary(left, op_type, op_lexeme, right):
    return BinaryExpr(left=left, operator=Token(op_type, op_lexeme), right=right)


def make_print(expr):
    return PrintStmt(expression=expr)


def make_block(*statements):
    return BlockStmt(statements=list(statements))


def assert_folds_to(expr, expected_value):
    """expr을 var x = expr;의 초기화식으로 두고 check() 후 리터럴로 접혔는지 확인한다."""
    stmt = make_var_decl("x", expr)
    CheckerUnit([stmt]).check()

    assert isinstance(stmt.initializer, LiteralExpr)
    assert stmt.initializer.value == expected_value


def assert_not_folded(expr):
    """expr을 var x = expr;의 초기화식으로 두고 check() 후에도 원본 그대로인지 확인한다."""
    stmt = make_var_decl("x", expr)
    CheckerUnit([stmt]).check()

    assert stmt.initializer is expr


# ── 정적 바인딩(변수 거리 계산) ──────────────────────────────────────────


def test_resolve_binds_distance_zero_for_variable_declared_and_used_at_top_level():
    # var a = 1; print a;  -- 전역도 scope_stack의 맨 아래라 거리 0.
    var_expr = make_var("a")
    statements = [make_var_decl("a", LiteralExpr(1)), make_print(var_expr)]
    checker = CheckerUnit(statements)

    errors = checker.check()

    assert errors == []
    assert checker.locals[id(var_expr)] == 0


def test_resolve_binds_distance_zero_when_used_in_same_block_as_declaration():
    # { var a = 1; print a; }  -- 선언과 같은 블록에서 쓰면 거리 0.
    var_expr = make_var("a")
    statements = [make_block(make_var_decl("a", LiteralExpr(1)), make_print(var_expr))]
    checker = CheckerUnit(statements)

    checker.check()

    assert checker.locals[id(var_expr)] == 0


def test_resolve_binds_distance_one_for_variable_from_one_block_up():
    # { var a = 1; { print a; } }  -- 한 블록 위 선언이라 거리 1.
    var_expr = make_var("a")
    statements = [make_block(make_var_decl("a", LiteralExpr(1)), make_block(make_print(var_expr)))]
    checker = CheckerUnit(statements)

    checker.check()

    assert checker.locals[id(var_expr)] == 1


def test_resolve_binds_distance_two_for_variable_from_two_blocks_up():
    # { var a = 1; { { print a; } } }  -- 두 블록 위 선언이라 거리 2.
    var_expr = make_var("a")
    statements = [make_block(make_var_decl("a", LiteralExpr(1)), make_block(make_block(make_print(var_expr))))]
    checker = CheckerUnit(statements)

    checker.check()

    assert checker.locals[id(var_expr)] == 2


def test_resolve_uses_nearest_shadowing_declaration():
    # { var a = 1; { var a = 2; print a; } }  -- 안쪽 a를 써야 하므로 거리는 0.
    var_expr = make_var("a")
    statements = [
        make_block(
            make_var_decl("a", LiteralExpr(1)),
            make_block(make_var_decl("a", LiteralExpr(2)), make_print(var_expr)),
        )
    ]
    checker = CheckerUnit(statements)

    checker.check()

    assert checker.locals[id(var_expr)] == 0


def test_resolve_binds_assign_expr_the_same_way_as_variable_expr():
    # { var a = 1; { a = 2; } }  -- 대입식도 참조식과 동일하게 거리를 기록한다.
    assign_expr = make_assign("a", LiteralExpr(2))
    statements = [
        make_block(make_var_decl("a", LiteralExpr(1)), make_block(ExpressionStmt(expression=assign_expr))),
    ]
    checker = CheckerUnit(statements)

    checker.check()

    assert checker.locals[id(assign_expr)] == 1


def test_resolve_binds_distance_zero_for_function_parameter_used_in_body():
    # Func foo(a) { print a; }  -- 파라미터도 지역 변수라 거리 0.
    var_expr = make_var("a")
    fn = make_function(params=[make_param("a")], body=[make_print(var_expr)])
    checker = CheckerUnit([fn])

    checker.check()

    assert checker.locals[id(var_expr)] == 0


def test_resolve_binds_distance_one_for_function_parameter_from_nested_block():
    # Func foo(a) { { print a; } }  -- 파라미터 스코프보다 한 블록 안쪽이라 거리 1.
    var_expr = make_var("a")
    fn = make_function(params=[make_param("a")], body=[make_block(make_print(var_expr))])
    checker = CheckerUnit([fn])

    checker.check()

    assert checker.locals[id(var_expr)] == 1


def test_resolve_binds_global_variable_referenced_inside_function():
    # var g = 1; Func foo() { print g; }  -- 함수 안에서도 전역은 거리 계산 대상이다
    # (Storage.push_call_frame이 전역은 복사해서 유지하므로 거리 1이면 된다).
    var_expr = make_var("g")
    fn = make_function(body=[make_print(var_expr)])
    statements = [make_var_decl("g", LiteralExpr(1)), fn]
    checker = CheckerUnit(statements)

    checker.check()

    assert checker.locals[id(var_expr)] == 1


def test_resolve_does_not_leak_binding_between_sibling_blocks():
    # { var a = 1; } { print a; }  -- 서로 다른 블록이라 두 번째 a는 지역 바인딩이 없다.
    var_expr = make_var("a")
    statements = [make_block(make_var_decl("a", LiteralExpr(1))), make_block(make_print(var_expr))]
    checker = CheckerUnit(statements)

    checker.check()

    assert id(var_expr) not in checker.locals


def test_resolve_binds_global_variable_deeply_nested_inside_blocks():
    # 실행전_최적화.md의 예시: var a = 0; { {13겹} for (...) { a = a + 1; } }
    # a는 전역이지만 13겹 블록 + for문 본문 블록까지 총 14단계 안쪽에서
    # 쓰이므로 거리는 14여야 한다 (Storage._scopes[-(14+1)] == 전역).
    assign_expr = make_assign("a", make_binary(make_var("a"), TokenType.PLUS, "+", LiteralExpr(1)))
    body = ExpressionStmt(expression=assign_expr)
    for _ in range(13):
        body = make_block(body)
    for_stmt = ForStmt(initializer=None, condition=None, increment=None, body=make_block(body))
    statements = [make_var_decl("a", LiteralExpr(0)), for_stmt]
    checker = CheckerUnit(statements)

    checker.check()

    assert checker.locals[id(assign_expr)] == 14


# ── 상수 연산 최적화 ────────────────────────────────────────────────────


def test_fold_replaces_constant_binary_addition_with_literal():
    # var x = 1 + 2;  -- 리터럴끼리의 사칙연산은 결과 리터럴로 접힌다.
    assert_folds_to(make_binary(LiteralExpr(1), TokenType.PLUS, "+", LiteralExpr(2)), 3)


def test_fold_replaces_constant_binary_subtraction_multiplication_division():
    # var x = (10 - 4) * 2 / 3;  -- 뺄셈/곱셈/나눗셈이 섞여도 하나의 리터럴로 접힌다.
    inner = make_binary(LiteralExpr(10), TokenType.MINUS, "-", LiteralExpr(4))
    mul = make_binary(inner, TokenType.STAR, "*", LiteralExpr(2))
    div = make_binary(mul, TokenType.SLASH, "/", LiteralExpr(3))

    assert_folds_to(div, 4.0)


def test_fold_recursively_folds_deeply_nested_constant_expression():
    # var x = ((1 + 2) + 3) + 4;  -- 여러 겹 중첩돼도 재귀적으로 접힌다.
    step1 = make_binary(LiteralExpr(1), TokenType.PLUS, "+", LiteralExpr(2))
    step2 = make_binary(step1, TokenType.PLUS, "+", LiteralExpr(3))
    step3 = make_binary(step2, TokenType.PLUS, "+", LiteralExpr(4))

    assert_folds_to(step3, 10)


def test_fold_unwraps_grouping_of_constant_expression():
    # var x = (1 + 2);  -- 괄호로 감싸도 안쪽이 상수면 리터럴로 접힌다.
    binary = make_binary(LiteralExpr(1), TokenType.PLUS, "+", LiteralExpr(2))

    assert_folds_to(GroupingExpr(expression=binary), 3)


def test_fold_replaces_constant_unary_negation_with_literal():
    # var x = -5;  -- 리터럴에 대한 단항 음수도 접힌다.
    unary = UnaryExpr(operator=Token(TokenType.MINUS, "-"), right=LiteralExpr(5))

    assert_folds_to(unary, -5)


def test_fold_replaces_constant_comparison_with_boolean_literal():
    # var x = 1 < 2;  -- 비교 연산도 리터럴끼리면 boolean 리터럴로 접힌다.
    binary = make_binary(LiteralExpr(1), TokenType.LESS, "<", LiteralExpr(2))

    assert_folds_to(binary, True)


def test_fold_does_not_touch_expression_mixed_with_variable():
    # var x = a + 1;  -- 변수가 섞이면 접기 대상이 아니다.
    assert_not_folded(make_binary(make_var("a"), TokenType.PLUS, "+", LiteralExpr(1)))


def test_fold_does_not_fold_literal_division_by_zero():
    # var x = 3 / 0;  -- 런타임 오류 경로를 보존해야 하므로 접지 않는다.
    assert_not_folded(make_binary(LiteralExpr(3), TokenType.SLASH, "/", LiteralExpr(0)))


def test_fold_replaces_constant_string_equality_with_boolean_literal():
    # var x = "hi" == "hi";  -- ==/!=는 숫자 전용이 아니라 문자열도 접혀야 한다.
    binary = make_binary(LiteralExpr("hi"), TokenType.EQUAL_EQUAL, "==", LiteralExpr("hi"))

    assert_folds_to(binary, True)


def test_fold_replaces_constant_modulo_with_literal():
    # var x = 10 % 3;  -- 나머지 연산도 리터럴끼리면 결과 리터럴로 접힌다.
    assert_folds_to(make_binary(LiteralExpr(10), TokenType.PERCENT, "%", LiteralExpr(3)), 1)


def test_fold_does_not_fold_literal_modulo_by_zero():
    # var x = 3 % 0;  -- 런타임 오류 경로를 보존해야 하므로 접지 않는다.
    assert_not_folded(make_binary(LiteralExpr(3), TokenType.PERCENT, "%", LiteralExpr(0)))


def test_fold_applies_inside_for_loop_body():
    # for (;;) { var x = 1 + 2; }  -- 최적화는 반복문 본문 안쪽에도 똑같이 적용된다.
    binary = make_binary(LiteralExpr(1), TokenType.PLUS, "+", LiteralExpr(2))
    inner_decl = make_var_decl("x", binary)
    statements = [ForStmt(initializer=None, condition=None, increment=None, body=make_block(inner_decl))]
    checker = CheckerUnit(statements)

    checker.check()

    assert isinstance(inner_decl.initializer, LiteralExpr)
    assert inner_decl.initializer.value == 3


def test_fold_applies_inside_function_body():
    # Func foo() { var x = 1 + 2; }  -- 최적화는 함수 본문 안쪽에도 똑같이 적용된다.
    binary = make_binary(LiteralExpr(1), TokenType.PLUS, "+", LiteralExpr(2))
    inner_decl = make_var_decl("x", binary)
    fn = make_function(body=[inner_decl])
    checker = CheckerUnit([fn])

    checker.check()

    assert isinstance(inner_decl.initializer, LiteralExpr)
    assert inner_decl.initializer.value == 3


def test_fold_does_not_fold_unary_plus_on_non_number():
    # var x = +"hi";  -- 단항 +는 숫자가 아니면 접을 수 없어 원본 그대로 둔다.
    unary = UnaryExpr(operator=Token(TokenType.PLUS, "+"), right=LiteralExpr("hi"))

    assert_not_folded(unary)


def test_fold_value_returns_not_foldable_for_unsupported_unary_operator():
    """_fold_unary_value는 Executor의 _evaluate_unary와 같은 연산자 집합
    (MINUS/PLUS/BANG)만 지원한다. 파서는 이 세 개만 UnaryExpr로 만들어내지만,
    함수 자체는 방어적으로 그 외 연산자에 대해 접을 수 없다고 답해야 한다.
    """
    assert _fold_unary_value(Token(TokenType.SLASH, "/"), 5.0) is _NOT_FOLDABLE


def test_fold_returns_non_expr_value_unchanged():
    """ConstantFolder.fold()는 Expr이 아닌 값이 들어오면 그대로 돌려준다."""
    assert ConstantFolder().fold(42) == 42
    assert ConstantFolder().fold(None) is None
