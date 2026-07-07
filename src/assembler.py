import nodes

from src.tokenizer import Tokenizer


class Assembler:
    def __init__(self, source: str):
        self._root : nodes.AstNode = nodes.StmtNode()  # TODO: specify block stmt type
        self._tokenizer = Tokenizer(source)

    @property
    def root(self) -> nodes.AstNode:
        return self._root

    @root.setter
    def root(self, node: nodes.AstNode):
        raise Exception("Cannot set root node directly.")

    def execute(self):
        self._build_tree(self._tokenizer.tokenize())

    def _build_tree(self, tokens):
        pass
