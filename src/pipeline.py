from assembler import Assembler, AssemblerError
from checker import CheckerUnit
from executor import ExecutionError, Storage, execute


class Pipeline:
    """Assembler -> CheckerUnit -> Executor를 순서대로 실행한다."""

    def __init__(self):
        self.storage = Storage()

    def run(self, source):
        try:
            statements = self._assemble(source)
        except AssemblerError as error:
            return [error]

        checker = CheckerUnit(statements)
        checker_errors = checker.check()
        if checker_errors:
            return checker_errors
        self.storage.locals = checker.locals

        try:
            self._execute(statements)
        except ExecutionError as error:
            return [error]

        return []

    def _assemble(self, source):
        assembler = Assembler(source)
        assembler.execute()
        return assembler.ast

    def _execute(self, statements):
        for statement in statements:
            execute(statement, self.storage)
