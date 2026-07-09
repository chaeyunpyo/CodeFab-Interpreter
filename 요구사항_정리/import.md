# [추가] import 구현 항목

## Node 정의

기존 `nodes/stmt.py`에 아래 타입을 추가한다.

| 클래스 | 필드 | 설명 | 예시 |
| --- | --- | --- | --- |
| `ImportStmt` | `keyword: Token`, `path: Token`, `alias: Token` | import문. path는 경로 자리에 항상 문자열 리터럴만 허용되므로 STRING 토큰이고, path.literal이 실제 경로 문자열 | `import "sum.txt" alias sum;` |

## 구현해야 할 기능

| 분류 | 항목 | 설명 | 예시 |
| --- | --- | --- | --- |
| import 문법 | import ~ alias | 파일 경로와 별칭을 지정해서 불러옴 | `import "sum.txt" alias sum;` |
| 사용 | alias로 접근 | 불러온 파일의 함수/변수를 별칭으로 접근 | `sum.add(1, 2);` |

## 구현해야 할 세부 규칙

| 분류 | 항목 | 설명 |
| --- | --- | --- |
| 위치 제한 | 반복문 내 사용 금지 | import문은 어디서든 가능하지만 반복문 내부에서는 불가 |
| 파일 내용 제한 | 선언만 허용 | import 대상 파일에는 import/함수 선언/전역 변수 선언만 허용 (그 외 처리는 팀 자율) |
| 경로 제한 | 문자열 리터럴만 허용 | 파일 경로 자리에는 문자열 리터럴만 올 수 있음 |
| 순환 참조 | 순환 import 금지 | a.txt가 b.txt를, b.txt가 다시 a.txt를 import하면 오류 |
| 스코프 | scope 한정 적용 | import된 선언은 import문이 실행된 현재 scope에만 적용됨 |
| 스코프 | 상위 중복 import 금지 | 상위 level에서 이미 import한 파일을 하위에서 다시 import 불가 |
| 스코프 | 동일 scope 중복 import 금지 | 같은 scope 안에서 같은 파일을 두 번 import 불가 |

## 구현해야 할 오류 검사

| 분류 | 항목 |
| --- | --- |
| 정적 오류 | import 문법 오류 |
| 정적/런타임 오류 | import 대상 파일 없음 |
| 정적 오류 | 같은 scope 내 중복 import |
| 정적 오류 | 순환 import |
| 정적 오류 | alias name 충돌 |
| 정적 오류 | 반복문 내 import문 호출 |

## 구현 현황 (Checker)

정적 오류 6개 중 Checker 담당 3개와 세부 규칙의 "상위 중복 import 금지"는
`src/checker.py`에 구현 완료됨 (테스트: `tests/test_checker/test_checker_import.py`).
나머지 3개(import 문법 오류, 파일 없음, 순환 import)는 Assembler 담당이라
여기 포함하지 않는다.

| 항목 | 구현된 메시지 |
| --- | --- |
| 같은 scope 내 중복 import | `Already imported this file in this scope.` |
| 상위 level 중복 import 금지 | `Already imported this file in an enclosing scope.` |
| alias name 충돌 | `Already a variable with this name in this scope.` |
| 반복문 내 import문 호출 | `Can't use import statement inside a loop.` |

Node 정의(`ImportStmt`)는 추가됐지만, 실제 파일 읽기·조립·alias 접근
실행은 Assembler/Executor 쪽 구현이 필요해서 아직 미착수 상태다.

## 적용 가능한 디자인 패턴 (가산점)

> 디자인 패턴은 여러 곳에서 발생될 수 있는 문제를 해결하는 일반화된
> 모범 사례입니다. GoF 디자인 패턴을 사용하면 약간의 추가 점수가
> 주어집니다 (`유의사항.md` 참고).

| 패턴 | 적용 지점 |
| --- | --- |
| Singleton/Registry 유사 | 같은 파일을 여러 번 import해도 다시 읽고 파싱하지 않도록, 파일 경로별로 조립 결과를 캐싱하는 레지스트리를 둔다. 이 캐시는 "지금 조립 중인 파일 목록"으로도 써서 순환 import를 감지하는 용도까지 겸할 수 있다. |
| Facade Pattern | `import "sum.txt" alias sum;` 한 줄 뒤에서 파일 읽기 + 토큰화 + 파싱 + 캐시 조회라는 여러 단계를 감추고 하나의 진입점으로 노출하는 구조. |

## 구현 항목 요약

| 분류 | 개수 |
| --- | -: |
| 기능 | 2개 |
| 세부 규칙 | 7개 |
| 오류 검사 | 6개 |
| 적용 후보 패턴 | 2개 |
