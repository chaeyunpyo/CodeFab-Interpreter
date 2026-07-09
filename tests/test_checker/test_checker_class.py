from checker import CheckerUnit
from nodes.expr import BinaryExpr, LiteralExpr, VariableExpr
from nodes.stmt import BlockStmt, ExpressionStmt, PrintStmt, ReturnStmt
from nodes.tokens import Token
from nodes.token_type import TokenType

from checker_helpers import make_class, make_function, make_param, make_super, make_this

# class 오류 검사 (요구사항_정리/class.md)


def test_check_detects_this_used_outside_class():
    # print This;  (클래스 밖)
    statements = [PrintStmt(expression=make_this())]
    checker = CheckerUnit(statements)

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Can't use 'this' outside of a class."


def test_check_detects_this_used_inside_plain_function():
    # Func foo() { print This; }  (클래스가 아니라 일반 함수 안)
    fn = make_function(body=[PrintStmt(expression=make_this())])
    checker = CheckerUnit([fn])

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Can't use 'this' outside of a class."


def test_check_allows_this_used_inside_method():
    # Class Robot { report() { print This; } }
    method = make_function(name="report", body=[PrintStmt(expression=make_this())])
    cls = make_class(methods=[method])
    checker = CheckerUnit([cls])

    assert checker.check() == []


def test_check_detects_super_used_outside_class():
    # Super.move();  (클래스 밖)
    statements = [ExpressionStmt(expression=make_super())]
    checker = CheckerUnit(statements)

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Can't use 'super' outside of a class."


def test_check_detects_super_used_in_class_without_superclass():
    # Class Robot { move() { Super.move(); } }  (상속하지 않은 클래스)
    method = make_function(name="move", body=[ExpressionStmt(expression=make_super())])
    cls = make_class(superclass=None, methods=[method])
    checker = CheckerUnit([cls])

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Can't use 'super' in a class with no superclass."


def test_check_allows_super_used_in_class_with_superclass():
    # Class SpeedRobot : Robot { move() { Super.move(); } }
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
    # Class Robot { move() { { print This; } } }
    method = make_function(name="move", body=[BlockStmt(statements=[PrintStmt(expression=make_this())])])
    cls = make_class(methods=[method])
    checker = CheckerUnit([cls])

    assert checker.check() == []


def test_check_detects_this_used_inside_nested_block_outside_class():
    # { { print This; } }  (클래스 밖, 블록이 여러 겹 중첩되어 있어도 잡혀야 한다)
    statements = [BlockStmt(statements=[BlockStmt(statements=[PrintStmt(expression=make_this())])])]
    checker = CheckerUnit(statements)

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Can't use 'this' outside of a class."


def test_check_detects_this_used_inside_binary_expression_outside_class():
    # print This == null;  (This가 표현식 맨 앞이 아니라 안쪽 깊숙히 있어도 잡혀야 한다)
    expr = BinaryExpr(left=make_this(), operator=Token(TokenType.EQUAL_EQUAL, "=="), right=LiteralExpr(None))
    statements = [PrintStmt(expression=expr)]
    checker = CheckerUnit(statements)

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Can't use 'this' outside of a class."


def test_check_allows_super_init_call_when_class_has_superclass():
    # Class SpeedRobot : Robot { init(name) { Super.init(name); } }  -- 상속+생성자+Super 조합.
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
    # Class Robot { init() { return; } move() { return 5; } }  -- "init 안" 상태가 새면 안 된다.
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


def test_check_detects_this_inside_plain_function_nested_in_method():
    # Class Robot { move() { Func helper() { print This; } } }
    # 이 언어는 클로저가 없어서(Storage.push_call_frame이 호출마다 지역
    # 스코프를 초기화) helper는 메서드로 바인딩되지 않은 일반 Function이라
    # This가 실행 시점에 없다 (Undefined variable 'This'). 그래서 정적
    # 검사에서도 "클래스 밖"과 동일하게 잡아야 한다.
    helper = make_function(name="helper", body=[PrintStmt(expression=make_this())])
    method = make_function(name="move", body=[helper])
    cls = make_class(methods=[method])
    checker = CheckerUnit([cls])

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Can't use 'this' outside of a class."


def test_check_detects_super_inside_plain_function_nested_in_method():
    # Class SpeedRobot : Robot { move() { Func helper() { Super.move(); } } }
    # This와 같은 이유로 Super도 helper 안에서는 유효하지 않다.
    helper = make_function(name="helper", body=[ExpressionStmt(expression=make_super())])
    method = make_function(name="move", body=[helper])
    cls = make_class(
        name="SpeedRobot",
        superclass=VariableExpr(Token(TokenType.IDENTIFIER, "Robot")),
        methods=[method],
    )
    checker = CheckerUnit([cls])

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Can't use 'super' outside of a class."


def test_check_allows_return_value_in_function_nested_inside_init():
    # Class Robot { init() { Func helper() { return 5; } } }  -- helper는 init과 별개 함수다.
    helper = make_function(
        name="helper",
        body=[ReturnStmt(keyword=Token(TokenType.RETURN, "return"), value=LiteralExpr(5))],
    )
    init_method = make_function(name="init", body=[helper])
    cls = make_class(methods=[init_method])
    checker = CheckerUnit([cls])

    assert checker.check() == []


def test_check_does_not_crash_when_superclass_is_not_a_variable_expr():
    # Class Robot : 10 { }  -- "클래스가 아닌 대상 상속"은 런타임 오류라 여기서 죽으면 안 된다.
    cls = make_class(name="Robot", superclass=LiteralExpr(10))
    checker = CheckerUnit([cls])

    assert checker.check() == []
