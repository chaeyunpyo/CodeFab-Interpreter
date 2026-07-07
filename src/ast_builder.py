from src.nodes.token_type import TokenType
from src.nodes import *

class AstBuilder:
    def __init__(self, tokens):
        self.tokens = tokens
        self.current = 0  # 현재 가리키고 있는 토큰의 인덱스

    def build(self):
        statements = []
        while not self._is_at_end():
            statements.append(self._declaration())
        return statements

    # --- helpers ---

    def _is_at_end(self):
        return self._peek().type == TokenType.EOF

    def _peek(self):
        return self.tokens[self.current]

    def _previous(self):
        return self.tokens[self.current - 1]

    def _advance(self):
        if not self._is_at_end():
            self.current += 1
        return self._previous()

    def _check(self, token_type):
        if self._is_at_end():
            return False
        return self._peek().type == token_type

    def _match(self, *token_types):
        for token_type in token_types:
            if self._check(token_type):
                self._advance()
                return True
        return False

    def _consume(self, token_type, message):
        if self._check(token_type):
            return self._advance()
        raise SyntaxError(message)

    # --- declarations & statements ---

    def _declaration(self):
        if self._match(TokenType.VAR):
            return self._var_declaration()
        return self._statement()

    def _var_declaration(self):
        name = self._consume(TokenType.IDENTIFIER, "Expected variable name")
        self._consume(TokenType.EQUAL, "Expected '=' after variable name")
        initializer = self._expression()
        self._consume(TokenType.SEMICOLON, "Expected ';' after variable declaration")
        return VarDeclStmt(name=name, initializer=initializer)

    def _statement(self):
        if self._match(TokenType.IF):
            return self._if_statement()
        if self._match(TokenType.PRINT):
            return self._print_statement()
        if self._match(TokenType.LEFT_BRACE):
            return BlockStmt(statements=self._block())
        return self._expression_statement()

    def _if_statement(self):
        self._consume(TokenType.LEFT_PAREN, "Expected '(' after 'if'")
        condition = self._expression()
        self._consume(TokenType.RIGHT_PAREN, "Expected ')' after if condition")

        then_branch = self._statement()
        else_branch = None
        if self._match(TokenType.ELSE):
            else_branch = self._statement()

        return IfStmt(condition=condition, then_branch=then_branch, else_branch=else_branch)

    def _print_statement(self):
        value = self._expression()
        self._consume(TokenType.SEMICOLON, "Expected ';' after value")
        return PrintStmt(expression=value)

    def _block(self):
        statements = []
        while not self._check(TokenType.RIGHT_BRACE) and not self._is_at_end():
            statements.append(self._declaration())
        self._consume(TokenType.RIGHT_BRACE, "Expected '}' after block")
        return statements

    def _expression_statement(self):
        expr = self._expression()
        self._consume(TokenType.SEMICOLON, "Expected ';' after expression")
        return ExpressionStmt(expression=expr)

    # --- expressions ---

    def _expression(self):
        return self._logic_or()

    def _logic_or(self):
        expr = self._logic_and()
        while self._match(TokenType.OR):
            operator = self._previous()
            right = self._logic_and()
            expr = LogicalExpr(left=expr, operator=operator, right=right)
        return expr

    def _logic_and(self):
        expr = self._comparison()
        while self._match(TokenType.AND):
            operator = self._previous()
            right = self._comparison()
            expr = LogicalExpr(left=expr, operator=operator, right=right)
        return expr

    def _comparison(self):
        expr = self._term()
        while self._match(TokenType.GREATER, TokenType.LESS):
            operator = self._previous()
            right = self._term()
            expr = BinaryExpr(left=expr, operator=operator, right=right)
        return expr

    def _term(self):
        expr = self._factor()
        while self._match(TokenType.PLUS, TokenType.MINUS):
            operator = self._previous()
            right = self._factor()
            expr = BinaryExpr(left=expr, operator=operator, right=right)
        return expr

    def _factor(self):
        expr = self._primary()
        while self._match(TokenType.STAR, TokenType.SLASH):
            operator = self._previous()
            right = self._primary()
            expr = BinaryExpr(left=expr, operator=operator, right=right)
        return expr

    def _primary(self):
        if self._match(TokenType.NUMBER, TokenType.STRING):
            return LiteralExpr(self._previous().literal)
        if self._match(TokenType.TRUE):
            return LiteralExpr(True)
        if self._match(TokenType.FALSE):
            return LiteralExpr(False)
        if self._match(TokenType.IDENTIFIER):
            return VariableExpr(self._previous())
        if self._match(TokenType.LEFT_PAREN):
            expr = self._expression()
            self._consume(TokenType.RIGHT_PAREN, "Expected ')' after expression")
            return GroupingExpr(expression=expr)

        raise SyntaxError(f"Unexpected token: {self._peek()}")
