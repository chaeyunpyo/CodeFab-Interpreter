import pytest

from assembler import Assembler
import nodes

def test_assembler_empty_literal():
    source = ""
    sut = Assembler(source)

    sut.execute()

    assert type(sut.root) == nodes.StmtNode
