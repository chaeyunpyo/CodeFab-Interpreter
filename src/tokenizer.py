from src.nodes.tokens import Token
from src.nodes.token_type import TokenType


class Tokenizer:
    SINGLE_CHAR_TOKENS = {
        "(": TokenType.LEFT_PAREN,
        "+": TokenType.PLUS,
    }

    def __init__(self, source: str):
        self.source = source
        self.start = 0
        self.current = 0
        self.line = 1
        self.tokens = []

    def tokenize(self):
        for ch in self.source:
            self.tokens.append(Token(self.SINGLE_CHAR_TOKENS[ch], ch))

        self.tokens.append(Token(TokenType.EOF, ""))
        return self.tokens
