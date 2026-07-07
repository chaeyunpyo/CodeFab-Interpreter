# 처리 단위(Unit) 종류

소스 코드 한 줄이 실행되기까지 거치는 단계와, 각 단계를 담당하는 Unit을 정리한다.

```
소스 코드(str)
  -> Pipeline
       -> Assembler   -> Tokenizer + AstBuilder로 Stmt 트리(AST) 조립
       -> CheckerUnit -> 실행 전 의미 오류(정적 오류) 검사
       -> Executor    -> 문제 없으면 실제 실행, Storage에 변수 저장/조회
```

`src/pipeline.py`의 `Pipeline`이 이 세 Unit을 순서대로 엮어서 실행하고,
`src/shell.py`가 사용자로부터 코드를 입력받아 `Pipeline`에 넘기는 REPL이다.

| 분류    | 클래스           | 설명                                              | 위치                          |
| ----- | ------------- | ----------------------------------------------- | --------------------------- |
| 진입점   | `Pipeline`    | Assembler -> CheckerUnit -> Executor를 순서대로 실행    | `src/pipeline.py`            |
| 진입점   | `run_shell`   | 사용자 입력을 받아 Pipeline에 넘기는 대화형 셸(REPL)             | `src/shell.py`               |
| 어휘 분석 | `Tokenizer`   | 소스 코드 문자열을 Token 목록으로 변환                        | `src/assembler/_tokenizer.py` |
| 구문 분석 | `AstBuilder`  | Token 목록을 재귀 하강 파싱하여 Stmt/Expr 트리를 생성            | `src/assembler/_ast_builder.py` |
| 구문 분석 | `Assembler`   | Tokenizer + AstBuilder를 묶어서 소스 -> Stmt 트리(AST) 조립 | `src/assembler/_assembler.py` |
| 의미 분석 | `CheckerUnit` | Stmt 트리를 DFS로 순회하며 실행 전 의미 오류(정적 오류)를 검사         | `src/checker.py`             |
| 실행    | `Executor`    | Stmt/Expr 트리를 실제로 실행(평가)해서 결과를 만듦               | `src/executor/_stmt.py`, `_expr.py` |
| 저장소   | `Storage`     | 변수 스코프(전역/블록)를 스택으로 관리하며 값을 저장·조회                | `src/executor/_storage.py`   |
| 공통    | `SourceError` | Assembler/Checker/Executor 오류가 공통으로 상속하는 베이스 (Unit, 줄 번호) | `src/source_error.py`        |

`Assembler`, `Executor`는 각각 `assembler/`, `executor/` 패키지의
`__init__.py`가 내부 모듈(`_assembler.py`, `_stmt.py` 등)을 묶어서
바깥으로 노출하는 구조다. `Storage`는 `executor` 패키지 안에만 있고
(`executor/_storage.py`), `executor/__init__.py`가 공개 API로 내보내므로
Pipeline은 `from executor import Storage`로 가져다 쓴다.

## 오류 공통 형식: SourceError

Assembler, Checker, Executor가 만드는 오류는 전부 `source_error.SourceError`를
상속한다. 클래스마다 `UNIT` 값만 다르고, 나머지(message, token, line,
문자열 표현)는 공통이다.

    print(error)
    -> "[Assembler] Line 1: Expected ';' after variable declaration"
    -> "[Checker] Line 5: Already a variable with this name in this scope."
    -> "[Executor] Line 1: 0으로 나눌 수 없습니다."

이 덕분에 `Pipeline.run()`은 오류가 Assembler/Checker/Executor 중
어디서 났는지 따로 분기하지 않고, 셋 다 그냥 오류 리스트로 반환하면 된다.

## Assembler Unit이 검출하는 오류

| 분류              | 예외 클래스                       | 예시            |
| --------------- | ---------------------------- | ------------- |
| 해석할 수 없는 문자     | `TokenizerError`              | `var a = @;`  |
| 필요한 토큰 누락       | `MissingTokenError`           | `var a = 3`（세미콜론 없음） |
| 해석할 수 없는 토큰     | `UnexpectedTokenError`        | `*3;`         |
| 잘못된 대입 대상       | `InvalidAssignmentTargetError` | `3 = 5;`      |

모두 `src/assembler/errors.py`에 정의되어 있고, `AssemblerError`(공통
상위 타입)를 거쳐 `SourceError`를 상속한다.

## Checker Unit이 검출하는 오류

| 분류         | 메시지                                                 | 예시                          |
| ---------- | --------------------------------------------------- | --------------------------- |
| 변수 중복 선언   | `Already a variable with this name in this scope.`  | `{ var a = 1; var a = 2; }` |
| 초기화식 자기 참조 | `Can't read local variable in initializer.`         | `{ var a = a; }`            |

자세한 내용은 `checker_summary.txt` 참고.

## Executor Unit이 검출하는 오류

| 분류         | 예외 클래스                | 예시            |
| ---------- | --------------------- | ------------- |
| 타입 불일치     | `TypeMismatchError`   | `3 - "hello"` |
| 0으로 나누기    | `DivideByZeroError`   | `3 / 0`       |
| 정의되지 않은 변수 | `UndefinedVariableError` | `print x;` |

모두 `src/executor/errors.py`에 정의되어 있고, `ExecutionError`(공통
상위 타입)를 거쳐 `SourceError`를 상속한다.

## 처리 단위 요약

| 분류    | 개수 |
| ----- | -: |
| 진입점   | 2개 |
| 어휘 분석 | 1개 |
| 구문 분석 | 2개 |
| 의미 분석 | 1개 |
| 실행    | 1개 |
| 저장소   | 1개 |
| 공통    | 1개 |
