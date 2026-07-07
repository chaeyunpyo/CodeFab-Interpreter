from assembler import Assembler
from checker import CheckerUnit
from executor import ExecutionError, Storage, execute


class Pipeline:
    """Assembler -> CheckerUnit -> Executor를 순서대로 실행한다."""

    def __init__(self):
        self.storage = Storage()

    def run(self, source):
        statements = self._assemble(source)

        checker_errors = self._check(statements)
        if checker_errors:
            return checker_errors

        try:
            self._execute(statements)
        except ExecutionError as error:
            return [error]

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
