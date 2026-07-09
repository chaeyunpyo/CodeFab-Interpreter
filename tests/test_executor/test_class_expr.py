"""ThisExpr / FieldGetExpr / FieldSetExpr / SuperExpr 평가 통합 테스트.

테스트 구조:
    TestThisExpr          - this 키워드 평가
    TestFieldGetExpr      - 필드/메서드 읽기 표현식 평가
    TestFieldSetExpr      - 필드 쓰기 표현식 평가
    TestMethodCallIntegration  - instance.method() 전체 흐름
    TestInheritanceIntegration - 상속/오버라이딩 흐름
    TestSuperExpr         - super 메서드 참조 및 호출
"""

import pytest

from executor import (
    Function,
    LoxClass,
    LoxInstance,
    NotAClassError,
    NotAnInstanceError,
    UndefinedPropertyError,
    UndefinedVariableError,
    evaluate,
    execute,
)
from nodes.expr import (
    BinaryExpr,
    CallExpr,
    FieldGetExpr,
    FieldSetExpr,
    InstanceOfExpr,
    LiteralExpr,
    SuperExpr,
    ThisExpr,
    VariableExpr,
)
from nodes.stmt import ClassStmt, ExpressionStmt, FunctionStmt, ReturnStmt
from nodes.token_type import TokenType

from helpers import tok


# ── AST 조립 헬퍼 ─────────────────────────────────────────────────────────────

def name_tok(name: str):
    return tok(TokenType.IDENTIFIER, name)


def this_tok():
    return tok(TokenType.THIS, "This")


def super_tok():
    return tok(TokenType.SUPER, "Super")


def instanceof_tok():
    return tok(TokenType.INSTANCEOF, "instanceof")


def instanceof_expr(obj_expr, class_expr) -> InstanceOfExpr:
    return InstanceOfExpr(obj_expr, instanceof_tok(), class_expr)


def declare_method(name: str, params: list, body: list) -> FunctionStmt:
    return FunctionStmt(
        tok(TokenType.IDENTIFIER, name),
        [tok(TokenType.IDENTIFIER, p) for p in params],
        body,
    )


def declare_class(name: str, methods: list, superclass=None) -> ClassStmt:
    return ClassStmt(tok(TokenType.IDENTIFIER, name), superclass, methods)


def var_expr(name: str) -> VariableExpr:
    return VariableExpr(tok(TokenType.IDENTIFIER, name))


def call_expr(callee, *arguments) -> CallExpr:
    return CallExpr(callee, tok(TokenType.LEFT_PAREN, "("), list(arguments))


def ret(value=None) -> ReturnStmt:
    return ReturnStmt(tok(TokenType.RETURN, "return"), value)


def field_get(obj_expr, field_name: str) -> FieldGetExpr:
    return FieldGetExpr(obj_expr, name_tok(field_name))


def field_set(obj_expr, field_name: str, value_expr) -> FieldSetExpr:
    return FieldSetExpr(obj_expr, name_tok(field_name), value_expr)


def this_expr() -> ThisExpr:
    return ThisExpr(this_tok())


def super_expr(method_name: str) -> SuperExpr:
    return SuperExpr(super_tok(), name_tok(method_name))


def lit(value) -> LiteralExpr:
    return LiteralExpr(value)


def plus(left, right) -> BinaryExpr:
    return BinaryExpr(left, tok(TokenType.PLUS, "+"), right)


# ── ThisExpr 평가 ──────────────────────────────────────────────────────────────

class TestThisExpr:
    def test_바인딩된_메서드_안에서_this는_인스턴스를_반환한다(self, storage):
        klass = LoxClass("Robot")
        fn = Function(
            declare_method("get_self", [], [ret(this_expr())]),
            owner_class=klass,
        )
        instance = LoxInstance(klass)
        result = fn.bind(instance).call(storage, [])
        assert result is instance

    def test_메서드_외부에서_this를_평가하면_UndefinedVariableError(self, storage):
        with pytest.raises(UndefinedVariableError):
            evaluate(this_expr(), storage)

    def test_this_평가_오류에_keyword_토큰이_설정된다(self, storage):
        keyword = this_tok()
        with pytest.raises(UndefinedVariableError) as exc_info:
            evaluate(ThisExpr(keyword), storage)
        assert exc_info.value.token is keyword


# ── FieldGetExpr 평가 ──────────────────────────────────────────────────────────

class TestFieldGetExpr:
    def test_인스턴스_필드를_읽는다(self, storage):
        klass = LoxClass("Robot")
        instance = LoxInstance(klass)
        instance.fields["speed"] = 42.0
        storage.define("r", instance)
        result = evaluate(field_get(var_expr("r"), "speed"), storage)
        assert result == 42.0

    def test_인스턴스_메서드를_읽으면_bound_Function을_반환한다(self, storage):
        klass = LoxClass("Robot")
        klass.methods["move"] = Function(declare_method("move", [], []), owner_class=klass)
        instance = LoxInstance(klass)
        storage.define("r", instance)
        bound = evaluate(field_get(var_expr("r"), "move"), storage)
        assert isinstance(bound, Function)
        assert bound.bound_instance is instance

    def test_인스턴스가_아닌_값에_필드_접근하면_NotAnInstanceError(self, storage):
        storage.define("x", 10.0)
        with pytest.raises(NotAnInstanceError):
            evaluate(field_get(var_expr("x"), "speed"), storage)

    def test_없는_필드를_읽으면_UndefinedPropertyError(self, storage):
        klass = LoxClass("Robot")
        instance = LoxInstance(klass)
        storage.define("r", instance)
        with pytest.raises(UndefinedPropertyError):
            evaluate(field_get(var_expr("r"), "power"), storage)


# ── FieldSetExpr 평가 ──────────────────────────────────────────────────────────

class TestFieldSetExpr:
    def test_인스턴스_필드에_값을_쓴다(self, storage):
        klass = LoxClass("Robot")
        instance = LoxInstance(klass)
        storage.define("r", instance)
        evaluate(field_set(var_expr("r"), "speed", lit(99.0)), storage)
        assert instance.fields["speed"] == 99.0

    def test_필드_쓰기_표현식은_대입한_값을_반환한다(self, storage):
        klass = LoxClass("Robot")
        instance = LoxInstance(klass)
        storage.define("r", instance)
        result = evaluate(field_set(var_expr("r"), "speed", lit(7.0)), storage)
        assert result == 7.0

    def test_없는_필드에_쓰면_새로_생성된다(self, storage):
        klass = LoxClass("Robot")
        instance = LoxInstance(klass)
        storage.define("r", instance)
        evaluate(field_set(var_expr("r"), "new_field", lit(1.0)), storage)
        assert instance.fields["new_field"] == 1.0

    def test_인스턴스가_아닌_값에_필드_쓰기하면_NotAnInstanceError(self, storage):
        storage.define("x", "hello")
        with pytest.raises(NotAnInstanceError):
            evaluate(field_set(var_expr("x"), "speed", lit(1.0)), storage)


# ── 메서드 호출 통합 ───────────────────────────────────────────────────────────

class TestMethodCallIntegration:
    def test_인스턴스_메서드를_호출할_수_있다(self, storage):
        # Class Robot { greet() { return 42; } }
        execute(
            declare_class("Robot", [declare_method("greet", [], [ret(lit(42.0))])]),
            storage,
        )
        storage.define("r", evaluate(call_expr(var_expr("Robot")), storage))
        result = evaluate(call_expr(field_get(var_expr("r"), "greet")), storage)
        assert result == 42.0

    def test_메서드_안에서_this로_필드를_쓰고_읽는다(self, storage):
        # Class Robot {
        #   setSpeed(v) { this.speed = v; }
        #   getSpeed()  { return this.speed; }
        # }
        execute(
            declare_class("Robot", [
                declare_method("setSpeed", ["v"], [
                    ExpressionStmt(field_set(this_expr(), "speed", var_expr("v"))),
                ]),
                declare_method("getSpeed", [], [
                    ret(field_get(this_expr(), "speed")),
                ]),
            ]),
            storage,
        )
        storage.define("r", evaluate(call_expr(var_expr("Robot")), storage))
        evaluate(call_expr(field_get(var_expr("r"), "setSpeed"), lit(55.0)), storage)
        result = evaluate(call_expr(field_get(var_expr("r"), "getSpeed")), storage)
        assert result == 55.0

    def test_init에서_this로_필드_초기화_후_메서드로_읽는다(self, storage):
        # Class Robot { init(name) { this.name = name; } getName() { return this.name; } }
        execute(
            declare_class("Robot", [
                declare_method("init", ["name"], [
                    ExpressionStmt(field_set(this_expr(), "name", var_expr("name"))),
                ]),
                declare_method("getName", [], [ret(field_get(this_expr(), "name"))]),
            ]),
            storage,
        )
        storage.define("r", evaluate(call_expr(var_expr("Robot"), lit("AndOr")), storage))
        result = evaluate(call_expr(field_get(var_expr("r"), "getName")), storage)
        assert result == "AndOr"


# ── 상속/오버라이딩 통합 ───────────────────────────────────────────────────────

class TestInheritanceIntegration:
    def test_자식_인스턴스가_부모_메서드를_호출한다(self, storage):
        # Class Robot { move() { return 10; } }
        # Class SpeedRobot : Robot {}
        execute(
            declare_class("Robot", [declare_method("move", [], [ret(lit(10.0))])]),
            storage,
        )
        execute(
            declare_class("SpeedRobot", [], superclass=var_expr("Robot")),
            storage,
        )
        storage.define("sr", evaluate(call_expr(var_expr("SpeedRobot")), storage))
        result = evaluate(call_expr(field_get(var_expr("sr"), "move")), storage)
        assert result == 10.0

    def test_자식이_메서드를_오버라이드하면_자식_메서드가_호출된다(self, storage):
        # Class Robot { move() { return 10; } }
        # Class SpeedRobot : Robot { move() { return 99; } }
        execute(
            declare_class("Robot", [declare_method("move", [], [ret(lit(10.0))])]),
            storage,
        )
        execute(
            declare_class("SpeedRobot", [declare_method("move", [], [ret(lit(99.0))])],
                          superclass=var_expr("Robot")),
            storage,
        )
        storage.define("sr", evaluate(call_expr(var_expr("SpeedRobot")), storage))
        result = evaluate(call_expr(field_get(var_expr("sr"), "move")), storage)
        assert result == 99.0

    def test_다단계_상속에서_가장_가까운_메서드가_호출된다(self, storage):
        # Robot(move→10) → SpeedRobot → TurboRobot(move→99)
        execute(declare_class("Robot", [declare_method("move", [], [ret(lit(10.0))])]), storage)
        execute(declare_class("SpeedRobot", [], superclass=var_expr("Robot")), storage)
        execute(
            declare_class("TurboRobot", [declare_method("move", [], [ret(lit(99.0))])],
                          superclass=var_expr("SpeedRobot")),
            storage,
        )
        storage.define("t", evaluate(call_expr(var_expr("TurboRobot")), storage))
        assert evaluate(call_expr(field_get(var_expr("t"), "move")), storage) == 99.0


# ── SuperExpr 평가 ────────────────────────────────────────────────────────────

class TestSuperExpr:
    def test_super_메서드_호출이_부모_구현을_실행한다(self, storage):
        # Class Robot { move() { return 10; } }
        # Class SpeedRobot : Robot { move() { return super.move() + 5; } }
        execute(declare_class("Robot", [declare_method("move", [], [ret(lit(10.0))])]), storage)
        execute(
            declare_class("SpeedRobot", [
                declare_method("move", [], [
                    ret(plus(call_expr(super_expr("move")), lit(5.0))),
                ]),
            ], superclass=var_expr("Robot")),
            storage,
        )
        storage.define("sr", evaluate(call_expr(var_expr("SpeedRobot")), storage))
        result = evaluate(call_expr(field_get(var_expr("sr"), "move")), storage)
        assert result == 15.0

    def test_super는_런타임_타입이_아닌_정의된_클래스_기준으로_부모를_찾는다(self, storage):
        # 3단 상속: Robot(move→10) → SpeedRobot(move→super.move()+5) → TurboRobot(move→super.move()+1)
        # TurboRobot().move() 는 SpeedRobot.move()를 호출하고,
        # SpeedRobot.move() 내부의 super는 Robot을 기준으로 찾아야 한다.
        execute(declare_class("Robot", [declare_method("move", [], [ret(lit(10.0))])]), storage)
        execute(
            declare_class("SpeedRobot", [
                declare_method("move", [], [
                    ret(plus(call_expr(super_expr("move")), lit(5.0))),
                ]),
            ], superclass=var_expr("Robot")),
            storage,
        )
        execute(
            declare_class("TurboRobot", [
                declare_method("move", [], [
                    ret(plus(call_expr(super_expr("move")), lit(1.0))),
                ]),
            ], superclass=var_expr("SpeedRobot")),
            storage,
        )
        storage.define("t", evaluate(call_expr(var_expr("TurboRobot")), storage))
        # TurboRobot.move() = SpeedRobot.move() + 1 = (Robot.move() + 5) + 1 = 16
        result = evaluate(call_expr(field_get(var_expr("t"), "move")), storage)
        assert result == 16.0

    def test_없는_부모_메서드를_super로_접근하면_UndefinedPropertyError(self, storage):
        # Class Robot {}  Class SpeedRobot : Robot { test() { return super.fly(); } }
        execute(declare_class("Robot", []), storage)
        execute(
            declare_class("SpeedRobot", [
                declare_method("test", [], [ret(call_expr(super_expr("fly")))]),
            ], superclass=var_expr("Robot")),
            storage,
        )
        storage.define("sr", evaluate(call_expr(var_expr("SpeedRobot")), storage))
        with pytest.raises(UndefinedPropertyError):
            evaluate(call_expr(field_get(var_expr("sr"), "test")), storage)

    def test_super_외부_사용시_UndefinedVariableError(self, storage):
        with pytest.raises(UndefinedVariableError):
            evaluate(super_expr("move"), storage)


# ── InstanceOfExpr 평가 ───────────────────────────────────────────────────────

class TestInstanceOfExpr:
    def test_자신의_클래스에_대해_True를_반환한다(self, storage):
        execute(declare_class("Robot", []), storage)
        storage.define("r", evaluate(call_expr(var_expr("Robot")), storage))
        assert evaluate(instanceof_expr(var_expr("r"), var_expr("Robot")), storage) is True

    def test_관계_없는_클래스에_대해_False를_반환한다(self, storage):
        execute(declare_class("Robot", []), storage)
        execute(declare_class("Worker", []), storage)
        storage.define("r", evaluate(call_expr(var_expr("Robot")), storage))
        assert evaluate(instanceof_expr(var_expr("r"), var_expr("Worker")), storage) is False

    def test_부모_클래스에_대해_True를_반환한다(self, storage):
        # SpeedRobot instanceof Robot → True (상속 관계)
        execute(declare_class("Robot", []), storage)
        execute(declare_class("SpeedRobot", [], superclass=var_expr("Robot")), storage)
        storage.define("sr", evaluate(call_expr(var_expr("SpeedRobot")), storage))
        assert evaluate(instanceof_expr(var_expr("sr"), var_expr("Robot")), storage) is True

    def test_자식_클래스에_대해_False를_반환한다(self, storage):
        # Robot instanceof SpeedRobot → False (역방향)
        execute(declare_class("Robot", []), storage)
        execute(declare_class("SpeedRobot", [], superclass=var_expr("Robot")), storage)
        storage.define("r", evaluate(call_expr(var_expr("Robot")), storage))
        assert evaluate(instanceof_expr(var_expr("r"), var_expr("SpeedRobot")), storage) is False

    def test_다단계_상속_체인에서_조상_클래스에_대해_True를_반환한다(self, storage):
        # TurboRobot instanceof Robot → True (Robot → SpeedRobot → TurboRobot)
        execute(declare_class("Robot", []), storage)
        execute(declare_class("SpeedRobot", [], superclass=var_expr("Robot")), storage)
        execute(declare_class("TurboRobot", [], superclass=var_expr("SpeedRobot")), storage)
        storage.define("t", evaluate(call_expr(var_expr("TurboRobot")), storage))
        assert evaluate(instanceof_expr(var_expr("t"), var_expr("Robot")), storage) is True

    def test_인스턴스가_아닌_값은_False를_반환한다(self, storage):
        execute(declare_class("Robot", []), storage)
        storage.define("x", 42.0)
        assert evaluate(instanceof_expr(var_expr("x"), var_expr("Robot")), storage) is False

    def test_오른쪽이_클래스가_아니면_NotAClassError(self, storage):
        storage.define("r", LoxInstance(LoxClass("Robot")))
        storage.define("notClass", 10.0)
        with pytest.raises(NotAClassError):
            evaluate(instanceof_expr(var_expr("r"), var_expr("notClass")), storage)


class TestReprIsHumanReadable:
    """LoxClass/LoxInstance는 print나 오류 메시지에서 짧게 보여야 한다 -
    기본 dataclass repr은 methods/필드까지 전부 펼쳐서 너무 장황하다.
    """

    def test_LoxClass_repr은_클래스_이름만_보여준다(self):
        assert repr(LoxClass("Robot")) == "Robot"

    def test_LoxInstance_repr은_클래스명과_instance만_보여준다(self):
        assert repr(LoxInstance(LoxClass("Robot"))) == "Robot instance"
