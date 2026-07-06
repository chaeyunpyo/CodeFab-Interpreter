"""Statement(행동을 수행하는 노드) 정의. (PDF Chapter 02-3, p.47-52)

Stmt는 값을 반환하지 않고 동작을 수행한다는 공통점을 갖는다.
문법 Tree의 루트(최상위)는 항상 Stmt이다. (PDF p.46)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from expr import Expr
from tokens import Token


class Stmt:
    """모든 Statement 노드의 최상위 타입. (PDF p.13)"""


@dataclass
class ExpressionStmt(Stmt):
    """Expr 하나를 감싸서 실행 가능한 문장으로 만드는 Wrapper.
    예: a + 1; (PDF p.48, p.52)
    """

    expression: Expr


@dataclass
class PrintStmt(Stmt):
    """값을 평가해서 출력하는 문장. 예: print a; (PDF p.52, p.77)"""

    expression: Expr


@dataclass
class VarDeclStmt(Stmt):
    """변수 선언문. 예: var a = 3; (PDF p.51, p.57)

    initializer가 없는 선언(var a;)을 허용한다면 None이 된다.
    """

    name: Token
    initializer: Optional[Expr] = None


@dataclass
class BlockStmt(Stmt):
    """{ }로 감싼 지역 스코프.

    진입 시 새 로컬 변수 저장소가 생성되고, 종료 시 소멸한다.
    (PDF p.50, p.82-83)
    """

    statements: List[Stmt] = field(default_factory=list)


@dataclass
class IfStmt(Stmt):
    """조건에 따라 실행을 분기하는 문장. else_branch는 없을 수 있다.
    (PDF p.48-49)
    """

    condition: Expr
    then_branch: Stmt
    else_branch: Optional[Stmt] = None


@dataclass
class ForStmt(Stmt):
    """반복문. initializer/condition/increment는 생략 가능하다.
    (PDF p.80-81)
    """

    initializer: Optional[Stmt]
    condition: Optional[Expr]
    increment: Optional[Expr]
    body: Stmt
