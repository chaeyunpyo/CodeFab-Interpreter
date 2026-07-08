from checker import CheckerUnit
from nodes.expr import LiteralExpr
from nodes.stmt import BlockStmt, ForStmt, IfStmt, ReturnStmt
from nodes.tokens import Token
from nodes.token_type import TokenType

from checker_helpers import make_function, make_param, make_var_decl

# function 오류 검사 (요구사항_정리/function.md)


def test_check_allows_function_with_no_duplicate_params():
    # Func foo(a, b) { }
    fn = make_function(params=[make_param("a"), make_param("b")])
    checker = CheckerUnit([fn])

    assert checker.check() == []


def test_check_detects_duplicate_parameter_names():
    # Func foo(a, a) { }
    fn = make_function(params=[make_param("a"), make_param("a")])
    checker = CheckerUnit([fn])

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Already a variable with this name in this scope."


def test_check_detects_duplicate_parameter_names_among_three():
    # Func foo(a, b, a) { }
    fn = make_function(params=[make_param("a"), make_param("b"), make_param("a")])
    checker = CheckerUnit([fn])

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Already a variable with this name in this scope."


def test_check_allows_return_inside_function():
    # Func foo() { return 5; }
    fn = make_function(body=[ReturnStmt(keyword=Token(TokenType.RETURN, "return"), value=LiteralExpr(5))])
    checker = CheckerUnit([fn])

    assert checker.check() == []


def test_check_allows_return_with_no_value_inside_function():
    # Func foo() { return; }
    fn = make_function(body=[ReturnStmt(keyword=Token(TokenType.RETURN, "return"), value=None)])
    checker = CheckerUnit([fn])

    assert checker.check() == []


def test_check_allows_return_inside_nested_block_of_function():
    # Func foo() { { return 5; } }
    fn = make_function(
        body=[BlockStmt(statements=[ReturnStmt(keyword=Token(TokenType.RETURN, "return"), value=LiteralExpr(5))])]
    )
    checker = CheckerUnit([fn])

    assert checker.check() == []


def test_check_detects_return_outside_function_at_top_level():
    # return 5;
    statements = [ReturnStmt(keyword=Token(TokenType.RETURN, "return"), value=LiteralExpr(5))]
    checker = CheckerUnit(statements)

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Can't return from top-level code."


def test_check_detects_return_outside_function_inside_plain_block():
    # { return 5; }  (함수가 아닌 블록 안)
    statements = [
        BlockStmt(statements=[ReturnStmt(keyword=Token(TokenType.RETURN, "return"), value=LiteralExpr(5))]),
    ]
    checker = CheckerUnit(statements)

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Can't return from top-level code."


# function 오류 검사 - md에 없는 추가 예외 케이스


def test_check_detects_duplicate_parameter_names_all_three_same():
    # Func foo(a, a, a) { }  -- 같은 이름이 3번 겹치면 오류도 2개(둘째, 셋째)여야 한다.
    fn = make_function(params=[make_param("a"), make_param("a"), make_param("a")])
    checker = CheckerUnit([fn])

    errors = checker.check()

    assert len(errors) == 2
    assert all(e.message == "Already a variable with this name in this scope." for e in errors)


def test_check_detects_duplicate_between_parameter_and_body_variable():
    # Func foo(a) { var a = 1; }
    # 파라미터도 함수 스코프의 선언이므로, 본문에서 같은 이름을 var로 또
    # 선언하면 파라미터 중복 선언과 같은 규칙으로 충돌해야 한다.
    fn = make_function(
        params=[make_param("a")],
        body=[make_var_decl("a", LiteralExpr(1))],
    )
    checker = CheckerUnit([fn])

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Already a variable with this name in this scope."


def test_check_allows_parameter_name_matching_outer_variable():
    # var a = 1; Func foo(a) { }
    # 파라미터는 함수 자신만의 새 스코프이므로, 바깥 변수와 이름이 같아도
    # (섀도잉) 충돌이 아니다.
    statements = [
        make_var_decl("a", LiteralExpr(1)),
        make_function(params=[make_param("a")]),
    ]
    checker = CheckerUnit(statements)

    assert checker.check() == []


def test_check_allows_nested_function_param_shadowing_outer_function_param():
    # Func outer(a) { Func inner(a) { } }
    # 서로 다른 함수의 파라미터 스코프이므로 이름이 같아도 충돌이 아니다.
    inner = make_function(name="inner", params=[make_param("a")])
    outer = make_function(name="outer", params=[make_param("a")], body=[inner])
    checker = CheckerUnit([outer])

    assert checker.check() == []


def test_check_allows_return_inside_nested_function():
    # Func outer() { Func inner() { return 5; } }
    # return이 가장 안쪽 함수(inner) 기준으로 판단되어야 정상 처리된다.
    inner = make_function(
        name="inner",
        body=[ReturnStmt(keyword=Token(TokenType.RETURN, "return"), value=LiteralExpr(5))],
    )
    outer = make_function(name="outer", body=[inner])
    checker = CheckerUnit([outer])

    assert checker.check() == []


def test_check_does_not_leak_function_context_to_sibling_statement():
    # Func foo() { return 5; } return 5;
    # 첫 번째 return은 foo 안이라 정상이고, foo 검사가 끝난 뒤에도
    # "함수 안"이라는 상태가 남아 두 번째(바깥) return까지 통과시키면 안 된다.
    fn = make_function(body=[ReturnStmt(keyword=Token(TokenType.RETURN, "return"), value=LiteralExpr(5))])
    statements = [fn, ReturnStmt(keyword=Token(TokenType.RETURN, "return"), value=LiteralExpr(5))]
    checker = CheckerUnit(statements)

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Can't return from top-level code."


def test_check_detects_return_as_bare_if_branch_at_top_level():
    # if (true) return 5;  (함수 밖, then_branch가 블록 없이 바로 return)
    statements = [
        IfStmt(
            condition=LiteralExpr(True),
            then_branch=ReturnStmt(keyword=Token(TokenType.RETURN, "return"), value=LiteralExpr(5)),
        ),
    ]
    checker = CheckerUnit(statements)

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Can't return from top-level code."


def test_check_detects_return_as_bare_for_body_at_top_level():
    # for (;;) return 5;  (함수 밖, body가 블록 없이 바로 return)
    statements = [
        ForStmt(
            initializer=None,
            condition=None,
            increment=None,
            body=ReturnStmt(keyword=Token(TokenType.RETURN, "return"), value=LiteralExpr(5)),
        ),
    ]
    checker = CheckerUnit(statements)

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Can't return from top-level code."
