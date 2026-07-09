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
| 파일 내용 제한 | 선언만 허용 | import 대상 파일 최상위에는 import/함수/변수/클래스 선언만 허용 (그 외 처리는 팀 자율 — **이 팀은 오류 처리를 선택**: 선언이 아닌 문장이 있으면 `ModuleImportError`. if/block은 선언은 아니지만 import를 감싸는 용도로는 투명하게 허용) |
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
`src/checker/`에 구현 완료됨 (테스트: `tests/test_checker/test_checker_import.py`).
나머지 3개(import 문법 오류, 파일 없음, 순환 import)는 아래 "구현 현황
(Importer)"에서 다룬다.

| 항목 | 구현된 메시지 |
| --- | --- |
| 같은 scope 내 중복 import | `Already imported this file in this scope.` |
| 상위 level 중복 import 금지 | `Already imported this file in an enclosing scope.` |
| alias name 충돌 | `Already a variable with this name in this scope.` |
| 반복문 내 import문 호출 | `Can't use import statement inside a loop.` |

## 구현 현황 (Importer)

나머지 3개(import 문법 오류, 파일 없음, 순환 import)는 파일을 실제로
읽어 조립해야 확인할 수 있는데, 이 조립은 Assembler 혼자만으로는
부족하다 — import 대상 파일도 최상위 프로그램과 똑같이 Checker의
정적 검사(파라미터 중복, this/super 오용 등)를 통과해야 안전하게 쓸
수 있기 때문이다. Assembler는 Checker를 모르므로(단방향 계층), 이
둘을 함께 다루는 별도 패키지 `src/importer/`(`_importer.py`)의 `Importer`에 구현
완료됨(테스트: `tests/test_importer/test_importer.py`). `Pipeline`
(`src/pipeline.py`)은 이 로직을 감싸지 않는다 — 필요한 쪽(Executor)이
`Importer`를 직접 쓴다.

- `Importer.import_module(path)` — 파일 읽기 + Assembler(문법) +
  Checker(정적 검사)를 하나로 감춘 진입점(Facade). 대상 파일 안의
  import문도 재귀적으로 같은 방식(assemble+check)으로 처리한다.
- 경로별 캐시(Registry)를 둬서 같은 파일을 여러 번 import해도 다시
  읽거나 조립하지 않는다. 이 캐시와 별도로 "지금 import 처리 중인
  파일 목록"을 두어, 같은 경로가 처리 도중 다시 나타나면
  `CircularImportError`를 던진다(다이아몬드 형태의 중복 import는
  순환이 아니므로 정상 처리됨). 대상 파일이 없으면
  `ImportedFileNotFoundError`를 던진다.
- 대상 파일이 Assembler(문법) 또는 Checker(정적 검사)를 통과하지
  못하면 두 경우 모두 `ModuleImportError`(하나로 통일) 하나로 알린다
  — "이 파일은 그대로 쓸 수 없다"는 같은 의미라 굳이 오류 타입을
  나누지 않는다. `.errors`에 실제로 발생한 오류 목록을 담는데,
  Assembler 단계 실패면 그 `AssemblerError` 하나만 담긴 리스트가,
  Checker 단계 실패면 `CheckerUnit`이 찾은 `CheckerError` 목록이
  담긴다. 전부 `SourceError`를 상속해 다른 Unit의 오류와 동일하게
  처리할 수 있다.
- import문 안의 상대 경로는 프로세스의 작업 디렉터리가 아니라 그
  import문이 적힌 파일 기준으로 해석한다.
- 대상 파일 최상위에 선언(import/함수/변수/클래스)이 아닌 문장이 있으면
  마찬가지로 `ModuleImportError`(`CheckerError` 목록)로 알린다. if/block은
  선언은 아니지만 반복문 제외 어디서든 import를 감쌀 수 있다는 위치
  제한 규칙과 일관되게, 그 안의 내용만 재귀적으로 검사해서 투명하게
  통과시킨다.
- 대상 파일의 오류를 `AssemblerError`/`CheckerError` 그대로 흘려보내지
  않고 `ModuleImportError`로 감싸는 이유는, 그대로 흘려보내면 호출하는
  쪽(Executor)이 "최상위 프로그램 자체의 오류"와 "import한 파일의
  오류"를 타입만으로 구분할 수 없기 때문이다.

alias를 실제 스코프에 바인딩해서 실행하는 것도 Executor 쪽에 구현
완료됨(`LoxNamespace`, 테스트: `tests/test_executor/test_import_stmt.py`,
`tests/test_integration/test_imports.py`). import된 선언은 import문이
실행된 현재 scope에만 적용되고(블록 밖에서는 alias 접근 불가), 정적
바인딩 거리도 import된 모듈 자신의 실행에 그대로 적용된다.

`LoxNamespace.fields`는 import 시점 스냅샷 복사가 아니라
`LiveModuleScope`(`src/executor/_namespace.py`)로 모듈의 실제 전역
스코프 dict를 그대로 공유한다 - 그래야 `alias.inc()`처럼 모듈 안
함수 호출로 전역이 바뀐 뒤 `alias.counter`로 필드에 직접 접근해도
최신 값을 본다.

**알려진 한계**: 같은 파일을 서로 다른 import문(예: 서로 다른 파일
b.txt/c.txt가 각각 d.txt를 import)에서 여러 번 import하면, 파싱/정적
검사 결과(AST)는 Importer가 경로별로 캐싱해 재사용하지만, **실행은
import문을 만날 때마다 매번 새 Storage로 새로 실행**된다. 즉 d.txt의
최상위 코드가 import 지점마다 다시 실행되어 서로 독립된 상태(별개의
전역 변수 값)를 갖게 된다 - 진짜 모듈처럼 한 번만 실행하고 결과를
공유하려면 실행 결과(namespace)까지 경로별로 캐싱해야 하는데, 아직
미착수 상태다.

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
