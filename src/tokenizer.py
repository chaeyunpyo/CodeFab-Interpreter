from nodes.tokens import Token
from nodes.token_type import TokenType


class Tokenizer:
    def __init__(self, source: str):
        self.source = source
        self.start = 0
        self.current = 0
        self.line = 1
        self.tokens = []

    def tokenize(self):
        # TODO: 실제 스캔 로직 구현
        return []
