# Statement(AST) 종류

| 분류    | 클래스              | 설명                              | 예시                                           |
| ----- | ---------------- | ------------------------------- | -------------------------------------------- |
| 표현식 문 | `ExpressionStmt` | Expression을 실행 가능한 문장으로 감싸는 노드  | `a + 1;`                                     |
| 출력문   | `PrintStmt`      | Expression을 평가하여 출력하는 문장        | `print a;`                                   |
| 변수 선언 | `VarDeclStmt`    | 변수를 선언하고 초기값을 저장하는 문장           | `var a = 3;`                                 |
| 블록    | `BlockStmt`      | 여러 Statement를 하나의 지역 스코프로 묶는 문장 | `{ print a; var b = 1; }`                    |
| 조건문   | `IfStmt`         | 조건에 따라 실행을 분기하는 문장              | `if (a > 0) { ... } else { ... }`            |
| 반복문   | `ForStmt`        | 초기식 조건식 증감식을 이용한 반복 실행 문장       | `for (var i = 0; i < 10; i = i + 1) { ... }` |
| 함수 선언 | `FunctionStmt`   | 이름/파라미터/본문을 갖는 함수 선언 (추가)      | `Func add(a, b) { ... }`                     |
| return문 | `ReturnStmt`     | 함수 반환. 값이 없으면 null 반환 (추가)      | `return;` / `return a + b;`                  |
| 클래스 선언 | `ClassStmt`      | 이름/(선택적) 부모/메서드 목록을 갖는 클래스 선언 (추가) | `Class SpeedRobot : Robot { ... }`           |
| import문 | `ImportStmt`     | 파일 경로와 별칭을 지정해 다른 파일을 불러오는 문장 (추가) | `import "sum.txt" alias sum;`                |

## Statement 종류 요약

| 분류    | 개수 |
| ----- | -: |
| 표현식 문 | 1개 |
| 출력문   | 1개 |
| 변수 선언 | 1개 |
| 블록    | 1개 |
| 조건문   | 1개 |
| 반복문   | 1개 |
| 함수 선언 | 1개 |
| return문 | 1개 |
| 클래스 선언 | 1개 |
| import문 | 1개 |

