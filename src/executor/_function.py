"""함수를 값으로 다루기 위한 래퍼. (요구사항_정리/function.md)

FunctionStmt(선언) 자체를 저장소에 담는 대신, 이 값 하나로 감싸서 다룬다.
LoxCallable을 구현하므로 CallExpr는 이 클래스의 내부 구조(params/body)를
몰라도 arity()/call()만으로 호출할 수 있다 (Command/Strategy 패턴).
"""

from dataclasses import dataclass
from typing import Any, List

from nodes import FunctionStmt
from ._callable import LoxCallable
from ._storage import Storage


@dataclass
class Function(LoxCallable):
    declaration: FunctionStmt

    def arity(self) -> int:
        return len(self.declaration.params)

    def call(self, storage: Storage, arguments: List[Any]) -> Any:
        # _stmt/_signals와의 순환 import를 피하기 위해 호출 시점에 지연 import한다.
        from ._stmt import execute
        from ._signals import ReturnSignal

        storage.push_call_frame()
        try:
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
