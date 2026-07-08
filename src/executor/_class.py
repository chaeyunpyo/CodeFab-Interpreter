"""클래스와 인스턴스. (요구사항_정리/class.md)

LoxClass는 LoxCallable을 구현해 인스턴스 생성(`Robot()`)도 함수 호출과
동일한 CallExpr 처리 경로(_expr.py의 _evaluate_call)를 그대로 타게 한다
(Command 패턴). find_method는 자기 methods에 없으면 superclass로
재귀해서 상속 체인 전체를 훑는다 (Chain of Responsibility 패턴).

Executor C가 이 파일(LoxClass/LoxInstance)과 ClassStmt 실행을 전담하고,
Executor D는 여기서 만든 API(find_method/bind/get/set)를 갖다 쓰는
ThisExpr/FieldGetExpr/FieldSetExpr/SuperExpr 평가만 _expr.py에 추가한다.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from nodes.tokens import Token
from ._callable import LoxCallable
from ._function import Function
from ._storage import Storage
from .errors import UndefinedPropertyError


@dataclass
class LoxClass(LoxCallable):
    name: str
    methods: Dict[str, Function] = field(default_factory=dict)
    superclass: Optional["LoxClass"] = None

    def find_method(self, name: str) -> Optional[Function]:
        """자기 methods에서 못 찾으면 superclass로 재귀해 상속 체인 전체를 훑는다."""
        if name in self.methods:
            return self.methods[name]
        if self.superclass is not None:
            return self.superclass.find_method(name)
        return None

    def arity(self) -> int:
        initializer = self.find_method("init")
        return initializer.arity() if initializer is not None else 0

    def call(self, storage: Storage, arguments: List[Any]) -> "LoxInstance":
        instance = LoxInstance(self)
        initializer = self.find_method("init")
        if initializer is not None:
            initializer.bind(instance).call(storage, arguments)
        return instance


@dataclass
class LoxInstance:
    klass: LoxClass
    fields: Dict[str, Any] = field(default_factory=dict)

    def get(self, name: Token) -> Any:
        """필드를 우선 찾고, 없으면 메서드를 찾아 this를 바인딩해 반환한다.

        메서드를 반환할 때 bind()로 감싸는 이유: FieldGetExpr가 CallExpr의
        callee로 쓰일 때(예: this.report()) 기존 _evaluate_call이 아무
        수정 없이 LoxCallable로 바로 호출할 수 있어야 하기 때문이다.
        """
        if name.lexeme in self.fields:
            return self.fields[name.lexeme]
        method = self.klass.find_method(name.lexeme)
        if method is not None:
            return method.bind(self)
        raise UndefinedPropertyError(name.lexeme, name)

    def set(self, name: Token, value: Any) -> None:
        """없는 필드면 새로 생성한다 (요구사항_정리/class.md)."""
        self.fields[name.lexeme] = value
