# 처리 단위(Unit) 종류

소스 코드 한 줄이 실행되기까지 거치는 단계와, 각 단계를 담당하는 Unit을 정리한다.

```
소스 코드(str)
  -> Tokenizer   -> Token 목록
  -> Assembler   -> Stmt 트리(AST)
  -> Checker     -> 실행 전 의미 오류(정적 오류) 검사
  -> Executor    -> 실제 실행, Storage에 변수 저장/조회
```

| 분류    | 클래스                | 설명                                                     | 위치                                    |
| ----- | ------------------ | ------------------------------------------------------ | ------------------------------------- |
| 어휘 분석 | `Tokenizer`        | 소스 코드 문자열을 Token 목록으로 변환                                | `src/assembler/_tokenizer.py`         |
| 구문 분석 | `Assembler`        | Tokenizer -> AstBuilder 순서로 이어서 Stmt 트리(AST)를 조립         | `src/assembler/_assembler.py`         |
| 구문 분석 | `AstBuilder`       | 파일 끝까지 문장을 반복해서 읽는 최상위 루프만 담당하고, 실제 문법은 아래 두 파서에 위임     | `src/assembler/_ast_builder.py`       |
| 구문 분석 | `StatementParser`  | 문장/선언(if, for, print, var, block 등) 문법을 파싱               | `src/assembler/_statement_parser.py`  |
| 구문 분석 | `ExpressionParser` | 표현식 문법을 대입부터 primary까지 우선순위 순서(precedence climbing)로 파싱 | `src/assembler/_expression_parser.py` |
| 구문 분석 | `TokenStream`      | Token 목록 위를 이동하는 커서. 파서들은 이 커서를 통해서만 토큰을 읽음             | `src/assembler/_token_stream.py`      |
| 의미 분석 | `CheckerUnit`      | Stmt 트리를 DFS로 순회하며 실행 전 의미 오류(정적 오류)를 검사                | `src/checker.py`                      |
| 실행    | `Executor`         | Stmt 실행/Expr 평가 함수(`execute`, `evaluate`)를 제공           | `src/executor/_stmt.py`, `src/executor/_expr.py` |
| 저장소   | `Storage`          | 변수 스코프(전역/블록)를 스택으로 관리하며 값을 저장·조회                       | `src/executor/_storage.py`            |

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
| 구문 분석 | 5개 |
| 의미 분석 | 1개 |
| 실행    | 1개 |
| 저장소   | 1개 |
