"""배열 런타임 객체와 빌트인 Array 함수."""

from typing import Any, List, Type

from ._callable import LoxCallable


def _parse_integer_value(value: Any, label: str, error_cls: Type[Exception], token: Any) -> int:
    """bool이 아닌 정수 숫자인지 검사하고 int로 변환한다. 타입 오류 시 error_cls를 발생시킨다."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise error_cls(f"{label}는 숫자여야 합니다. (받은 값: {value!r})", token)
    if isinstance(value, float) and not value.is_integer():
        raise error_cls(f"{label}는 정수여야 합니다. (받은 값: {value})", token)
    return int(value)


class FabArray:
    """정적(고정 크기) 배열 런타임 객체.

    생성 시 크기가 확정되고 각 칸은 None(null)으로 초기화된다.
    인덱스 범위 검사는 호출 측(_expr.py)에서 수행한다.
    """

    def __init__(self, size: int) -> None:
        self._elements: List[Any] = [None] * size

    def __len__(self) -> int:
        return len(self._elements)

    def get(self, index: int) -> Any:
        return self._elements[index]

    def set(self, index: int, value: Any) -> None:
        self._elements[index] = value


class ArrayBuiltin(LoxCallable):
    """Array(n) 내장 함수.

    LoxCallable 인터페이스를 구현하므로 CallExpr는 Function/ArrayBuiltin/
    이후 추가될 class 생성자를 구분하지 않고 arity()/call()만으로 호출한다
    (Command/Strategy 패턴, 요구사항_정리/정적배열.md).
    """

    def arity(self) -> int:
        return 1

    def call(self, storage: Any, arguments: List[Any]) -> "FabArray":
        from .errors import InvalidArraySizeError

        size_val = arguments[0]
        size = _parse_integer_value(size_val, "배열 크기", InvalidArraySizeError, None)
        if size < 0:
            raise InvalidArraySizeError(
                f"배열 크기는 0 이상이어야 합니다. (받은 값: {size})"
            )
        return FabArray(size)


ARRAY_BUILTIN = ArrayBuiltin()
