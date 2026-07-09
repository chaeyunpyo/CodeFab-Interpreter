"""import된 모듈의 네임스페이스. (요구사항_정리/import.md)

`import "sum.txt" alias sum;` 실행 결과로 sum에 바인딩되는 객체.
`sum.add(1, 2)` 형태의 접근이 FieldGetExpr → get(token) 경로를 타도록
LoxInstance와 동일한 인터페이스(get)를 구현한다.

네임스페이스 자체의 필드는 외부에서 쓰기 불가 — set()이 없으므로
FieldSetExpr가 NotAnInstanceError를 올린다.
"""

from typing import Any, Dict

from nodes.tokens import Token
from .errors import UndefinedPropertyError


class LoxNamespace:
    """import된 모듈의 이름 공간. alias.name 접근만 허용하는 읽기 전용 컨테이너."""

    def __init__(self, alias: str) -> None:
        self.alias = alias
        self.fields: Dict[str, Any] = {}

    def get(self, name_token: Token) -> Any:
        if name_token.lexeme in self.fields:
            return self.fields[name_token.lexeme]
        raise UndefinedPropertyError(name_token.lexeme, name_token)

    def __repr__(self) -> str:
        return f"<namespace {self.alias}>"
