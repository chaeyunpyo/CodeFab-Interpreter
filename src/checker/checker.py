"""Checker Unit 정의.

Checker Unit에서 구현할 규칙 (추후 구현 예정, 현재는 기본 골격만 제공):
- 변수 중복 선언 Error 검출
- 지역 변수 초기화 시 자기 참조 Error 검출
"""

from __future__ import annotations
from typing import List
from nodes.stmt import Stmt

class CheckerUnit:
    def __init__(self, statements: List[Stmt]):
        self.statements = statements

    def check(self) -> List[Stmt]:
        """검사를 수행한다. 세부 규칙은 이후 구현한다."""
        raise NotImplementedError
