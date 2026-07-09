# 1팀

# -팀명 : ErrorZero 
-뜻 : 코드 리뷰를 통해 오류를 사전에 예방하고, 더 높은 품질의 코드를 만들어가는 팀

-팀장 : 채윤표
-팀원 : 이용진, 김문정, 강보경, 신경섭

# 그라운드룰
1. 점심시간에는 긴급 상황이 아니면 리뷰를 요청하거나 응답하지 않는다.
2. 퇴근 30분 전에는 새로운 PR 등록을 지양한다.
3. 출근과 퇴근 시에는 서로 인사하며 원활한 소통 문화를 만든다.
4. PR 설명은 변경 목적과 내용을 포함하여 2줄 이상 작성한다.
5. PR은 큰 단위보다 작은 단위로 작성하여 자주 리뷰를 요청한다.
6. Branch는 팀에서 정한 Naming Rule을 준수하여 생성한다.
7. Self Review를 완료하고 Local에서 Conflict를 해결한 후 PR을 등록한다.
8. 취향이 아닌 근거를 바탕으로 코드만 리뷰한다.
9. LGTM을 남발하지 않고 승인 사유를 한 줄 이상 작성하며 리뷰 요청에는 반드시 응답한다.
10. Merge 전 최종 검증을 완료하고 받은 코드보다 더 좋은 코드로 남긴다.

# 개요

우리만의 문법을 가진 프로그래밍 언어(Custom Language)를 직접 만들고,
그 언어로 짠 코드를 실행해주는 인터프리터다.

# 사용법

## 실행 명령어

```bash
python main.py              # 프롬프트 모드
python main.py run <파일>    # 파일 모드
python main.py debug <파일>  # 디버그 모드
```

3가지 모드에서 쓸 수 있는 세부 명령어는 모드마다 다르다. 아래 표로
어떤 명령어가 어느 모드에서 되는지 먼저 확인하고, 자세한 설명은 각
모드 절을 참고한다.

| 명령어 | 프롬프트 모드 | 파일 모드 | 디버그 모드 | 설명 |
| --- | :-: | :-: | :-: | --- |
| 코드 한 줄 입력 | ✅ | - | - | 입력한 줄을 즉시 실행 |
| `exit` / `quit` | ✅ | - | ✅ | 세션 종료 |
| `step` | - | - | ✅ | 현재 Stmt 실행 후 다음 Stmt에서 정지 |
| `next` | - | - | ✅ | 현재 최상위 Stmt 실행 (블록 내부로 진입 X) |
| `continue` | - | - | ✅ | 다음 breakpoint까지 실행 |
| `break <줄번호>` | - | - | ✅ | 해당 줄에 breakpoint 설정 |
| `breakpoints` | - | - | ✅ | 현재 설정된 breakpoint 목록 출력 |
| `remove <줄번호>` | - | - | ✅ | breakpoint 해제 |
| `watch <변수명>` | - | - | ✅ | 해당 변수를 감시 목록에 추가 |
| `unwatch <변수명>` | - | - | ✅ | 감시 목록에서 제거 |
| `watches` | - | - | ✅ | 감시 중인 변수 목록과 값 출력 |
| `inspect` | - | - | ✅ | 현재 스코프의 모든 변수와 값 출력 (단, 로컬의 경우 해당 스코프 내에서 선언된 변수만 표기됨) |

파일 모드는 파일 하나를 통째로 실행만 하는 모드라 별도의 명령어가
없다 (파일 실행이 끝나거나 오류가 나면 바로 종료된다).

### 프롬프트 모드 (`python main.py`)

인자 없이 실행하면 코드를 한 줄씩 입력해서 바로 실행해볼 수 있다.
`exit` 또는 `quit`을 입력하면 종료된다.

```
> var a = 3;
> var b = 7;
> print a + b;
10
> exit
```

### 파일 모드 (`python main.py run <파일>`)

`.txt` 파일에 미리 작성해둔 코드를 한 번에 실행한다.

```bash
python main.py run hello.txt
```

- 파일이 없으면 오류 메시지를 출력한다.
- 실행 중 오류가 나면 오류가 발생한 줄 번호와 함께 출력하고 즉시 종료한다.

### 디버그 모드 (`python main.py debug <파일>`)

코드를 Stmt(문장) 단위로 한 줄씩 멈춰가며 실행 상태를 점검한다.
위 표의 `step`/`next`/`continue`/`break`/`watch`/`inspect` 등 명령어는
전부 이 모드에서만 쓸 수 있다.

```bash
python main.py debug hello.txt
```

## 문법 예시

**변수/출력**
```
var a = 1;
print a + 1;
```

**조건문 / 반복문** (반복문은 `for`만 지원, `while`은 없음)
```
if (a > 0) {
    print "positive";
} else {
    print "non-positive";
}

for (var i = 0; i < 3; i = i + 1) {
    print i;
}
```

**함수**
```
Func add(a, b) {
    return a + b;
}
print add(1, 2);
```

**클래스 (필드/메서드/생성자/상속/instanceof)** - 자기 인스턴스/부모 참조는
`This`/`Super`로 대문자로 시작한다 (`Func`/`Class`와 같은 규칙).
```
Class Robot {
    init(name) { This.name = name; }
    move(dist) { This.position = dist; }
}

Class SpeedRobot : Robot {
    move(dist) { Super.move(dist); print "Speeeed!"; }
}

var r = SpeedRobot("Sam");
r.move(5);
print (r instanceof Robot);   // true
```

**정적 배열**
```
var arr = Array(3);   // [null, null, null]
arr[0] = 10;
print arr[0];
```

**import** (문법/정적 검사만 구현되어 있고, 실제 파일 로드·실행은 아직
미구현이라 실행하면 `NotImplementedError`가 발생한다 - `요구사항_정리/개발_현황.md` 참고)
```
import "sum.txt" alias sum;
var total = sum.add(1, 2);
```
- import는 반복문 내부에서는 사용할 수 없다.
- 같은 scope나 상위 scope에서 이미 import한 파일은 다시 import할 수 없다.

## 기타 특이사항

- 요구되는 Python 버전은 3.14 이상이다 (`pyproject.toml`의 `requires-python` 참고).
- 테스트 실행: 저장소 루트에서 `pytest tests/` (`pytest.ini`에 `pythonpath = src` 설정되어 있어 별도 PYTHONPATH 설정 불필요).
- 언어 문법/오류 검사에 대한 상세 요구사항은 `요구사항_정리/` 디렉터리의 기능별 md 문서를 참고한다.
- 현재까지 진행 상황과 남은 작업은 `요구사항_정리/개발_현황.md`에 정리되어 있다.
- 함수는 클로저를 지원하지 않는다. 함수 호출마다 전역 스코프만 유지되고 호출부의 지역 변수 체인은 초기화된다 (`src/executor/_function.py` 참고).
- `instanceof`는 자기 자신뿐 아니라 상속 체인상의 조상 클래스에 대해서도 `true`를 반환한다.
- 전역 변수가 함수 내에서 바로 사용될 때, 저장소를 복사하여 사용하게 설계되었기 때문에 함수 밖을 나가는 순간 원래의 값으로 되돌아 간다 (함수 종료 후에도 영향을 주려면 return을 사용하여 반영).
