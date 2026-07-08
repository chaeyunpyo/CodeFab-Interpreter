"""Expression(값을 만드는 노드) 정의. (PDF Chapter 02-2, p.42-43)

Expr는 실행하면 값 하나로 평가(evaluate)된다는 공통점을 갖는다.
Expr 내부에 Stmt를 Child로 두는 것은 허용하지 않는다. (PDF p.31, p.46)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List

from .ast_node import AstNode
from .tokens import Token


class Expr(AstNode):
    """모든 Expression 노드의 최상위 타입. (PDF p.13)"""


@dataclass
class LiteralExpr(Expr):
    """리터럴 값을 그대로 담는 노드. Child가 없는 단일 구조. (PDF p.33, p.35)"""

    value: Any


@dataclass
class VariableExpr(Expr):
    """변수의 이름(식별자)을 나타내는 노드. (PDF p.34)"""

    name: Token


@dataclass
class AssignExpr(Expr):
    """변수에 값을 대입하는 노드. 예: a = 3, x = a + b (PDF p.37, p.39)"""

    name: Token
    value: Expr


@dataclass
class UnaryExpr(Expr):
    """값을 1개만 사용하는 연산자 노드. 예: -a, !a (PDF p.36)"""

    operator: Token
    right: Expr


@dataclass
class BinaryExpr(Expr):
    """값을 2개 사용하는 연산자 노드. 예: a+b, a*b, a>b (PDF p.38, p.40)"""

    left: Expr
    operator: Token
    right: Expr


@dataclass
class LogicalExpr(Expr):
    """논리 연산자 노드. 예: a and b (PDF p.42-43)

    Binary와 별도 타입으로 둔 이유: and/or는 단축 평가(short-circuit)가
    필요해 Executor가 Binary와 다르게 처리해야 하기 때문.
    """

    left: Expr
    operator: Token
    right: Expr


@dataclass
class GroupingExpr(Expr):
    """괄호로 묶인 표현식. 예: (a + b) (PDF p.41)"""

    expression: Expr


@dataclass
class CallExpr(Expr):
    """함수 호출 표현식. 예: add(1, 2) (요구사항_정리/function.md)

    callee는 호출 대상(보통 VariableExpr), paren은 오류 위치(줄 번호)
    표시용으로 호출의 여는 괄호 토큰을 담는다.
    """

    callee: Expr
    paren: Token
    arguments: List[Expr] = field(default_factory=list)


@dataclass
class ThisExpr(Expr):
    """메서드 내부에서 자기 인스턴스를 가리키는 표현식. 예: this.name (요구사항_정리/class.md)"""

    keyword: Token


@dataclass
class SuperExpr(Expr):
    """부모 클래스의 메서드를 가리키는 표현식. 예: super.move (요구사항_정리/class.md)

    keyword는 오류 위치(줄 번호) 표시용 super 토큰, method는 호출할
    부모 메서드 이름 토큰이다.
    """

    keyword: Token
    method: Token
