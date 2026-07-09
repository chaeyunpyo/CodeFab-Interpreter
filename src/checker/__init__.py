"""Checker: Stmt 트리를 DFS로 순회하며 실행 전 의미 오류(정적 오류)를 검사한다.

자세한 설명은 요구사항_정리/Unit.md 참고.

Public API:
    CheckerUnit(statements) - check() 호출 시 오류 목록을 반환하고,
        checker.locals(정적 바인딩 거리)를 채우며, 상수 표현식을 AST에서
        직접 LiteralExpr로 접어둔다.
    CheckerError            - Checker가 만드는 오류의 공통 타입
"""

from .errors import CheckerError
from ._checker_unit import CheckerUnit

__all__ = [
    "CheckerUnit",
    "CheckerError",
]
