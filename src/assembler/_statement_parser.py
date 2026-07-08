from nodes.token_type import TokenType
from nodes import (
    BlockStmt,
    ExpressionStmt,
    ForStmt,
    FunctionStmt,
    IfStmt,
    PrintStmt,
    ReturnStmt,
    VarDeclStmt,
)


class StatementParser:
    """선언/문장 문법을 파싱한다.

    statement()는 현재 토큰이 어떤 키워드인지에 따라 알맞은 파싱 메서드로
    분기하는데, 이 매핑을 if/elif 사슬 대신 표(_statement_factories)로 표현한다.
    새로운 문장 키워드가 추가되면 이 표에 한 줄만 추가하면 되고, 기존 분기
    로직은 건드릴 필요가 없다.
    """

    def __init__(self, tokens, expressions):
        self.tokens = tokens
        self.expressions = expressions
        # 문장을 시작하는 키워드 토큰 -> 그 문장을 파싱하는 메서드.
        # 새 문장 키워드가 추가되면 이 표에 한 줄만 추가하면 된다.
        self._statement_factories = {
            TokenType.FOR: self.for_statement,
            TokenType.IF: self.if_statement,
            TokenType.PRINT: self.print_statement,
            TokenType.LEFT_BRACE: self.block_statement,
            TokenType.FUNC: self.function_statement,
            TokenType.RETURN: self.return_statement,
        }

    # --- 선언 (declarations) ---

    def parse_line(self):
        """`var` 로 시작하면 변수 선언으로, 아니면 일반 문장으로 파싱한다."""
        if self.tokens.match(TokenType.VAR):
            return self.var_declaration()
        return self.statement()

    def var_declaration(self):
        """`var` IDENTIFIER `=` expression `;` 형태의 변수 선언을 파싱한다."""
        line = self.tokens.previous().line  # 'var' 키워드
        name = self.tokens.consume(TokenType.IDENTIFIER, "Expected variable name")
        self.tokens.consume(TokenType.EQUAL, "Expected '=' after variable name")
        initializer = self.expressions.parse()
        self.tokens.consume(TokenType.SEMICOLON, "Expected ';' after variable declaration")
        return VarDeclStmt(name=name, initializer=initializer, line=line)

    # --- 문장 (statements) ---

    def statement(self):
        """현재 토큰의 키워드에 맞는 문장 파서를 찾아 실행하고, 없으면 표현식 문장으로 처리한다."""
        for token_type, parse_statement in self._statement_factories.items():
            if self.tokens.match(token_type):
                return parse_statement()
        return self.expression_statement()

    def for_statement(self):
        """`for` `(` initializer `;` condition `;` increment `)` body 형태의 for문을 파싱한다."""
        line = self.tokens.previous().line  # 'for' 키워드
        self.tokens.consume(TokenType.LEFT_PAREN, "Expected '(' after 'for'")

        if self.tokens.match(TokenType.SEMICOLON):
            initializer = None
        elif self.tokens.match(TokenType.VAR):
            initializer = self.var_declaration()
        else:
            initializer = self.expression_statement()

        condition = None
        if not self.tokens.check(TokenType.SEMICOLON):
            condition = self.expressions.parse()
        self.tokens.consume(TokenType.SEMICOLON, "Expected ';' after loop condition")

        increment = None
        if not self.tokens.check(TokenType.RIGHT_PAREN):
            increment = self.expressions.parse()
        self.tokens.consume(TokenType.RIGHT_PAREN, "Expected ')' after for clauses")

        body = self.statement()

        return ForStmt(
            initializer=initializer, condition=condition, increment=increment, body=body, line=line
        )

    def if_statement(self):
        """`if` `(` condition `)` then_branch (`else` else_branch)? 형태의 if문을 파싱한다."""
        line = self.tokens.previous().line  # 'if' 키워드
        self.tokens.consume(TokenType.LEFT_PAREN, "Expected '(' after 'if'")
        condition = self.expressions.parse()
        self.tokens.consume(TokenType.RIGHT_PAREN, "Expected ')' after if condition")

        then_branch = self.statement()
        else_branch = None
        if self.tokens.match(TokenType.ELSE):
            else_branch = self.statement()

        return IfStmt(condition=condition, then_branch=then_branch, else_branch=else_branch, line=line)

    def print_statement(self):
        """`print` expression `;` 형태의 print문을 파싱한다."""
        line = self.tokens.previous().line  # 'print' 키워드
        value = self.expressions.parse()
        self.tokens.consume(TokenType.SEMICOLON, "Expected ';' after value")
        return PrintStmt(expression=value, line=line)

    def block_statement(self):
        """`{` 로 시작하는 블록 문장을 파싱한다."""
        line = self.tokens.previous().line  # '{'
        return BlockStmt(statements=self.block(), line=line)

    def function_statement(self):
        """`Func` IDENTIFIER `(` params? `)` `{` body `}` 형태의 함수 선언을 파싱한다.
        (요구사항_정리/function.md)
        """
        line = self.tokens.previous().line  # 'Func' 키워드
        name = self.tokens.consume(TokenType.IDENTIFIER, "Expected function name")
        self.tokens.consume(TokenType.LEFT_PAREN, "Expected '(' after function name")

        params = []
        if not self.tokens.check(TokenType.RIGHT_PAREN):
            params.append(self.tokens.consume(TokenType.IDENTIFIER, "Expected parameter name"))
            while self.tokens.match(TokenType.COMMA):
                params.append(self.tokens.consume(TokenType.IDENTIFIER, "Expected parameter name"))
        self.tokens.consume(TokenType.RIGHT_PAREN, "Expected ')' after parameters")

        self.tokens.consume(TokenType.LEFT_BRACE, "Expected '{' before function body")
        body = self.block()

        return FunctionStmt(name=name, params=params, body=body, line=line)

    def return_statement(self):
        """`return` expression? `;` 형태의 return문을 파싱한다. (요구사항_정리/function.md)

        keyword는 return이 함수 외부에 있는지 등을 검사할 때 오류 위치로 쓰인다.
        """
        keyword = self.tokens.previous()
        value = None
        if not self.tokens.check(TokenType.SEMICOLON):
            value = self.expressions.parse()
        self.tokens.consume(TokenType.SEMICOLON, "Expected ';' after return value")
        return ReturnStmt(keyword=keyword, value=value, line=keyword.line)

    def block(self):
        """`}` 나 파일 끝을 만날 때까지 한 줄씩 반복해서 읽어 문장 목록을 만든다."""
        statements = []
        while not self.tokens.check(TokenType.RIGHT_BRACE) and not self.tokens.is_at_end():
            statements.append(self.parse_line())
        self.tokens.consume(TokenType.RIGHT_BRACE, "Expected '}' after block")
        return statements

    def expression_statement(self):
        """expression `;` 형태의 표현식 문장을 파싱한다."""
        line = self.tokens.current().line
        expr = self.expressions.parse()
        self.tokens.consume(TokenType.SEMICOLON, "Expected ';' after expression")
        return ExpressionStmt(expression=expr, line=line)
