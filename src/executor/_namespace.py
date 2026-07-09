"""import된 모듈의 네임스페이스. (요구사항_정리/import.md)

`import "sum.txt" alias sum;` 실행 결과로 sum에 바인딩되는 객체.
`sum.add(1, 2)` 형태의 접근이 FieldGetExpr → get(token) 경로를 타도록
LoxInstance와 동일한 인터페이스(get)를 구현한다.

네임스페이스 자체의 필드는 외부에서 쓰기 불가 — set()이 없으므로
FieldSetExpr가 NotAnInstanceError를 올린다.
"""

from collections.abc import MutableMapping
from typing import Any, Dict, Iterable, Optional

from nodes.tokens import Token
from .errors import UndefinedPropertyError


class LiveModuleScope(MutableMapping):
    """모듈의 실제 전역 스코프 dict를 그대로 들여다보는 뷰.

    import 실행 시점의 값만 한 번 복사해두면, 이후 모듈 안 함수 호출로
    전역이 바뀌어도(예: alias.inc() 호출) alias.counter처럼 필드에 직접
    접근할 때는 그 변경이 안 보인다 - 함수는 home_storage로 module_storage를
    직접 참조하지만 네임스페이스의 필드 복사본은 그대로라서 둘이 어긋난다.
    그래서 복사 대신 이 뷰로 같은 dict를 그대로 공유한다. built-in
    이름(Array 등, import 시점에 이미 있던 이름)만 감춘다.
    """

    def __init__(self, scope: Dict[str, Any], excluded_names: Iterable[str]) -> None:
        self._scope = scope
        self._excluded_names = set(excluded_names)

    def __getitem__(self, key):
        if key in self._excluded_names:
            raise KeyError(key)
        return self._scope[key]

    def __setitem__(self, key, value):
        self._scope[key] = value

    def __delitem__(self, key):
        del self._scope[key]

    def __iter__(self):
        return (name for name in self._scope if name not in self._excluded_names)

    def __len__(self):
        return sum(1 for _ in self)


class LoxNamespace:
    """import된 모듈의 이름 공간. alias.name 접근만 허용하는 읽기 전용 컨테이너.

    fields를 넘기지 않으면(단독 생성/테스트용) 그냥 빈 dict를 새로 만든다.
    import 실행 시에는 LiveModuleScope를 넘겨서 모듈의 실제 전역 스코프를
    그대로 공유하게 한다.
    """

    def __init__(self, alias: str, fields: Optional[MutableMapping] = None) -> None:
        self.alias = alias
        self.fields: MutableMapping[str, Any] = fields if fields is not None else {}

    def get(self, name_token: Token) -> Any:
        if name_token.lexeme in self.fields:
            return self.fields[name_token.lexeme]
        raise UndefinedPropertyError(name_token.lexeme, name_token)

    def __repr__(self) -> str:
        return f"<namespace {self.alias}>"
