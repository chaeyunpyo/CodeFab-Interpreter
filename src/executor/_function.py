"""함수를 값으로 다루기 위한 래퍼. (요구사항_정리/function.md)

FunctionStmt(선언) 자체를 저장소에 담는 대신, 이 값 하나로 감싸서 다룬다.
LoxCallable을 구현하므로 CallExpr는 이 클래스의 내부 구조(params/body)를
몰라도 arity()/call()만으로 호출할 수 있다 (Command/Strategy 패턴).

class 기능에서는 메서드도 FunctionStmt를 그대로 재사용해 이 클래스로
감싼다. owner_class/bound_instance는 메서드로 쓰일 때만 채워진다
(요구사항_정리/class.md):
    - owner_class: 이 메서드가 선언된 클래스. ClassStmt 실행 시 한 번만
      박아두므로, 상속받은 메서드를 몇 단계 자식이 호출하든 super는
      항상 이 값을 기준으로 부모를 찾을 수 있다 (다단계 상속 대응).
    - bound_instance: bind()로 채워지는, this가 가리킬 인스턴스.
Storage에 클로저가 없어(호출마다 스코프가 초기화됨) this/__class__를
매 호출 시점에 명시적으로 스코프에 심어주는 방식으로 대신한다.
"""

from dataclasses import dataclass, replace
from typing import Any, List, Optional

from nodes import FunctionStmt
from ._callable import LoxCallable
from ._storage import Storage


@dataclass
class Function(LoxCallable):
    declaration: FunctionStmt
    owner_class: Optional[Any] = None
    bound_instance: Optional[Any] = None

    def bind(self, instance: Any) -> "Function":
        """this가 instance를 가리키도록 묶은 새 Function을 반환한다 (요구사항_정리/class.md)."""
        return replace(self, bound_instance=instance)

    def arity(self) -> int:
        return len(self.declaration.params)

    def call(self, storage: Storage, arguments: List[Any]) -> Any:
        # _stmt/_signals와의 순환 import를 피하기 위해 호출 시점에 지연 import한다.
        from ._stmt import execute
        from ._signals import ReturnSignal

        storage.push_call_frame()
        try:
            if self.bound_instance is not None:
                storage.define("this", self.bound_instance)
                storage.define("__class__", self.owner_class)
            for param, argument in zip(self.declaration.params, arguments):
                storage.define(param.lexeme, argument)
            try:
                for body_stmt in self.declaration.body:
                    execute(body_stmt, storage)
            except ReturnSignal as signal:
                return signal.value
            return None
        finally:
            storage.pop_call_frame()
