from checker import CheckerUnit
from nodes.expr import AssignExpr, BinaryExpr, LiteralExpr, SuperExpr, ThisExpr, VariableExpr
from nodes.stmt import (
    BlockStmt,
    ClassStmt,
    ExpressionStmt,
    ForStmt,
    FunctionStmt,
    IfStmt,
    PrintStmt,
    ReturnStmt,
    VarDeclStmt,
)
from nodes.tokens import Token
from nodes.token_type import TokenType


def make_var_decl(name: str = "a", initializer=None) -> VarDeclStmt:
    return VarDeclStmt(name=Token(TokenType.IDENTIFIER, name), initializer=initializer)


def make_function(name="foo", params=None, body=None):
    return FunctionStmt(
        name=Token(TokenType.IDENTIFIER, name),
        params=params if params is not None else [],
        body=body if body is not None else [],
    )


def make_param(name):
    return Token(TokenType.IDENTIFIER, name)


def make_class(name="Robot", superclass=None, methods=None):
    return ClassStmt(
        name=Token(TokenType.IDENTIFIER, name),
        superclass=superclass,
        methods=methods if methods is not None else [],
    )


def make_this():
    return ThisExpr(keyword=Token(TokenType.THIS, "this"))


def make_super(method="move"):
    return SuperExpr(keyword=Token(TokenType.SUPER, "super"), method=Token(TokenType.IDENTIFIER, method))


def test_stores_empty_statements():
    checker = CheckerUnit([])

    assert checker.statements == []


def test_stores_given_statements_as_is():
    statements = [make_var_decl("a"), make_var_decl("b")]

    checker = CheckerUnit(statements)

    assert checker.statements == statements
    assert len(checker.statements) == 2


def test_accepts_mixed_statement_types():
    statements = [
        make_var_decl("a"),
        ExpressionStmt(expression=None),
    ]

    checker = CheckerUnit(statements)

    assert isinstance(checker.statements[0], VarDeclStmt)
    assert isinstance(checker.statements[1], ExpressionStmt)


def test_check_returns_no_errors_when_empty():
    checker = CheckerUnit([])

    assert checker.check() == []


def test_check_returns_no_errors_for_single_declaration():
    checker = CheckerUnit([make_var_decl("a")])

    assert checker.check() == []


def test_check_detects_duplicate_declaration_in_same_block():
    statements = [make_var_decl("a"), make_var_decl("a")]
    checker = CheckerUnit(statements)

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Already a variable with this name in this scope."


def test_check_error_str_includes_line_number():
    first = VarDeclStmt(name=Token(TokenType.IDENTIFIER, "a", line=3), initializer=None)
    second = VarDeclStmt(name=Token(TokenType.IDENTIFIER, "a", line=5), initializer=None)
    checker = CheckerUnit([first, second])

    errors = checker.check()

    assert str(errors[0]) == "[Checker] Line 5: Already a variable with this name in this scope."


# 변수 중복 선언 검사

def test_check_allows_same_name_in_nested_block():
    statements = [
        make_var_decl("a"),
        BlockStmt(statements=[make_var_decl("a")]),
    ]
    checker = CheckerUnit(statements)

    assert checker.check() == []


def test_check_detects_duplicate_declaration_inside_nested_block():
    # { var a = "hi"; var a = 3; }
    statements = [
        BlockStmt(
            statements=[
                make_var_decl("a", LiteralExpr("hi")),
                make_var_decl("a", LiteralExpr(3)),
            ]
        ),
    ]
    checker = CheckerUnit(statements)

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Already a variable with this name in this scope."


# 자기 참조 검사
def test_check_detects_self_reference_in_initializer():
    # { var a = a; }
    statements = [
        BlockStmt(
            statements=[
                make_var_decl("a", VariableExpr(Token(TokenType.IDENTIFIER, "a"))),
            ]
        ),
    ]
    checker = CheckerUnit(statements)

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Can't read local variable in initializer."


def test_check_detects_self_reference_even_when_outer_scope_has_same_name():
    # var a = 1; { var a = a; } -- the local `a` shadows the outer one, so the
    # initializer still reads the not-yet-initialized local `a`.
    statements = [
        make_var_decl("a", LiteralExpr(1)),
        BlockStmt(
            statements=[
                make_var_decl("a", VariableExpr(Token(TokenType.IDENTIFIER, "a"))),
            ]
        ),
    ]
    checker = CheckerUnit(statements)

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Can't read local variable in initializer."

def test_check_does_not_crash_when_initializer_is_not_an_expr_node():
    # Expr이 아닌 초기화식이 와도 죽지 않아야 한다.
    broken_initializer = "a"
    checker = CheckerUnit([make_var_decl("a", broken_initializer)])

    assert checker.check() == []


def test_check_does_not_crash_when_var_decl_name_token_is_missing():
    # name 토큰이 없어도(None) 죽지 않아야 한다.
    broken_statement = VarDeclStmt(name=None, initializer=None)
    checker = CheckerUnit([broken_statement])

    assert checker.check() == []


def test_check_does_not_crash_on_self_referencing_block():
    # 블록이 자기 자신을 포함하는 순환 참조에도 죽지 않아야 한다.
    cyclic_block = BlockStmt(statements=[])
    cyclic_block.statements.append(cyclic_block)
    checker = CheckerUnit([cyclic_block])

    errors = checker.check()

    assert isinstance(errors, list)


# for 문 검사
def test_check_for_loop_with_no_issues_has_no_errors():
    # for (var i = 0; i < 10; i = i + 1) { print i; }
    i_token = Token(TokenType.IDENTIFIER, "i")
    statements = [
        ForStmt(
            initializer=VarDeclStmt(name=i_token, initializer=LiteralExpr(0)),
            condition=BinaryExpr(
                left=VariableExpr(i_token),
                operator=Token(TokenType.LESS, "<"),
                right=LiteralExpr(10),
            ),
            increment=AssignExpr(
                name=i_token,
                value=BinaryExpr(
                    left=VariableExpr(i_token),
                    operator=Token(TokenType.PLUS, "+"),
                    right=LiteralExpr(1),
                ),
            ),
            body=BlockStmt(statements=[PrintStmt(expression=VariableExpr(i_token))]),
        ),
    ]
    checker = CheckerUnit(statements)

    assert checker.check() == []


def test_check_detects_duplicate_declaration_between_outer_var_and_for_initializer():
    # var i = 0; for (var i = 1; ; ) {}
    # for의 initializer는 새 스코프를 열지 않으므로 바깥의 i와 충돌한다.
    statements = [
        make_var_decl("i", LiteralExpr(0)),
        ForStmt(
            initializer=make_var_decl("i", LiteralExpr(1)),
            condition=None,
            increment=None,
            body=BlockStmt(statements=[]),
        ),
    ]
    checker = CheckerUnit(statements)

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Already a variable with this name in this scope."


def test_check_detects_duplicate_declaration_between_for_initializer_and_bare_body_statement():
    # for (var i = 0; ; ) var i = 1;
    # body가 BlockStmt로 감싸여 있지 않으면 새 스코프가 열리지 않으므로,
    # initializer와 body가 같은 스코프를 공유해서 충돌한다.
    statements = [
        ForStmt(
            initializer=make_var_decl("i", LiteralExpr(0)),
            condition=None,
            increment=None,
            body=make_var_decl("i", LiteralExpr(1)),
        ),
    ]
    checker = CheckerUnit(statements)

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Already a variable with this name in this scope."


def test_check_allows_same_name_when_if_then_and_else_are_blocks():
    # if (true) { var a = 1; } else { var a = 2; }
    # then/else가 BlockStmt로 감싸여 있으면 각자 새 스코프를 열므로 충돌하지 않는다.
    statements = [
        IfStmt(
            condition=LiteralExpr(True),
            then_branch=BlockStmt(statements=[make_var_decl("a", LiteralExpr(1))]),
            else_branch=BlockStmt(statements=[make_var_decl("a", LiteralExpr(2))]),
        ),
    ]
    checker = CheckerUnit(statements)

    assert checker.check() == []


def test_check_detects_duplicate_declaration_when_if_then_and_else_are_bare_statements():
    # if (true) var a = 1; else var a = 2;
    # then/else가 BlockStmt로 감싸여 있지 않으면 새 스코프가 열리지 않으므로,
    # 바깥(if 자신)과 같은 스코프를 공유해서 충돌한다.
    statements = [
        IfStmt(
            condition=LiteralExpr(True),
            then_branch=make_var_decl("a", LiteralExpr(1)),
            else_branch=make_var_decl("a", LiteralExpr(2)),
        ),
    ]
    checker = CheckerUnit(statements)

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Already a variable with this name in this scope."


# function 오류 검사 (요구사항_정리/function.md)
# 아직 checker.py에 FunctionStmt/ReturnStmt 핸들러가 없어서 지금은 전부
# RED(실패) 상태다. 구현하면 통과하도록 먼저 테스트만 작성해둔다.


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


# class 오류 검사 (요구사항_정리/class.md)
# 아직 checker.py에 ClassStmt/ThisExpr/SuperExpr 핸들러가 없어서 지금은
# 전부 RED(실패) 상태다. 구현하면 통과하도록 먼저 테스트만 작성해둔다.


def test_check_detects_this_used_outside_class():
    # print this;  (클래스 밖)
    statements = [PrintStmt(expression=make_this())]
    checker = CheckerUnit(statements)

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Can't use 'this' outside of a class."


def test_check_detects_this_used_inside_plain_function():
    # Func foo() { print this; }  (클래스가 아니라 일반 함수 안)
    fn = make_function(body=[PrintStmt(expression=make_this())])
    checker = CheckerUnit([fn])

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Can't use 'this' outside of a class."


def test_check_allows_this_used_inside_method():
    # Class Robot { report() { print this; } }
    method = make_function(name="report", body=[PrintStmt(expression=make_this())])
    cls = make_class(methods=[method])
    checker = CheckerUnit([cls])

    assert checker.check() == []


def test_check_detects_super_used_outside_class():
    # super.move();  (클래스 밖)
    statements = [ExpressionStmt(expression=make_super())]
    checker = CheckerUnit(statements)

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Can't use 'super' outside of a class."


def test_check_detects_super_used_in_class_without_superclass():
    # Class Robot { move() { super.move(); } }  (상속하지 않은 클래스)
    method = make_function(name="move", body=[ExpressionStmt(expression=make_super())])
    cls = make_class(superclass=None, methods=[method])
    checker = CheckerUnit([cls])

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Can't use 'super' in a class with no superclass."


def test_check_allows_super_used_in_class_with_superclass():
    # Class SpeedRobot : Robot { move() { super.move(); } }
    method = make_function(name="move", body=[ExpressionStmt(expression=make_super())])
    cls = make_class(
        name="SpeedRobot",
        superclass=VariableExpr(Token(TokenType.IDENTIFIER, "Robot")),
        methods=[method],
    )
    checker = CheckerUnit([cls])

    assert checker.check() == []


def test_check_detects_self_inheritance():
    # Class Robot : Robot { }
    cls = make_class(name="Robot", superclass=VariableExpr(Token(TokenType.IDENTIFIER, "Robot")))
    checker = CheckerUnit([cls])

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "A class can't inherit from itself."


def test_check_allows_inheriting_a_different_class():
    # Class SpeedRobot : Robot { }
    cls = make_class(name="SpeedRobot", superclass=VariableExpr(Token(TokenType.IDENTIFIER, "Robot")))
    checker = CheckerUnit([cls])

    assert checker.check() == []


def test_check_detects_return_value_in_init():
    # Class Robot { init() { return 5; } }
    init_method = make_function(
        name="init",
        body=[ReturnStmt(keyword=Token(TokenType.RETURN, "return"), value=LiteralExpr(5))],
    )
    cls = make_class(methods=[init_method])
    checker = CheckerUnit([cls])

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Can't return a value from an initializer."


def test_check_allows_bare_return_in_init():
    # Class Robot { init() { return; } }  (값 없는 조기 return은 허용)
    init_method = make_function(
        name="init",
        body=[ReturnStmt(keyword=Token(TokenType.RETURN, "return"), value=None)],
    )
    cls = make_class(methods=[init_method])
    checker = CheckerUnit([cls])

    assert checker.check() == []


def test_check_allows_return_value_in_regular_method():
    # Class Robot { move() { return 5; } }  (init이 아니면 값 반환 허용)
    method = make_function(
        name="move",
        body=[ReturnStmt(keyword=Token(TokenType.RETURN, "return"), value=LiteralExpr(5))],
    )
    cls = make_class(methods=[method])
    checker = CheckerUnit([cls])

    assert checker.check() == []


# class 오류 검사 - md에 없는 추가 예외 케이스 (구현이 실제로 맞게 동작하는지 검증)


def test_check_allows_this_inside_nested_block_of_method():
    # Class Robot { move() { { print this; } } }
    method = make_function(name="move", body=[BlockStmt(statements=[PrintStmt(expression=make_this())])])
    cls = make_class(methods=[method])
    checker = CheckerUnit([cls])

    assert checker.check() == []


def test_check_detects_this_used_inside_nested_block_outside_class():
    # { { print this; } }  (클래스 밖, 블록이 여러 겹 중첩되어 있어도 잡혀야 한다)
    statements = [BlockStmt(statements=[BlockStmt(statements=[PrintStmt(expression=make_this())])])]
    checker = CheckerUnit(statements)

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Can't use 'this' outside of a class."


def test_check_detects_this_used_inside_binary_expression_outside_class():
    # print this == null;  (this가 표현식 맨 앞이 아니라 안쪽 깊숙히 있어도 잡혀야 한다)
    expr = BinaryExpr(left=make_this(), operator=Token(TokenType.EQUAL_EQUAL, "=="), right=LiteralExpr(None))
    statements = [PrintStmt(expression=expr)]
    checker = CheckerUnit(statements)

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Can't use 'this' outside of a class."


def test_check_allows_super_init_call_when_class_has_superclass():
    # Class SpeedRobot : Robot { init(name) { super.init(name); } }
    # PDF 예시(class.md)의 실제 상속+생성자+super 조합을 그대로 재현한다.
    init_method = make_function(
        name="init",
        params=[make_param("name")],
        body=[ExpressionStmt(expression=make_super(method="init"))],
    )
    cls = make_class(
        name="SpeedRobot",
        superclass=VariableExpr(Token(TokenType.IDENTIFIER, "Robot")),
        methods=[init_method],
    )
    checker = CheckerUnit([cls])

    assert checker.check() == []


def test_check_does_not_leak_init_flag_between_sibling_methods():
    # Class Robot { init() { return; } move() { return 5; } }
    # init을 먼저 검사한 뒤에도 "init 안"이라는 상태가 남아서 다음 메서드의
    # 정상적인 값 반환까지 오류로 잘못 잡으면 안 된다.
    init_method = make_function(
        name="init",
        body=[ReturnStmt(keyword=Token(TokenType.RETURN, "return"), value=None)],
    )
    move_method = make_function(
        name="move",
        body=[ReturnStmt(keyword=Token(TokenType.RETURN, "return"), value=LiteralExpr(5))],
    )
    cls = make_class(methods=[init_method, move_method])
    checker = CheckerUnit([cls])

    assert checker.check() == []


def test_check_allows_this_inside_function_nested_in_method():
    # Class Robot { move() { Func helper() { print this; } } }
    # 메서드 안에 있는 일반 함수(클로저)에서도 this는 여전히 유효해야 한다.
    helper = make_function(name="helper", body=[PrintStmt(expression=make_this())])
    method = make_function(name="move", body=[helper])
    cls = make_class(methods=[method])
    checker = CheckerUnit([cls])

    assert checker.check() == []


def test_check_allows_return_value_in_function_nested_inside_init():
    # Class Robot { init() { Func helper() { return 5; } } }
    # helper는 init 자신이 아니라 init 안에 있는 별개의 함수이므로,
    # helper의 값 반환은 "생성자에서 값 반환" 오류가 아니어야 한다.
    helper = make_function(
        name="helper",
        body=[ReturnStmt(keyword=Token(TokenType.RETURN, "return"), value=LiteralExpr(5))],
    )
    init_method = make_function(name="init", body=[helper])
    cls = make_class(methods=[init_method])
    checker = CheckerUnit([cls])

    assert checker.check() == []


def test_check_does_not_crash_when_superclass_is_not_a_variable_expr():
    # Class Robot : 10 { }  (부모 자리에 클래스 이름이 아닌 값이 와도 죽지 않아야 한다)
    # "클래스가 아닌 대상 상속"은 런타임 오류라 Checker가 여기서 정적으로
    # 자기 상속 오류를 잘못 내지도, 죽지도 않아야 한다.
    cls = make_class(name="Robot", superclass=LiteralExpr(10))
    checker = CheckerUnit([cls])

    assert checker.check() == []
