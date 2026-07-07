"""Assembler: 소스 코드를 Token으로 분해한 뒤, AstBuilder로 Stmt 트리(AST)를 조립한다.

Public API:
    Assembler                  - 소스 코드 문자열을 받아 AST를 조립하는 진입점
    AssemblerError              - Assembler Unit 오류의 최상위 타입
    TokenizerError              - Token으로 분해할 수 없는 문자를 만났을 때
    MissingTokenError           - 문법 규칙상 있어야 할 토큰이 없을 때
    UnexpectedTokenError        - 어떤 문법 규칙으로도 해석할 수 없는 토큰을 만났을 때
    InvalidAssignmentTargetError - 대입 연산자(=)의 좌변이 변수가 아닐 때
    AstBuilder                  - Token 목록을 재귀 하강 파싱하여 Stmt/Expr 트리를 생성
    Tokenizer                   - 소스 코드 문자열을 Token 목록으로 변환
"""

from .errors import (
    AssemblerError,
    InvalidAssignmentTargetError,
    MissingTokenError,
    TokenizerError,
    UnexpectedTokenError,
)
from ._assembler import Assembler
from ._ast_builder import AstBuilder
from ._tokenizer import Tokenizer

__all__ = [
    "Assembler",
    "AssemblerError",
    "TokenizerError",
    "MissingTokenError",
    "UnexpectedTokenError",
    "InvalidAssignmentTargetError",
    "AstBuilder",
    "Tokenizer",
]
