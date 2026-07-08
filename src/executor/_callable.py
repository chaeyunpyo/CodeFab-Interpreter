"""호출 가능한 값들의 공통 인터페이스. (Command/Strategy 패턴, 요구사항_정리/function.md)

CallExpr는 호출 대상이 무엇인지(Function, 이후 추가될 class의 생성자/
바운드 메서드 등) 몰라도 이 인터페이스(arity/call)만으로 호출을 처리한다.
새 호출 가능 타입이 늘어나도 Executor의 CallExpr 처리 코드는 바뀌지 않는다.
"""

from abc import ABC, abstractmethod
from typing import Any, List

from ._storage import Storage


class LoxCallable(ABC):
    @abstractmethod
    def arity(self) -> int:
        """선언된 파라미터 개수. ArityMismatchError 검사에 사용한다."""

    @abstractmethod
    def call(self, storage: Storage, arguments: List[Any]) -> Any:
        """실제 호출을 수행하고 반환값을 돌려준다."""
