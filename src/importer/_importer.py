"""import 대상 파일을 재귀적으로 assemble + check하는 로더.

Assembler(문법)만으로는 부족하다 — import 대상 파일도 최상위
프로그램과 똑같이 Checker의 정적 검사(파라미터 중복, this/super 오용
등)를 통과해야 안전하게 쓸 수 있기 때문이다. Assembler는 Checker를
모르므로(단방향 계층: Assembler -> Checker -> Executor), 이 둘을 함께
아는 위치에 별도 모듈로 둔다. (요구사항_정리/import.md)

Public API는 패키지 최상위(__init__.py)에서 re-export한다.
"""

import os
from contextlib import contextmanager

from assembler import Assembler, AssemblerError
from checker import CheckerUnit
from executor.errors import ExecutionError
from nodes.stmt import BlockStmt, IfStmt, ImportStmt


class PipelineImportError(ExecutionError):
    """import 대상 모듈을 assemble/check하는 과정에서 나는 오류의 공통 베이스.

    ExecutionError를 상속해, Pipeline/Debugger가 실행 중 오류를 잡는
    except ExecutionError 절에 import 오류도 함께 걸리게 한다. import
    자체도 결국 "실행 중(import 문을 만났을 때) 발생하는 오류"이기 때문이다.
    """

    UNIT = "Import"


class ImportedFileNotFoundError(PipelineImportError):
    """import 대상 파일이 존재하지 않을 때."""


class CircularImportError(PipelineImportError):
    """import가 서로를 순환 참조할 때. 예: a.txt가 b.txt를, b.txt가 다시
    a.txt를 import하는 경우.
    """


class ModuleImportError(PipelineImportError):
    """import 대상 파일이 Assembler(문법) 또는 Checker(정적 검사)를
    통과하지 못했을 때. 두 단계 모두 "이 파일은 그대로 쓸 수 없다"는
    같은 의미라 하나의 오류 타입으로 합쳐서 알린다.

    errors에 실제로 발생한 오류 목록을 그대로 담아, 호출한 쪽(Executor)이
    무엇이 잘못됐는지 확인할 수 있게 한다. Assembler 단계에서 실패했다면
    그 AssemblerError(TokenizerError/MissingTokenError/UnexpectedTokenError
    등) 하나만 담긴 리스트가, Checker 단계에서 실패했다면 CheckerUnit이
    찾은 CheckerError 목록이 담긴다.

    AssemblerError/CheckerError를 그대로 흘려보내지 않고 감싸는 이유는,
    "import 대상 파일 자체의 오류"와 "최상위 프로그램 자체의 오류"를
    호출하는 쪽이 타입만으로 구분할 수 있어야 하기 때문이다.
    """

    def __init__(self, path, errors, keyword=None):
        super().__init__(f"Imported file failed to import: {path}", keyword)
        self.path = path
        self.errors = errors


class Importer:
    """import 대상 파일을 읽어 Assembler + Checker까지 통과시킨 Stmt
    목록을 반환한다. (요구사항_정리/import.md)

    `import "sum.txt" alias sum;` 한 줄 뒤에서 파일 읽기 + Assembler +
    Checker + 캐시 조회라는 여러 단계를 감추고 import_module() 하나로
    노출한다(Facade 패턴). 같은 파일을 여러 번 import해도 다시 읽고
    조립하지 않도록 경로별 캐시(Registry)를 두고, 이 캐시와 별도로
    "지금 import 처리 중인 파일 목록"도 들고 있어 같은 경로가 다시
    나타나면 순환 import로 판단한다.

    alias를 실제 스코프에 바인딩해서 실행하는 것은 Executor 몫이라 이
    클래스는 관여하지 않는다 — import_module()이 돌려주는 Stmt 목록을
    어떻게 실행할지는 호출하는 쪽이 정한다.
    """

    # 정적 사전 순회(순환 import 조기 감지)가 내려가도 되는 구조. 이 문장이
    # 실행되면 그 자식도 무조건 실행되는(=한 번이라도 실행되면 반드시
    # 도달하는) 구조만 담는다. ForStmt/FunctionStmt/ClassStmt 본문은 반복
    # 횟수/호출 여부에 따라 실행이 안 될 수도 있어 여기서 제외한다 — 새
    # Stmt 타입이 생겨도 "항상 실행되는 자식이 있다"에 해당하면 여기 한
    # 줄만 추가하면 된다.
    _ALWAYS_EXECUTED_CHILDREN = {
        BlockStmt: lambda stmt: stmt.statements,
        IfStmt: lambda stmt: [branch for branch in (stmt.then_branch, stmt.else_branch) if branch is not None],
    }

    def __init__(self):
        # import 대상 경로 -> assemble+check까지 끝낸 Stmt 목록 (Registry).
        self._module_cache = {}
        # 지금 import 처리 중인 파일 경로 스택 (assemble+check 단계의 순환 import 감지용).
        self._importing = []
        # 지금 실행 중인 모듈 경로 스택 (실행 단계의 순환 import 감지용 안전망).
        #
        # 정적 사전 순회는 If/Block처럼 "실행되면 반드시 도달하는" 구조만
        # 보수적으로 훑는다 — Func/Class 본문 속 import는 호출 시점에야
        # 실행되므로 사전에 훑으면 실제로는 절대 안 일어날 순환을 오탐할
        # 수 있어 일부러 제외했다. 대신 그렇게 놓친 순환은 실제로 실행될
        # 때 여기서 잡아, RecursionError로 죽는 대신 CircularImportError로
        # 알린다.
        self._executing = []

    def import_module(self, path, keyword=None, base_dir=None):
        """path를 읽어 Assembler로 파싱하고 Checker로 정적 검사까지 마친
        뒤, 그 안의 import문까지 재귀적으로 같은 방식으로 처리해 최상위
        Stmt 목록을 반환한다.

        keyword는 이 파일을 불러오게 만든 import문의 토큰(오류 위치
        표시용)이다. base_dir은 상대 경로를 어느 디렉터리 기준으로
        풀지 정한다 — import문 안의 상대 경로는 실행 중인 프로세스의
        작업 디렉터리가 아니라 그 import문이 적힌 파일 기준이어야
        하므로, 재귀 호출 시 지금 조립 중인 파일의 디렉터리를 넘긴다.

        문법 오류든 정적 오류든 ModuleImportError로, 파일이 없으면
        ImportedFileNotFoundError로, 순환 import면 CircularImportError로
        알린다.
        """
        resolved = self._resolve_module_path(path, base_dir)

        if resolved in self._module_cache:
            return self._module_cache[resolved]

        if resolved in self._importing:
            cycle = " -> ".join(self._importing + [resolved])
            raise CircularImportError(f"Circular import detected: {cycle}", keyword)

        source = self._read_module_source(resolved, keyword)

        self._importing.append(resolved)
        try:
            try:
                statements = self._assemble(source)
            except AssemblerError as error:
                raise ModuleImportError(resolved, [error], keyword) from error

            checker_errors = self._check(statements)
            if checker_errors:
                raise ModuleImportError(resolved, checker_errors, keyword)

            nested_base_dir = os.path.dirname(resolved)
            for import_stmt in self._iter_nested_import_stmts(statements):
                self.import_module(import_stmt.path.literal, import_stmt.keyword, base_dir=nested_base_dir)
        finally:
            self._importing.pop()

        self._module_cache[resolved] = statements
        return statements

    @classmethod
    def _iter_nested_import_stmts(cls, statements):
        """statements 안의 ImportStmt를, 무조건 실행되는 구조(if/block)까지
        내려가며 찾는다. import는 반복문 안에서만 금지고 그 외 어디서든
        가능하므로(요구사항_정리/import.md), if 블록 속에 있어도 순환
        감지 대상이어야 한다.
        """
        for statement in statements:
            if isinstance(statement, ImportStmt):
                yield statement
                continue
            children_of = cls._ALWAYS_EXECUTED_CHILDREN.get(type(statement))
            if children_of is not None:
                yield from cls._iter_nested_import_stmts(children_of(statement))

    @contextmanager
    def executing(self, path, keyword=None, base_dir=None):
        """모듈을 실제로 실행하는 동안 재진입을 감지하는 실행 단계 안전망.

        정적 사전 순회가 의도적으로 건너뛰는 Func/Class 본문 속 import가
        실제로 실행되며 순환을 이루면, 캐시 히트가 _importing 체크보다
        먼저 걸려 정적 단계에서는 순환으로 안 잡히고 그대로 재실행을
        반복해 RecursionError로 죽는다 — 여기서 그 재진입을 잡는다.
        """
        resolved = self._resolve_module_path(path, base_dir)
        if resolved in self._executing:
            cycle = " -> ".join(self._executing + [resolved])
            raise CircularImportError(f"Circular import detected: {cycle}", keyword)

        self._executing.append(resolved)
        try:
            yield
        finally:
            self._executing.pop()

    @staticmethod
    def _resolve_module_path(path, base_dir):
        if base_dir and not os.path.isabs(path):
            path = os.path.join(base_dir, path)
        return os.path.normpath(path)

    @staticmethod
    def _read_module_source(path, keyword):
        try:
            with open(path, encoding="utf-8") as file:
                return file.read()
        except OSError:
            raise ImportedFileNotFoundError(f"Import target file not found: {path}", keyword) from None

    @staticmethod
    def _assemble(source):
        assembler = Assembler(source)
        assembler.execute()
        return assembler.ast

    @staticmethod
    def _check(statements):
        return CheckerUnit(statements).check()
