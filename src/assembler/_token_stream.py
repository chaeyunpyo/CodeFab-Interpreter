from nodes.token_type import TokenType

from .errors import MissingTokenError


class TokenStream:
    """Token 목록 위를 이동하는 커서. 파서들은 이 커서를 통해서만 토큰을 읽는다."""

    def __init__(self, tokens):
        self._tokens = tokens
        self._current = 0

    def is_at_end(self):
        return self.current().type == TokenType.EOF

    def current(self):
        return self._tokens[self._current]

    def previous(self):
        return self._tokens[self._current - 1]

    def advance(self):
        if not self.is_at_end():
            self._current += 1
        return self.previous()

    def check(self, token_type):
        if self.is_at_end():
            return False
        return self.current().type == token_type

    def match(self, *token_types):
        """현재 토큰이 주어진 타입들 중 하나라면 커서를 한 칸 전진시키고 True를 반환한다."""
        for token_type in token_types:
            if self.check(token_type):
                self.advance()
                return True
        return False

    def consume(self, token_type, message):
        """현재 토큰이 기대한 타입이면 소비하고, 아니면 MissingTokenError를 발생시킨다."""
        if self.check(token_type):
            return self.advance()
        raise MissingTokenError(message, self.current())
