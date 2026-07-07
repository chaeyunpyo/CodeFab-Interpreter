from src.nodes.tokens import Token
from src.nodes.token_type import TokenType


class Tokenizer:
    SINGLE_CHAR_TOKENS = {
        "(": TokenType.LEFT_PAREN,
        ")": TokenType.RIGHT_PAREN,
        "{": TokenType.LEFT_BRACE,
        "}": TokenType.RIGHT_BRACE,
        "+": TokenType.PLUS,
        "-": TokenType.MINUS,
        "*": TokenType.STAR,
        "/": TokenType.SLASH,
        "<": TokenType.LESS,
        ">": TokenType.GREATER,
        "=": TokenType.EQUAL,
        ";": TokenType.SEMICOLON,
    }

    TWO_CHAR_TOKENS = {
        "==": TokenType.EQUAL_EQUAL,
        ">=": TokenType.GREATER_EQUAL,
        "<=": TokenType.LESS_EQUAL,
        "=<": TokenType.EQUAL_LESS,
        "=>": TokenType.EQUAL_GREATER,
    }

    KEYWORDS = {
        "var": TokenType.VAR,
        "print": TokenType.PRINT,
        "if": TokenType.IF,
        "else": TokenType.ELSE,
        "for": TokenType.FOR,
        "true": TokenType.TRUE,
        "false": TokenType.FALSE,
    }

    def __init__(self, source: str):
        self.source = source
        self.start = 0
        self.current = 0
        self.line = 1
        self.tokens = []

    def tokenize(self):
        while self.current < len(self.source):
            ch = self.source[self.current]

            if ch.isspace():
                self.current += 1
                continue

            if ch.isdigit():
                self._scan_number()
                continue

            if ch.isalpha() or ch == "_":
                self._scan_identifier()
                continue

            if ch == '"':
                self._scan_string()
                continue

            if ch == "/" and self.source[self.current + 1:self.current + 2] == "/":
                self._skip_line_comment()
                continue

            two_chars = self.source[self.current:self.current + 2]
            if two_chars in self.TWO_CHAR_TOKENS:
                self.tokens.append(Token(self.TWO_CHAR_TOKENS[two_chars], two_chars))
                self.current += 2
                continue

            self.tokens.append(Token(self.SINGLE_CHAR_TOKENS[ch], ch))
            self.current += 1

        self.tokens.append(Token(TokenType.EOF, ""))
        return self.tokens

    def _scan_number(self):
        start = self.current
        while self.current < len(self.source) and self.source[self.current].isdigit():
            self.current += 1

        if (
            self.current < len(self.source)
            and self.source[self.current] == "."
            and self.current + 1 < len(self.source)
            and self.source[self.current + 1].isdigit()
        ):
            self.current += 1
            while self.current < len(self.source) and self.source[self.current].isdigit():
                self.current += 1

        lexeme = self.source[start:self.current]
        self.tokens.append(Token(TokenType.NUMBER, lexeme, literal=float(lexeme)))

    def _scan_identifier(self):
        start = self.current
        while self.current < len(self.source) and (
            self.source[self.current].isalnum() or self.source[self.current] == "_"
        ):
            self.current += 1

        lexeme = self.source[start:self.current]
        token_type = self.KEYWORDS.get(lexeme, TokenType.IDENTIFIER)
        self.tokens.append(Token(token_type, lexeme))

    def _scan_string(self):
        start = self.current
        self.current += 1
        while self.current < len(self.source) and self.source[self.current] != '"':
            self.current += 1

        self.current += 1
        lexeme = self.source[start:self.current]
        self.tokens.append(Token(TokenType.STRING, lexeme, literal=lexeme[1:-1]))

    def _skip_line_comment(self):
        while self.current < len(self.source) and self.source[self.current] != "\n":
            self.current += 1
