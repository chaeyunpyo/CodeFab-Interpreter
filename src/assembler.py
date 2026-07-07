import nodes

from src.ast_builder import AstBuilder
from src.tokenizer import Tokenizer


class Assembler:
    def __init__(self, source: str):
        self._source = source
        self._ast : list[nodes.AstNode] = []

    @property
    def ast(self) -> list[nodes.AstNode]:
        return self._ast

    @ast.setter
    def ast(self, node):
        raise Exception("Cannot set ast node directly.")

    def execute(self):
        tokens = Tokenizer(self._source).tokenize()
        self._ast = AstBuilder(tokens).build()
