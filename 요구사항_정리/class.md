# [추가] class 구현 항목

> 참고: 원본 PDF에는 `This`/`Super`(대문자)와 `this`/`super`(소문자) 표기가
> 슬라이드마다 섞여 있다. 실제 구현 시 대소문자 규칙은 팀에서 통일해서
> 정하면 된다.

## Node 정의

기존 `nodes/stmt.py`, `nodes/expr.py`에 아래 타입을 추가한다.

**Stmt 추가**

| 클래스 | 필드 | 설명 | 예시 |
| --- | --- | --- | --- |
| `ClassStmt` | `name: Token`, `superclass: Optional[Expr]`, `methods: List[FunctionStmt]` | 클래스 선언. superclass는 부모 클래스 이름(보통 VariableExpr), 없으면 None. methods는 생성자(init) 포함 전체 메서드 목록 | `Class SpeedRobot : Robot { ... }` |

**Expr 추가**

| 클래스 | 필드 | 설명 | 예시 |
| --- | --- | --- | --- |
| `ThisExpr` | `keyword: Token` | 메서드 내부에서 자기 인스턴스를 가리킴 | `this.name` |
| `SuperExpr` | `keyword: Token`, `method: Token` | 부모 클래스의 메서드를 가리킴 | `super.move` |
| `FieldGetExpr` | `object: Expr`, `name: Token` | 필드 읽기 | `r.speed` |
| `FieldSetExpr` | `object: Expr`, `name: Token`, `value: Expr` | 필드 쓰기 | `r.speed = 10` |
| `InstanceOfExpr` | `object: Expr`, `keyword: Token`, `class_name: Expr` | 인스턴스가 특정 클래스(또는 조상)인지 확인. class_name은 이름 참조만 담고 실제 판정은 Executor 몫 | `w instanceof Robot` |

## 구현해야 할 기능

| 분류 | 항목 | 설명 | 예시 |
| --- | --- | --- | --- |
| 클래스 선언 | Class 선언문 | 이름과 본문을 갖는 클래스를 선언 | `Class Robot { ... }` |
| 인스턴스 | 인스턴스 생성 | 클래스를 함수처럼 호출해서 생성 | `var r = Robot();` |
| 필드 | 필드 쓰기 (set) | 없는 필드면 새로 생성 | `r.speed = 10;` |
| 필드 | 필드 읽기 (get) | 저장된 필드 값을 읽음 | `print r.speed;` |
| 필드 | 필드 갱신 | 기존 값을 읽어서 다시 씀 | `r.speed = r.speed + 5;` |
| 메서드 | 메서드 선언 | 클래스 내부에 동작을 선언 | `Class Robot { move(dist) { ... } }` |
| 메서드 | 메서드 호출 | 인스턴스를 통해 메서드 실행 | `r.move(5);` |
| 메서드 | this로 필드 접근 | 메서드 내부에서 자기 인스턴스 필드 접근 | `this.position = this.position + dist;` |
| 메서드 | 메서드 내부 호출 | 메서드 안에서 다른 메서드 호출 | `this.report();` |
| 생성자 | init 선언 | 인스턴스 생성 시 자동 호출되는 초기화 메서드 | `init(name, speed) { ... }` |
| 생성자 | 생성 시 인자 전달 | 클래스 호출 인자가 init으로 전달됨 | `var r = Robot("AndOr", 10);` |
| 생성자 | 생성자에서 필드 초기화 | init 안에서 this 필드를 채움 | `this.name = name;` |
| 상속 | 상속 선언 | 부모 클래스를 지정 | `Class SpeedRobot : Robot { ... }` |
| 상속 | 메서드 상속 | 자식 인스턴스에서 부모 메서드 호출 가능 | `SpeedRobot().report();` |
| 상속 | 메서드 오버라이딩 | 자식에서 같은 이름 메서드 재정의 | `Class SpeedRobot : Robot { move(dist) { ... } }` |
| 상속 | super 호출 | 부모 메서드를 명시적으로 실행 | `super.move(dist);` |
| 타입 검사 | instanceof 연산자 | 인스턴스가 특정 클래스(또는 조상)인지 확인 | `w instanceof Robot` |

## 구현해야 할 오류 검사

| 분류 | 항목 | 설명 | 예시 |
| --- | --- | --- | --- |
| 정적 오류 | 클래스 외부 this 사용 | 클래스 밖에서 this를 쓰면 오류 | `print this;` |
| 정적 오류 | init에서 return 사용 | 생성자는 값을 반환할 수 없음 | `init() { return 5; }` |
| 정적 오류 | 자기 자신 상속 | 클래스가 자기 자신을 부모로 지정 (AST상 이름 비교만으로 판단 가능) | `Class Robot : Robot { ... }` |
| 정적 오류 | 클래스 외부 super 사용 | 클래스 밖에서 super를 쓰면 오류 | `super.move();` |
| 정적 오류 | 부모 없는 클래스의 super | 상속하지 않은 클래스 내부에서 super 사용 | 상속 없는 클래스 안의 `super.move()` |
| 런타임 오류 | 클래스가 아닌 대상 상속 | 부모 자리의 값이 실행 시점에 클래스가 아님 (변수라 재할당될 수 있어 런타임에만 확정됨) | `var x = 10; Class Robot : x { ... }` |
| 런타임 오류 | 인스턴스가 아닌 대상의 필드 접근 | 인스턴스가 아닌 값에 필드 대입 | `var x = "hello"; x.field = 1;` |
| 런타임 오류 | 존재하지 않는 필드/메서드 접근 | 정의되지 않은 필드·메서드 호출 | `r.notExist();` |
| 런타임 오류 | 존재하지 않는 필드 읽기 | 정의되지 않은 필드를 읽음 | `print r.power;` |

## 구현 현황 (Checker)

정적 오류 5개는 `src/checker/`에 구현 완료됨 (테스트: `tests/test_checker/test_checker_class.py`).

| 항목 | 구현된 메시지 |
| --- | --- |
| 클래스 외부 this 사용 | `Can't use 'this' outside of a class.` |
| 클래스 외부 super 사용 | `Can't use 'super' outside of a class.` |
| 부모 없는 클래스의 super | `Can't use 'super' in a class with no superclass.` |
| 자기 자신 상속 | `A class can't inherit from itself.` |
| init에서 값 있는 return | `Can't return a value from an initializer.` |

`init() { return; }`처럼 값 없는 조기 `return`은 허용된다 (생성자가 항상
인스턴스를 반환한다는 원칙은 지키면서, 값을 반환하려는 시도만 막는다).

필드/메서드/인스턴스 생성/상속 실행과 런타임 오류 4개는 Assembler/Executor
쪽에 이미 구현되어 있다.

| 항목 | 구현 |
| --- | --- |
| 클래스가 아닌 대상 상속 | `NotAClassError` |
| 인스턴스가 아닌 대상의 필드 접근 | `NotAnInstanceError` |
| 존재하지 않는 필드/메서드 접근·읽기 | `UndefinedPropertyError` |

`instanceof` 연산자도 Assembler 파싱(`_expression_parser.py`의
`_finish_instanceof`)이 추가되면서 Node/Executor 평가(`_evaluate_instanceof`)까지
end-to-end로 완료됨.

## 적용 가능한 디자인 패턴 (가산점)

> 디자인 패턴은 여러 곳에서 발생될 수 있는 문제를 해결하는 일반화된
> 모범 사례입니다. GoF 디자인 패턴을 사용하면 약간의 추가 점수가
> 주어집니다 (`유의사항.md` 참고).

| 패턴 | 적용 지점 |
| --- | --- |
| Command Pattern | 인스턴스 생성(`Robot()`)도 함수 호출과 같은 callable 인터페이스로 다루면, function에서 만든 호출 처리 코드를 그대로 재사용할 수 있다. |
| Chain of Responsibility | 메서드/필드 조회 시 자기 클래스에서 못 찾으면 부모 클래스로, 또 그 부모로 넘어가며 찾는 상속 체인 탐색 구조. |
| Prototype 유사 | 인스턴스 생성 시 클래스가 갖고 있는 메서드 테이블을 인스턴스가 그대로 참조하는 구조 (완전한 Prototype 패턴은 아니지만 개념이 유사). |

## 구현 항목 요약

| 분류 | 개수 |
| --- | -: |
| Node (Stmt) | 1개 |
| Node (Expr) | 5개 |
| 클래스 선언/인스턴스 | 2개 |
| 필드 | 3개 |
| 메서드 | 4개 |
| 생성자 | 3개 |
| 상속 | 4개 |
| 타입 검사 | 1개 |
| 오류 검사 | 9개 |
| 적용 후보 패턴 | 3개 |
