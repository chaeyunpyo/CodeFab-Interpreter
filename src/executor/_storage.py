"""변수 저장소.

scope 스택을 사용하여 블록 스코프를 지원한다.

Public API:
    storage.define(name, value)  - 현재 스코프에 변수 선언 (VarDeclStmt 용)
    storage.set(name, value)     - 스코프 체인을 따라 기존 변수 업데이트 (AssignExpr 용)
    storage.get(name)            - 스코프 체인에서 변수 읽기
    storage.exists(name)         - 변수 존재 여부 확인
    storage.push_scope()         - 새 블록 스코프 진입 (BlockStmt 진입 시)
    storage.pop_scope()          - 현재 블록 스코프 종료 (BlockStmt 종료 시)
    storage.push_call_frame()    - 함수 호출 진입 (CallExpr 실행 시)
    storage.pop_call_frame()     - 함수 호출 종료 (CallExpr 실행 종료 시)
    storage.current_scope_items() - 현재(가장 안쪽) 스코프의 변수 목록 조회 (디버그 모드 inspect 용)
"""

from typing import Any, Dict, List

from .errors import UndefinedVariableError


class Storage:
    def __init__(self) -> None:
        # 인덱스 0이 전역 스코프, -1이 현재 가장 안쪽 스코프
        from ._array import ARRAY_BUILTIN
        self._scopes: List[Dict[str, Any]] = [{"Array": ARRAY_BUILTIN}]
        # 함수 호출 진입 시 호출부의 지역 스코프 목록을 잠시 보관해두는 스택.
        self._call_stack: List[List[Dict[str, Any]]] = []

    # ── 변수 선언 ─────────────────────────────────────────────────────────────

    def define(self, name: str, value: Any) -> None:
        """현재(가장 안쪽) 스코프에 변수를 선언한다.

        이미 같은 스코프에 존재하면 덮어쓴다 (재선언 허용).
        VarDeclStmt 실행 시 사용한다.
        """
        self._scopes[-1][name] = value

    # ── 변수 업데이트 ─────────────────────────────────────────────────────────

    def set(self, name: str, value: Any) -> None:
        """스코프 체인을 안쪽에서 바깥쪽으로 탐색하여 기존 변수를 업데이트한다.

        변수가 어떤 스코프에도 없으면 UndefinedVariableError를 발생시킨다.
        AssignExpr 실행 시 사용한다.
        """
        for scope in reversed(self._scopes):
            if name in scope:
                scope[name] = value
                return
        raise UndefinedVariableError(name)

    # ── 변수 읽기 ─────────────────────────────────────────────────────────────

    def get(self, name: str) -> Any:
        """스코프 체인을 안쪽에서 바깥쪽으로 탐색하여 변수 값을 반환한다.

        변수가 없으면 UndefinedVariableError를 발생시킨다.
        """
        for scope in reversed(self._scopes):
            if name in scope:
                return scope[name]
        raise UndefinedVariableError(name)

    # ── 존재 여부 ─────────────────────────────────────────────────────────────

    def exists(self, name: str) -> bool:
        """스코프 체인 어딘가에 변수가 정의되어 있으면 True를 반환한다."""
        return any(name in scope for scope in self._scopes)

    def current_scope_items(self) -> Dict[str, Any]:
        """현재(가장 안쪽) 스코프에 선언된 변수들을 이름->값 딕셔너리 사본으로 반환한다.

        디버그 모드의 inspect 명령용 (PDF: "현재 스코프의 모든 변수와 값 출력").
        """
        return dict(self._scopes[-1])

    # ── 스코프 관리 ───────────────────────────────────────────────────────────

    def push_scope(self) -> None:
        """새로운 블록 스코프를 스택에 추가한다 (BlockStmt 진입 시 호출)."""
        self._scopes.append({})

    def pop_scope(self) -> None:
        """현재 블록 스코프를 스택에서 제거한다 (BlockStmt 종료 시 호출).

        전역 스코프를 제거하려 하면 RuntimeError를 발생시킨다.
        """
        if len(self._scopes) <= 1:
            raise RuntimeError("Cannot pop the global scope")
        self._scopes.pop()

    # ── 함수 호출 프레임 관리 ─────────────────────────────────────────────────────

    def push_call_frame(self) -> None:
        """함수 호출에 진입한다 (CallExpr 실행 시 호출).

        호출부의 지역 스코프 체인은 함수 본문에서 보이면 안 되므로, 현재
        스코프 목록을 스택에 스냅샷으로 저장해두고 전역 스코프만 남긴 뒤
        그 위에 새 프레임(파라미터용 스코프)을 하나 쌓는다.
        """
        self._call_stack.append(self._scopes)
        self._scopes = [self._scopes[0], {}]

    def pop_call_frame(self) -> None:
        """함수 호출을 종료하고 호출부의 스코프 체인을 복원한다."""
        self._scopes = self._call_stack.pop()
