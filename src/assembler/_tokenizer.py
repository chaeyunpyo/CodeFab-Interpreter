from nodes.tokens import Token
from nodes.token_type import TokenType

from .errors import TokenizerError


class Tokenizer:
    SINGLE_CHAR_TOKENS = {
        "(": TokenType.LEFT_PAREN,
        ")": TokenType.RIGHT_PAREN,
        "{": TokenType.LEFT_BRACE,
        "}": TokenType.RIGHT_BRACE,
        "[": TokenType.LEFT_BRACKET,
        "]": TokenType.RIGHT_BRACKET,
        "+": TokenType.PLUS,
        "-": TokenType.MINUS,
        "*": TokenType.STAR,
        "/": TokenType.SLASH,
        "<": TokenType.LESS,
        ">": TokenType.GREATER,
        "=": TokenType.EQUAL,
        ";": TokenType.SEMICOLON,
        ",": TokenType.COMMA,
        ".": TokenType.DOT,
        ":": TokenType.COLON,
        "!": TokenType.BANG,
    }

    TWO_CHAR_TOKENS = {
        "==": TokenType.EQUAL_EQUAL,
        ">=": TokenType.GREATER_EQUAL,
        "<=": TokenType.LESS_EQUAL,
        "=<": TokenType.EQUAL_LESS,
        "=>": TokenType.EQUAL_GREATER,
        "!=": TokenType.BANG_EQUAL,
    }

    KEYWORDS = {
        "var": TokenType.VAR,
        "print": TokenType.PRINT,
        "if": TokenType.IF,
        "else": TokenType.ELSE,
        "for": TokenType.FOR,
        "true": TokenType.TRUE,
        "false": TokenType.FALSE,
        "and": TokenType.AND,
        "or": TokenType.OR,
        "Func": TokenType.FUNC,
        "Class": TokenType.CLASS,
        "return": TokenType.RETURN,
        "This": TokenType.THIS,
        "Super": TokenType.SUPER,
        "instanceof": TokenType.INSTANCEOF,
        "import": TokenType.IMPORT,
        "alias": TokenType.ALIAS,
    }

    def __init__(self, source: str):
        self.source = source
        self.current = 0
        self.line = 1
        self.tokens = []

    def tokenize(self):
        self.current = 0
        self.line = 1
        self.tokens = []

        while self.current < len(self.source):
            ch = self.source[self.current]
            two_chars = self.source[self.current:self.current + 2]

            if ch == "\n":
                self.line += 1
                self.current += 1
                continue

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

            if two_chars == "//":
                self._skip_line_comment()
                continue

            if two_chars in self.TWO_CHAR_TOKENS:
                self.tokens.append(Token(self.TWO_CHAR_TOKENS[two_chars], two_chars, line=self.line))
                self.current += 2
                continue

            if ch not in self.SINGLE_CHAR_TOKENS:
                raise TokenizerError(f"Unexpected character: {ch!r}")

            self.tokens.append(Token(self.SINGLE_CHAR_TOKENS[ch], ch, line=self.line))
            self.current += 1

        self.tokens.append(Token(TokenType.EOF, "", line=self.line))
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
        self.tokens.append(Token(TokenType.NUMBER, lexeme, literal=float(lexeme), line=self.line))

    def _scan_identifier(self):
        start = self.current
        while self.current < len(self.source) and (
            self.source[self.current].isalnum() or self.source[self.current] == "_"
        ):
            self.current += 1

        lexeme = self.source[start:self.current]
        token_type = self.KEYWORDS.get(lexeme, TokenType.IDENTIFIER)
        self.tokens.append(Token(token_type, lexeme, line=self.line))

    def _scan_string(self):
        start = self.current
        self.current += 1
        while self.current < len(self.source) and self.source[self.current] != '"':
            self.current += 1

        self.current += 1
        lexeme = self.source[start:self.current]
        self.tokens.append(Token(TokenType.STRING, lexeme, literal=lexeme[1:-1], line=self.line))

    def _skip_line_comment(self):
        while self.current < len(self.source) and self.source[self.current] != "\n":
            self.current += 1
