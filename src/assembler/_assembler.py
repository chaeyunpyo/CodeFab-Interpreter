from nodes.ast_node import AstNode

from ._ast_builder import AstBuilder
from ._tokenizer import Tokenizer


class Assembler:
    def __init__(self, source: str):
        self._source = source
        self._ast : list[AstNode] = []

    @property
    def ast(self) -> list[AstNode]:
        return self._ast

    @ast.setter
    def ast(self, node):
        raise Exception("Cannot set ast node directly.")

    def execute(self):
        tokens = Tokenizer(self._source).tokenize()
        self._ast = AstBuilder(tokens).build()
