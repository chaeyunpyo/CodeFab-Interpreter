"""전체 Unit을 하나로 묶어 실행하는 Pipeline.

소스 코드(str) 한 덩어리를 아래 순서로 처리한다.

    Assembler   -> Stmt 트리(AST) 조립
    CheckerUnit -> 실행 전 의미 오류(정적 오류) 검사
    Executor    -> 문제 없으면 실제 실행

주의: src.nodes / nodes 이중 import 문제가 해결되기 전까지는, Assembler가
만든 트리를 CheckerUnit/Executor가 제대로 인식하지 못할 수 있다.
"""

from assembler import Assembler
from checker import CheckerUnit
from executor import execute
from storage import Storage


class Pipeline:
    """Assembler -> CheckerUnit -> Executor를 순서대로 실행한다."""

    def __init__(self):
        self.storage = Storage()

    def run(self, source):
        """소스 코드를 조립 -> 검사 -> 실행한다.

        검사에서 오류를 찾으면 실행하지 않고 오류 리스트를 반환한다.
        문제가 없으면 실행까지 마치고 빈 리스트를 반환한다.
        """
        statements = self._assemble(source)

        errors = self._check(statements)
        if errors:
            return errors

        self._execute(statements)
        return []

    def _assemble(self, source):
        assembler = Assembler(source)
        assembler.execute()
        return assembler.ast

    def _check(self, statements):
        return CheckerUnit(statements).check()

    def _execute(self, statements):
        for statement in statements:
            execute(statement, self.storage)
