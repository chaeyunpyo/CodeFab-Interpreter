import pytest

from executor import (
    ArityMismatchError,
    Function,
    LoxCallable,
    LoxClass,
    LoxInstance,
    NotAClassError,
    UndefinedPropertyError,
    UndefinedVariableError,
    evaluate,
    execute,
)
from nodes.expr import CallExpr, LiteralExpr, VariableExpr
from nodes.stmt import ClassStmt, FunctionStmt, ReturnStmt
from nodes.token_type import TokenType

from helpers import tok

# NOTE 1: FieldGetExpr/FieldSetExpr("this.x = ...")의 evaluate() 처리는
# Executor D 담당(_expr.py에 추가 예정)이라 아직 없다. 그래서 이 파일의
# 테스트는 "this.field = value" 같은 언어 수준 문법 대신, this/__class__가
# 스코프에 올바르게 주입되는지를 LoxInstance.get/set 직접 호출이나
# return값으로 캡처하는 방식으로 검증한다.
#
# NOTE 2: Storage.push_call_frame()은 전역 스코프를 참조가 아니라
# "복사본"으로 넘긴다(_storage.py). 그래서 함수/메서드 호출 안에서 이미
# 있던 전역 변수에 대입해도 호출이 끝나면 사라진다 - 전역 변수 캡처
# 트릭 대신 return으로 값을 직접 확인해야 하는 이유.


# ── 테스트용 AST 조립 헬퍼 ────────────────────────────────────────────────────

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


def call(callee, *arguments) -> CallExpr:
    return CallExpr(callee, tok(TokenType.LEFT_PAREN, "("), list(arguments))


def ret(value=None) -> ReturnStmt:
    return ReturnStmt(tok(TokenType.RETURN, "return"), value)


def name_tok(name: str):
    return tok(TokenType.IDENTIFIER, name)


# ── 클래스 선언 ───────────────────────────────────────────────────────────────

class TestExecuteClassStmt:
    def test_클래스를_선언하면_저장소에_LoxClass값으로_등록된다(self, storage):
        execute(declare_class("Robot", []), storage)
        assert isinstance(storage.get("Robot"), LoxClass)

    def test_LoxClass는_LoxCallable_인터페이스를_구현한다(self, storage):
        execute(declare_class("Robot", []), storage)
        assert isinstance(storage.get("Robot"), LoxCallable)

    def test_클래스가_아닌_대상을_상속하면_오류(self, storage):
        storage.define("x", 10.0)
        with pytest.raises(NotAClassError):
            execute(declare_class("Robot", [], superclass=var_expr("x")), storage)


# ── 인스턴스 생성 ─────────────────────────────────────────────────────────────

class TestInstanceCreation:
    def test_init이_없으면_호출만으로_인스턴스가_생성된다(self, storage):
        execute(declare_class("Robot", []), storage)
        instance = evaluate(call(var_expr("Robot")), storage)
        assert isinstance(instance, LoxInstance)
        assert instance.klass.name == "Robot"

    def test_init이_있으면_생성_시점에_자동_호출된다(self, storage):
        # Class Robot { init(name) { return name; } }
        # (실제 문법은 this.name = name; 이지만 FieldSetExpr 평가는 D 담당이라
        # 아직 없음 - 여기서는 init이 인자를 바인딩받아 실행되는지를
        # return값으로 확인한다)
        execute(
            declare_class("Robot", [declare_method("init", ["name"], [ret(var_expr("name"))])]),
            storage,
        )
        klass = storage.get("Robot")
        instance = evaluate(call(var_expr("Robot"), LiteralExpr("AndOr")), storage)
        assert isinstance(instance, LoxInstance)
        # LoxClass.call()은 Lox 관례상 init의 반환값을 버리고 instance를
        # 돌려주므로, init이 실제로 인자를 받아 실행됐는지는 bind된
        # Function을 직접 호출해 반환값으로 확인한다.
        initializer = klass.find_method("init")
        assert initializer.bind(instance).call(storage, ["AndOr"]) == "AndOr"

    def test_init_인자_개수가_다르면_ArityMismatchError(self, storage):
        execute(
            declare_class("Robot", [declare_method("init", ["name"], [])]), storage
        )
        with pytest.raises(ArityMismatchError):
            evaluate(call(var_expr("Robot")), storage)


# ── 필드/메서드 저장소 (LoxInstance.get/set 단위 테스트) ─────────────────────

class TestLoxInstanceFieldStorage:
    def test_필드를_쓰고_읽을_수_있다(self, storage):
        klass = LoxClass("Robot")
        instance = LoxInstance(klass)
        instance.set(name_tok("speed"), 10.0)
        assert instance.get(name_tok("speed")) == 10.0

    def test_없는_필드를_다시_쓰면_새로_생성된다(self, storage):
        klass = LoxClass("Robot")
        instance = LoxInstance(klass)
        instance.set(name_tok("speed"), 10.0)
        instance.set(name_tok("speed"), 20.0)
        assert instance.get(name_tok("speed")) == 20.0

    def test_없는_필드를_읽으면_UndefinedPropertyError(self, storage):
        klass = LoxClass("Robot")
        instance = LoxInstance(klass)
        with pytest.raises(UndefinedPropertyError):
            instance.get(name_tok("power"))

    def test_필드에_없으면_메서드를_찾아_bind된_Function을_반환한다(self, storage):
        klass = LoxClass("Robot")
        method = Function(declare_method("move", [], []), owner_class=klass)
        klass.methods["move"] = method
        instance = LoxInstance(klass)
        bound = instance.get(name_tok("move"))
        assert isinstance(bound, Function)
        assert bound.bound_instance is instance


# ── 상속 체인 (find_method) ───────────────────────────────────────────────────

class TestFindMethodInheritance:
    def test_부모_클래스의_메서드를_상속받아_찾는다(self, storage):
        parent = LoxClass("Robot")
        parent.methods["move"] = Function(declare_method("move", [], []), owner_class=parent)
        child = LoxClass("SpeedRobot", superclass=parent)
        found = child.find_method("move")
        assert found is not None
        assert found.owner_class is parent

    def test_자식이_같은_이름_메서드를_오버라이드하면_그것을_우선한다(self, storage):
        parent = LoxClass("Robot")
        parent.methods["move"] = Function(declare_method("move", [], []), owner_class=parent)
        child = LoxClass("SpeedRobot", superclass=parent)
        child_move = Function(declare_method("move", [], []), owner_class=child)
        child.methods["move"] = child_move
        assert child.find_method("move") is child_move

    def test_3단_상속에서_찾은_메서드의_owner_class는_정의된_클래스를_가리킨다(self, storage):
        # Robot -> SpeedRobot(move 정의) -> TurboRobot(move 오버라이드 안 함)
        robot = LoxClass("Robot")
        speed_robot = LoxClass("SpeedRobot", superclass=robot)
        speed_robot.methods["move"] = Function(
            declare_method("move", [], []), owner_class=speed_robot
        )
        turbo_robot = LoxClass("TurboRobot", superclass=speed_robot)

        found = turbo_robot.find_method("move")
        # 인스턴스 런타임 클래스는 TurboRobot이지만, super 해석 기준이 될
        # owner_class는 실제 정의처인 SpeedRobot이어야 한다 (다단계 상속의 핵심).
        assert found.owner_class is speed_robot
        assert found.owner_class is not turbo_robot

    def test_없는_메서드를_찾으면_None을_반환한다(self, storage):
        parent = LoxClass("Robot")
        child = LoxClass("SpeedRobot", superclass=parent)
        assert child.find_method("fly") is None


# ── this 바인딩 통합 ──────────────────────────────────────────────────────────

class TestThisBindingIntegration:
    def test_메서드_호출시_this가_스코프에_주입된다(self, storage):
        klass = LoxClass("Robot")
        fn = Function(declare_method("get_this", [], [ret(var_expr("this"))]), owner_class=klass)
        instance = LoxInstance(klass)
        assert fn.bind(instance).call(storage, []) is instance

    def test_메서드_호출시___class___가_스코프에_주입된다(self, storage):
        klass = LoxClass("Robot")
        fn = Function(declare_method("get_class", [], [ret(var_expr("__class__"))]), owner_class=klass)
        instance = LoxInstance(klass)
        assert fn.bind(instance).call(storage, []) is klass

    def test_bound_instance가_없으면_this와___class___를_주입하지_않는다(self, storage):
        # unbound Function 호출 시(일반 함수와 동일 경로) this를 조회하면
        # UndefinedVariableError가 나야 한다 - bind() 없이는 아무것도 심지 않는지 확인.
        fn = Function(declare_method("plain", [], [ret(var_expr("this"))]))
        with pytest.raises(UndefinedVariableError):
            fn.call(storage, [])

    def test_bind는_owner_class를_그대로_유지한다(self, storage):
        klass = LoxClass("Robot")
        fn = Function(declare_method("move", [], []), owner_class=klass)
        instance = LoxInstance(klass)
        bound = fn.bind(instance)
        assert bound.owner_class is klass
        assert bound.bound_instance is instance
        # 원본 Function은 그대로 unbound 상태 유지 (bind는 새 객체를 반환)
        assert fn.bound_instance is None
