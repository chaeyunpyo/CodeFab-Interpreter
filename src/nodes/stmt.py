"""Statement(행동을 수행하는 노드) 정의. (PDF Chapter 02-3, p.47-52)

Stmt는 값을 반환하지 않고 동작을 수행한다는 공통점을 갖는다.
문법 Tree의 루트(최상위)는 항상 Stmt이다. (PDF p.46)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .ast_node import AstNode
from .expr import Expr
from .tokens import Token


class Stmt(AstNode):
    """모든 Statement 노드의 최상위 타입. (PDF p.13)"""


@dataclass
class ExpressionStmt(Stmt):
    """Expr 하나를 감싸서 실행 가능한 문장으로 만드는 Wrapper.
    예: a + 1; (PDF p.48, p.52)
    """

    expression: Expr
    line: int = field(default=1, kw_only=True, compare=False)


@dataclass
class PrintStmt(Stmt):
    """값을 평가해서 출력하는 문장. 예: print a; (PDF p.52, p.77)"""

    expression: Expr
    line: int = field(default=1, kw_only=True, compare=False)


@dataclass
class VarDeclStmt(Stmt):
    """변수 선언문. 예: var a = 3; (PDF p.51, p.57)

    initializer가 없는 선언(var a;)을 허용한다면 None이 된다.
    """

    name: Token
    initializer: Optional[Expr] = None
    line: int = field(default=1, kw_only=True, compare=False)


@dataclass
class BlockStmt(Stmt):
    """{ }로 감싼 지역 스코프.

    진입 시 새 로컬 변수 저장소가 생성되고, 종료 시 소멸한다.
    (PDF p.50, p.82-83)
    """

    statements: List[Stmt] = field(default_factory=list)
    line: int = field(default=1, kw_only=True, compare=False)


@dataclass
class IfStmt(Stmt):
    """조건에 따라 실행을 분기하는 문장. else_branch는 없을 수 있다.
    (PDF p.48-49)
    """

    condition: Expr
    then_branch: Stmt
    else_branch: Optional[Stmt] = None
    line: int = field(default=1, kw_only=True, compare=False)


@dataclass
class ForStmt(Stmt):
    """반복문. initializer/condition/increment는 생략 가능하다.
    (PDF p.80-81)
    """

    initializer: Optional[Stmt]
    condition: Optional[Expr]
    increment: Optional[Expr]
    body: Stmt
    line: int = field(default=1, kw_only=True, compare=False)


@dataclass
class FunctionStmt(Stmt):
    """함수 선언문. 예: Func add(a, b) { ... } (요구사항_정리/function.md)"""

    name: Token
    params: List[Token] = field(default_factory=list)
    body: List[Stmt] = field(default_factory=list)
    line: int = field(default=1, kw_only=True, compare=False)


@dataclass
class ReturnStmt(Stmt):
    """return문. 예: return; / return a + b; (요구사항_정리/function.md)

    keyword는 오류 위치(줄 번호) 표시용, value가 없으면 null 반환.
    """

    keyword: Token
    value: Optional[Expr] = None
    line: int = field(default=1, kw_only=True, compare=False)


@dataclass
class ClassStmt(Stmt):
    """클래스 선언문. 예: Class SpeedRobot : Robot { ... } (요구사항_정리/class.md)

    superclass는 부모 클래스 이름을 나타내는 Expr(보통 VariableExpr)이고,
    상속이 없으면 None이다. methods는 클래스 본문의 메서드(생성자 init
    포함) 목록으로, 전부 FunctionStmt로 표현한다.
    """

    name: Token
    superclass: Optional[Expr] = None
    methods: List[FunctionStmt] = field(default_factory=list)
    line: int = field(default=1, kw_only=True, compare=False)


@dataclass
class ImportStmt(Stmt):
    """import문. 예: import "sum.txt" alias sum; (요구사항_정리/import.md)

    keyword는 오류 위치(줄 번호) 표시용 import 토큰, path는 파일 경로
    문자열 리터럴 토큰(경로 자리에는 문자열 리터럴만 허용되므로 항상
    STRING 토큰이고, path.literal이 실제 경로 문자열이다), alias는
    불러온 내용을 참조할 별칭 식별자 토큰이다.
    """

    keyword: Token
    path: Token
    alias: Token
