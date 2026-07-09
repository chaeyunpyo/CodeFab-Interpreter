"""변수 저장소.

scope 스택을 사용하여 블록 스코프를 지원한다.

Public API:
    storage.define(name, value)  - 현재 스코프에 변수 선언 (VarDeclStmt 용)
    storage.set(name, value)     - 스코프 체인을 따라 기존 변수 업데이트 (AssignExpr 용)
    storage.get(name)            - 스코프 체인에서 변수 읽기
    storage.get_resolved(node, name) - checker.locals에 거리가 기록돼 있으면
        스코프 체인을 거슬러 올라가지 않고 그 위치를 바로 읽는다 (없으면 get()과 동일,
        요구사항_정리/실행전_최적화.md 정적 바인딩).
    storage.set_resolved(node, name, value) - get_resolved()의 대입 버전 (AssignExpr 용).
    storage.exists(name)         - 변수 존재 여부 확인
    storage.push_scope()         - 새 블록 스코프 진입 (BlockStmt 진입 시)
    storage.pop_scope()          - 현재 블록 스코프 종료 (BlockStmt 종료 시)
    storage.push_call_frame()    - 함수 호출 진입 (CallExpr 실행 시)
    storage.pop_call_frame()     - 함수 호출 종료 (CallExpr 실행 종료 시)
    storage.current_scope_items() - 현재(가장 안쪽) 스코프의 변수 목록 조회 (디버그 모드 inspect 용)
    storage.global_scope_items() - 전역 스코프의 변수 목록 조회 (디버그 모드 inspect 용)
    storage.scope_depth()        - 현재 스코프 체인의 깊이 (1이면 전역 스코프뿐)
"""

from typing import Any, Dict, List, Optional

from .errors import UndefinedVariableError


class Storage:
    def __init__(self, locals: Optional[Dict[int, int]] = None) -> None:
        # 인덱스 0이 전역 스코프, -1이 현재 가장 안쪽 스코프
        from ._array import ARRAY_BUILTIN
        self._scopes: List[Dict[str, Any]] = [{"Array": ARRAY_BUILTIN}]
        # 함수 호출 진입 시 호출부의 지역 스코프 목록을 잠시 보관해두는 스택.
        self._call_stack: List[List[Dict[str, Any]]] = []
        # CheckerUnit.check() 이후의 checker.locals: id(VariableExpr/AssignExpr) -> distance.
        # 파이프라인이 채워주며(Storage 생성 시 또는 나중에 속성으로), 없는 노드는
        # 전역 참조/함수 경계를 넘는 참조로 보고 get()/set()의 전체 체인 탐색으로 처리한다.
        self.locals: Dict[int, int] = locals if locals is not None else {}

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

    # ── 정적 바인딩 조회/대입 (요구사항_정리/실행전_최적화.md) ──────────────────

    def get_resolved(self, node: Any, name: str) -> Any:
        """checker.locals에 기록된 거리로 스코프를 거슬러 올라가지 않고 바로 조회한다.

        거리가 없는 노드(전역 참조, 함수 경계를 넘는 참조)는 get()의 전체
        체인 탐색으로 그대로 처리한다 - 정적 바인딩은 지역 변수 조회에만
        적용되는 최적화이기 때문이다.
        """
        distance = self.locals.get(id(node))
        if distance is None:
            return self.get(name)
        return self._scopes[-(distance + 1)][name]

    def set_resolved(self, node: Any, name: str, value: Any) -> None:
        """get_resolved()의 대입 버전 (AssignExpr 용)."""
        distance = self.locals.get(id(node))
        if distance is None:
            self.set(name, value)
            return
        self._scopes[-(distance + 1)][name] = value

    # ── 존재 여부 ─────────────────────────────────────────────────────────────

    def exists(self, name: str) -> bool:
        """스코프 체인 어딘가에 변수가 정의되어 있으면 True를 반환한다."""
        return any(name in scope for scope in self._scopes)

    def current_scope_items(self) -> Dict[str, Any]:
        """현재(가장 안쪽) 스코프에 선언된 변수들을 이름->값 딕셔너리 사본으로 반환한다.

        디버그 모드의 inspect 명령용 (PDF: "현재 스코프의 모든 변수와 값 출력").
        내장 함수(LoxCallable)는 사용자 변수가 아니므로 제외한다.
        """
        from ._callable import LoxCallable
        return {k: v for k, v in self._scopes[-1].items() if not isinstance(v, LoxCallable)}

    def global_scope_items(self) -> Dict[str, Any]:
        """전역 스코프에 선언된 변수들을 이름->값 딕셔너리 사본으로 반환한다.

        디버그 모드의 inspect 명령용 ([전역] 표시).
        """
        return dict(self._scopes[0])

    def scope_depth(self) -> int:
        """현재 스코프 체인의 깊이를 반환한다 (1이면 현재 스코프가 곧 전역 스코프).

        디버그 모드의 inspect 명령이 로컬/전역을 구분할 때 사용한다.
        """
        return len(self._scopes)

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
        self._scopes = [dict(self._scopes[0]), {}]

    def pop_call_frame(self) -> None:
        """함수 호출을 종료하고 호출부의 스코프 체인을 복원한다."""
        self._scopes = self._call_stack.pop()
