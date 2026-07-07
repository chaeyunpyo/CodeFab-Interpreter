"""변수 저장소.

scope 스택을 사용하여 블록 스코프를 지원한다.

Public API:
    storage.define(name, value)  - 현재 스코프에 변수 선언 (VarDeclStmt 용)
    storage.set(name, value)     - 스코프 체인을 따라 기존 변수 업데이트 (AssignExpr 용)
    storage.get(name)            - 스코프 체인에서 변수 읽기
    storage.exists(name)         - 변수 존재 여부 확인
    storage.push_scope()         - 새 블록 스코프 진입 (BlockStmt 진입 시)
    storage.pop_scope()          - 현재 블록 스코프 종료 (BlockStmt 종료 시)
"""

from typing import Any, Dict, List

from .errors import UndefinedVariableError


class Storage:
    def __init__(self) -> None:
        # 인덱스 0이 전역 스코프, -1이 현재 가장 안쪽 스코프
        self._scopes: List[Dict[str, Any]] = [{}]

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
