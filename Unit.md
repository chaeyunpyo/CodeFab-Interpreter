# 처리 단위(Unit) 종류

소스 코드 한 줄이 실행되기까지 거치는 단계와, 각 단계를 담당하는 Unit을 정리한다.

```
소스 코드(str)
  -> Tokenizer   -> Token 목록
  -> Assembler   -> Stmt 트리(AST)
  -> Checker     -> 실행 전 의미 오류(정적 오류) 검사
  -> Executor    -> 실제 실행, Storage에 변수 저장/조회
```

| 분류    | 클래스              | 설명                                          | 위치                                  |
| ----- | ---------------- | ------------------------------------------- | ----------------------------------- |
| 어휘 분석 | `Tokenizer`      | 소스 코드 문자열을 Token 목록으로 변환                     | `src/tokenizer.py`                  |
| 구문 분석 | `Assembler`      | Tokenizer 결과를 받아 AstBuilder로 Stmt 트리(AST)를 조립 | `src/assembler.py`                  |
| 구문 분석 | `AstBuilder`     | Token 목록을 재귀 하강 파싱하여 실제 Stmt/Expr 트리를 생성      | `src/ast_builder.py`                |
| 의미 분석 | `CheckerUnit`    | Stmt 트리를 DFS로 순회하며 실행 전 의미 오류(정적 오류)를 검사      | `src/checker.py`                    |
| 실행    | `Executor`       | Stmt/Expr 트리를 실제로 실행(평가)해서 결과를 만듦            | `src/executor.py`                   |
| 저장소   | `Storage`        | 변수 스코프(전역/블록)를 스택으로 관리하며 값을 저장·조회             | `src/storage.py`                    |

## Checker Unit이 검출하는 오류

| 분류            | 메시지                                                | 예시                       |
| ------------- | -------------------------------------------------- | ------------------------ |
| 변수 중복 선언      | `Already a variable with this name in this scope.` | `{ var a = 1; var a = 2; }` |
| 초기화식 자기 참조    | `Can't read local variable in initializer.`        | `{ var a = a; }`         |

자세한 내용은 `checker_summary.txt` 참고.

## Executor Unit이 검출하는 오류

| 분류        | 예외 클래스             | 예시             |
| --------- | ------------------ | -------------- |
| 타입 불일치    | `TypeMismatchError` | `3 - "hello"`  |
| 0으로 나누기   | `DivideByZeroError` | `3 / 0`        |
| 정의되지 않은 변수 | `UndefinedVariableError` (Storage) | 선언 안 된 변수 참조 |

## 처리 단위 요약

| 분류    | 개수 |
| ----- | -: |
| 어휘 분석 | 1개 |
| 구문 분석 | 2개 |
| 의미 분석 | 1개 |
| 실행    | 1개 |
| 저장소   | 1개 |
