from ._expression_parser import ExpressionParser
from ._statement_parser import StatementParser
from ._token_stream import TokenStream


class AstBuilder:
    """Token 목록을 재귀 하강 파싱하여 Stmt 트리(AST)를 만든다.

    실제 문법 규칙은 ExpressionParser(표현식)와 StatementParser(문장/선언)에
    나뉘어 있고, AstBuilder는 둘을 이어 붙여 "파일 끝까지 한 줄씩 반복해서
    읽는다"는 최상위 규칙만 담당한다.
    """

    def __init__(self, tokens):
        self.tokens = TokenStream(tokens)
        self.expressions = ExpressionParser(self.tokens)
        self.statements = StatementParser(self.tokens, self.expressions)

    def build(self):
        program = []
        while not self.tokens.is_at_end():
            program.append(self.statements.parse_line())
        return program
