# Token 종류 요약

| 분류        | 개수 | 설명                                                                |
| --------- |---:|-------------------------------------------------------------------|
| 괄호        | 6개 | `(`, `)`, `{`, `}`, `[`, `]`                                       |
| 구분자       | 1개 | `;`                                                               |
| 산술 연산자    | 4개 | `+`, `-`, `*`, `/`                                                |
| 대입/비교 연산자 | 8개 | `=`, `>`, `<`, `==`, `>=`, `<=`, `=<`, `=>`                        |
| 단항 연산자    | 2개 | `!`, `!=`                                                          |
| 예약어       | 17개 | `var`, `if`, `else`, `for`, `print`, `true`, `false`, `and`, `or`, `Func`, `Class`, `return`, `This`, `Super`, `instanceof`, `import`, `alias` |
| 식별자       | 1개 | 변수 또는 함수 이름                                                       |
| 리터럴       | 2개 | 숫자(`NUMBER`), 문자열(`STRING`)                                       |
| 종료 토큰     | 1개 | `EOF`                                                             |

## 총 TokenType

* **총 42개**

> 추가분(`LEFT_BRACKET`/`RIGHT_BRACKET`, `FUNC`~`ALIAS`)은 function/class/정적 배열/import 요구사항 기준. 대소문자는 참고 문서 예시(`Func`, `Class`, `This`, `Super`, `return`, `instanceof`, `import`, `alias`)를 그대로 따름 — 팀에서 확정 필요.





| 분류 | TokenType     | 예시               | 설명          |
|------|---------------|------------------|-------------|
| 괄호 | LEFT_PAREN    | (                | 여는 소괄호      |
| 괄호 | RIGHT_PAREN   | )                | 닫는 소괄호      |
| 괄호 | LEFT_BRACE    | {                | 여는 중괄호      |
| 괄호 | RIGHT_BRACE   | }                | 닫는 중괄호      |
| 괄호 | LEFT_BRACKET  | [                | 배열 인덱스 시작 (추가) |
| 괄호 | RIGHT_BRACKET | ]                | 배열 인덱스 종료 (추가) |
| 구분자 | SEMICOLON     | ;                | 문장 종료       |
| 산술 연산자 | PLUS          | +                | 덧셈          |
| 산술 연산자 | MINUS         | -                | 뺄셈          |
| 산술 연산자 | STAR          | *                | 곱셈          |
| 산술 연산자 | SLASH         | /                | 나눗셈         |
| 대입/비교 연산자 | EQUAL         | =                | 대입 연산자      |
| 대입/비교 연산자 | GREATER       | >                | 크다 비교       |
| 대입/비교 연산자 | LESS          | <                | 작다 비교       |
| 대입/비교 연산자 | EQUAL_EQUAL   | ==               | 같은지 비교      |
| 대입/비교 연산자 | GREATER_EQUAL | >=               | 이상인지 비교     |
| 대입/비교 연산자 | LESS_EQUAL    | <=               | 이하인지 비교     |
| 대입/비교 연산자 | EQUAL_LESS    | =<               | (=< 형태) 이하인지 비교 |
| 대입/비교 연산자 | EQUAL_GREATER | =>               | (=> 형태) 이상인지 비교 |
| 단항 연산자 | BANG          | !                | 논리 부정(NOT)   |
| 단항 연산자 | BANG_EQUAL    | !=               | 같지 않은지 비교   |
| 예약어 | VAR           | var              | 변수 선언       |
| 예약어 | IF            | if               | 조건문         |
| 예약어 | ELSE          | else             | 조건문 분기      |
| 예약어 | FOR           | for              | 반복문         |
| 예약어 | PRINT         | print            | 출력          |
| 예약어 | TRUE          | true             | Boolean 참   |
| 예약어 | FALSE         | false            | Boolean 거짓  |
| 예약어 | AND           | and              | 논리 AND      |
| 예약어 | OR            | or               | 논리 OR       |
| 예약어 | FUNC          | Func             | 함수 선언 (추가)  |
| 예약어 | CLASS         | Class            | 클래스 선언 (추가) |
| 예약어 | RETURN        | return           | 함수 반환 (추가)  |
| 예약어 | THIS          | This             | 자기 인스턴스 참조 (추가) |
| 예약어 | SUPER         | Super            | 부모 클래스 참조 (추가) |
| 예약어 | INSTANCEOF    | instanceof       | 인스턴스 여부 확인 연산자 (추가) |
| 예약어 | IMPORT        | import           | 파일 import (추가) |
| 예약어 | ALIAS         | alias            | import 별칭 (추가) |
| 식별자 | IDENTIFIER    | a, num, x        | 변수 또는 함수 이름 |
| 리터럴 | NUMBER        | 3, 100, 3.141592 | 숫자 값        |
| 리터럴 | STRING        | "hello"          | 문자열 값       |
| 종료 | EOF           | EOF              | 입력의 끝       |
