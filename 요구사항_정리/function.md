# [추가] function 구현 항목

## Node 정의

기존 `nodes/stmt.py`, `nodes/expr.py`에 아래 타입을 추가해야 한다.

**Stmt 추가**

| 클래스 | 필드 | 설명 | 예시 |
| --- | --- | --- | --- |
| `FunctionStmt` | `name: Token`, `params: List[Token]`, `body: List[Stmt]` | 함수 선언 (이름, 파라미터 목록, 본문) | `Func add(a, b) { ... }` |
| `ReturnStmt` | `keyword: Token`, `value: Optional[Expr]` | return문. keyword는 오류 위치(줄 번호) 표시용, value가 없으면 null 반환 | `return;` / `return a + b;` |

**Expr 추가**

| 클래스 | 필드 | 설명 | 예시 |
| --- | --- | --- | --- |
| `CallExpr` | `callee: Expr`, `paren: Token`, `arguments: List[Expr]` | 함수 호출 표현식. paren은 오류 위치(줄 번호) 표시용, callee는 호출 대상(보통 `VariableExpr`) | `add(1, 2)` |

## 구현해야 할 기능

| 분류 | 항목 | 설명 | 예시 |
| --- | --- | --- | --- |
| 함수 선언 | Func 선언문 | 이름/파라미터/본문을 갖는 함수를 선언 | `Func add(a, b) { ... }` |
| 함수 호출 | 호출 표현식 | 함수 이름에 인자를 넘겨 호출 | `add(1, 2);` |
| return 처리 | 값 없는 return | 값을 생략하면 null 반환 | `return;` |
| return 처리 | 값 있는 return | 반환값을 호출부에 전달 | `ret = add(1, 2);` |
| 재귀 호출 | 자기 자신 호출 | 함수 본문에서 자기 자신을 다시 호출 | `Func fact(n) { if (n <= 1) return 1; return n * fact(n - 1); }` |

## 구현해야 할 오류 검사

| 분류 | 항목 | 설명 | 예시 |
| --- | --- | --- | --- |
| 정적 오류 | 함수 외부 return | 함수 밖에서 return을 쓰면 오류 | `return 5;` (최상위에 작성) |
| 정적 오류 | 파라미터 이름 중복 | 같은 함수의 파라미터 이름이 겹치면 오류 | `Func foo(a, a) { ... }` |
| 런타임 오류 | 호출 불가 대상 호출 | 함수가 아닌 값을 호출하면 오류 | `var x = "hello"; x();` |
| 런타임 오류 | 인자 개수 불일치 | 선언된 파라미터 수와 호출 인자 수가 다르면 오류 | `Func foo(a, b, c) {...}` 인데 `foo(1, 2);` |

## 적용 가능한 디자인 패턴 (가산점)

> 디자인 패턴은 여러 곳에서 발생될 수 있는 문제를 해결하는 일반화된
> 모범 사례입니다. GoF 디자인 패턴을 사용하면 약간의 추가 점수가
> 주어집니다 (`유의사항.md` 참고).

| 패턴 | 적용 지점 |
| --- | --- |
| Command Pattern | 함수를 "호출 가능한 것(callable)"으로 캡슐화. `CallExpr` 실행 시 대상이 `FunctionStmt`든(나중에 추가될) 클래스든 동일한 `call(interpreter, arguments)` 인터페이스로 다루면, Executor의 호출 처리 코드가 대상 종류에 상관없이 하나로 통일된다. |
| Strategy Pattern | 위 callable 인터페이스를 함수/클래스/내장 함수 등 서로 다른 구현으로 갈아끼우는 것 자체가 Strategy 패턴의 전형적인 형태다. |

## 구현 항목 요약

| 분류 | 개수 |
| --- | -: |
| Node (Stmt) | 2개 |
| Node (Expr) | 1개 |
| 기능 | 5개 |
| 오류 검사 | 4개 |
| 적용 후보 패턴 | 2개 |
