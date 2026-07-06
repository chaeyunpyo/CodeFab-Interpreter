"""Checker Unit 정의.

Checker Unit에서 구현할 규칙 (추후 구현 예정, 현재는 1단계만 제공):
- 변수 중복 선언 Error 검출
- 지역 변수 초기화 시 자기 참조 Error 검출
"""

from __future__ import annotations
from typing import List, Set
from nodes.stmt import BlockStmt, ForStmt, IfStmt, Stmt, VarDeclStmt
from nodes.tokens import Token


class CheckerError(Exception):
    def __init__(self, message: str, token: Token):
        super().__init__(message)
        self.message = message
        self.token = token


class CheckerUnit:
    def __init__(self, statements: List[Stmt]):
        self.statements = statements

    def check(self) -> List[CheckerError]:
        """DFS로 각 Stmt를 순회하며 의미상 오류를 검사해 목록으로 반환한다.

        1단계: 같은 블록 내 변수 중복 선언 검사만 수행한다.
        """
        errors: List[CheckerError] = []
        self._check_block(self.statements, errors)
        return errors

    def _check_block(self, statements: List[Stmt], errors: List[CheckerError]) -> None:
        declared: Set[str] = set()
        for stmt in statements:
            self._check_stmt(stmt, declared, errors)

    def _check_stmt(self, stmt: Stmt, declared: Set[str], errors: List[CheckerError]) -> None:
        if isinstance(stmt, VarDeclStmt):
            name = stmt.name.lexeme
            if name in declared:
                errors.append(
                    CheckerError(f"Variable '{name}' already declared in this scope.", stmt.name)
                )
            else:
                declared.add(name)
        elif isinstance(stmt, BlockStmt):
            self._check_block(stmt.statements, errors)
        elif isinstance(stmt, IfStmt):
            self._check_stmt(stmt.then_branch, declared, errors)
            if stmt.else_branch is not None:
                self._check_stmt(stmt.else_branch, declared, errors)
        elif isinstance(stmt, ForStmt):
            if stmt.initializer is not None:
                self._check_stmt(stmt.initializer, declared, errors)
            self._check_stmt(stmt.body, declared, errors)
