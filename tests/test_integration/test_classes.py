"""class 선언/인스턴스/필드/메서드/상속/super/instanceof 관련 블랙박스 테스트.
(요구사항_정리/class.md)

this/super는 대문자 This/Super로만 써야 한다 (요구사항_정리/TokenType.md에
나열된 표기만 유효하고 대소문자를 구분한다 — 소문자 this/super는
예약어가 아니라 그냥 식별자로 취급된다).
"""

import textwrap


def test_instance_creation_and_field_access(run_source):
    output = run_source(
        """
        Class Robot {
          init(name, speed) { This.name = name; This.speed = speed; }
        }
        var r = Robot("AndOr", 10);
        print r.name;
        print r.speed;
        """
    )
    assert output == textwrap.dedent(
        """\
        AndOr
        10
        """
    )


def test_method_call_reads_and_writes_field_via_this(run_source):
    output = run_source(
        """
        Class Robot {
          init(name, speed) { This.name = name; This.speed = speed; }
          move(dist) { This.speed = This.speed + dist; return This.speed; }
        }
        var r = Robot("AndOr", 10);
        print r.move(5);
        """
    )
    assert output == "15\n"


def test_method_calls_another_method_via_this(run_source):
    output = run_source(
        """
        Class Robot {
          init(n) { This.n = n; }
          report() { This.log(); }
          log() { print This.n; }
        }
        var r = Robot(5);
        r.report();
        """
    )
    assert output == "5\n"


def test_field_write_creates_new_field_if_missing(run_source):
    output = run_source(
        """
        Class Robot { }
        var r = Robot();
        r.speed = 42;
        print r.speed;
        """
    )
    assert output == "42\n"


def test_inheritance_and_super_call(run_source):
    output = run_source(
        """
        Class Robot { speak() { print "beep"; } }
        Class SpeedRobot : Robot {
          speak() { Super.speak(); print "zoom"; }
        }
        var sr = SpeedRobot();
        sr.speak();
        """
    )
    assert output == textwrap.dedent(
        """\
        beep
        zoom
        """
    )


def test_super_chain_across_three_generations(run_source):
    output = run_source(
        """
        Class A { speak() { print "A"; } }
        Class B : A { speak() { Super.speak(); print "B"; } }
        Class C : B { speak() { Super.speak(); print "C"; } }
        var c = C();
        c.speak();
        """
    )
    assert output == textwrap.dedent(
        """\
        A
        B
        C
        """
    )


def test_instanceof_checks_direct_and_ancestor_classes(run_source):
    output = run_source(
        """
        Class Robot { }
        Class SpeedRobot : Robot { }
        var sr = SpeedRobot();
        var r = Robot();
        print sr instanceof Robot;
        print sr instanceof SpeedRobot;
        print r instanceof SpeedRobot;
        """
    )
    assert output == textwrap.dedent(
        """\
        true
        true
        false
        """
    )


def test_array_of_instances_indexed_and_field_accessed(run_source):
    output = run_source(
        """
        Class Robot { init(n) { This.n = n; } }
        var team = Array(2);
        team[0] = Robot("A");
        team[1] = Robot("B");
        print team[0].n;
        print team[1].n;
        """
    )
    assert output == textwrap.dedent(
        """\
        A
        B
        """
    )


def test_this_super_keywords_are_case_sensitive(run_source):
    """this/super(소문자)는 예약어가 아니라 그냥 식별자로 취급되어야 한다
    (요구사항_정리/TokenType.md에 나열된 This/Super 표기만 유효).
    클래스 밖에서 정의되지 않은 변수로 취급되면, 이는 Checker가 아니라
    Executor가 잡는 "정의되지 않은 변수" 오류로 나타난다 — 만약
    this/super가 예약어로 인식됐다면 Checker가 "Can't use 'this'
    outside of a class."로 먼저 잡았을 것이다.
    """
    output = run_source("print this;")
    assert output == "[Executor] Line 1: Undefined variable 'this'\n"


def test_accessing_undefined_property_raises_executor_error(run_source):
    output = run_source(
        """
        Class Robot { }
        var r = Robot();
        print r.power;
        """
    )
    assert output == "[Executor] Line 4: Undefined property 'power'\n"


def test_field_access_on_non_instance_raises_executor_error(run_source):
    output = run_source(
        """
        var x = 10;
        x.field = 1;
        """
    )
    assert output == "[Executor] Line 3: 필드 접근은 인스턴스에만 사용할 수 있습니다.\n"


def test_inheriting_from_non_class_value_raises_executor_error(run_source):
    output = run_source(
        """
        var x = 10;
        Class Robot : x { }
        """
    )
    assert output == "[Executor] Line 3: 클래스만 상속할 수 있습니다.\n"


def test_subclass_without_init_uses_parent_constructor_automatically(run_source):
    """자식 클래스가 init을 재정의하지 않으면, 부모의 init이 그대로
    생성자로 쓰여야 한다.
    """
    output = run_source(
        """
        Class Robot { init(n) { This.n = n; } }
        Class SpeedRobot : Robot { }
        var sr = SpeedRobot(7);
        print sr.n;
        """
    )
    assert output == "7\n"


def test_subclass_can_override_method_without_calling_super(run_source):
    output = run_source(
        """
        Class Robot { speak() { print "beep"; } }
        Class SpeedRobot : Robot { speak() { print "zoom"; } }
        var sr = SpeedRobot();
        sr.speak();
        """
    )
    assert output == "zoom\n"


def test_each_instance_has_independent_field_state(run_source):
    output = run_source(
        """
        Class Counter { init() { This.n = 0; } inc() { This.n = This.n + 1; } }
        var a = Counter();
        var b = Counter();
        a.inc();
        a.inc();
        b.inc();
        print a.n;
        print b.n;
        """
    )
    assert output == textwrap.dedent(
        """\
        2
        1
        """
    )


def test_this_inside_plain_func_nested_in_method_is_rejected(run_source):
    """메서드 본문에 중첩된 일반 Func(클로저처럼 보이는 helper)는 메서드로
    바인딩되지 않은 Function이라 This가 없다 — 이 언어는 클로저가 없어서
    (호출마다 지역 스코프가 초기화됨) 실행하면 Undefined variable로
    죽는다. Checker가 이걸 "클래스 밖"과 동일하게 미리 잡아야 한다.
    """
    output = run_source(
        """
        Class Robot {
          move() {
            Func helper() { print This.x; }
            return helper();
          }
        }
        var r = Robot();
        r.move();
        """
    )
    assert output == "[Checker] Line 4: Can't use 'this' outside of a class.\n"


def test_super_inside_plain_func_nested_in_method_is_rejected(run_source):
    output = run_source(
        """
        Class Robot { speak() { print "base"; } }
        Class SpeedRobot : Robot {
          speak() {
            Func helper() { Super.speak(); }
            helper();
          }
        }
        var sr = SpeedRobot();
        sr.speak();
        """
    )
    assert output == "[Checker] Line 5: Can't use 'super' outside of a class.\n"
