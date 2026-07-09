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
from checker import CheckerError, CheckerUnit
from nodes.stmt import BlockStmt, ClassStmt, FunctionStmt, IfStmt, ImportStmt, VarDeclStmt

from .errors import CircularImportError, ImportedFileNotFoundError, ModuleImportError


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

    # import 대상 파일의 최상위에는 선언(다른 파일 import, 함수 선언, 전역
    # 변수 선언, 클래스 선언)만 허용한다 (요구사항_정리/import.md). 그 외
    # 구문(print, for, 최상위 expression 등)은 이 팀의 선택에 따라 오류로
    # 처리한다. if/block은 선언 자체는 아니지만 import 위치 제한 규칙상
    # import를 감싸는 용도로 어디서든 쓸 수 있어(반복문만 금지) 투명하게
    # 뚫고 내려가 안쪽 내용만 검사한다 (_ALWAYS_EXECUTED_CHILDREN과 동일한
    # "무조건 실행되는 구조" 기준).
    _ALLOWED_TOP_LEVEL_STATEMENTS = (ImportStmt, FunctionStmt, VarDeclStmt, ClassStmt)

    def __init__(self):
        # import 대상 경로 -> (assemble+check까지 끝낸 Stmt 목록, 그 안의
        # 변수 거리(distance) 맵(checker.locals)) (Registry).
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
        statements, _locals = self.import_module_with_locals(path, keyword, base_dir)
        return statements

    def import_module_with_locals(self, path, keyword=None, base_dir=None):
        """import_module()과 동일하게 동작하지만, 대상 파일의 Stmt 목록과
        함께 그 안의 변수 거리(distance) 맵(CheckerUnit.locals)도 반환한다.

        Executor가 모듈 실행용 Storage(정적 바인딩 조회용 locals)를 만들 때
        쓴다. import_module()은 이 값을 버리고 Stmt 목록만 돌려주는 얇은
        래퍼다.
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

            checker = CheckerUnit(statements)
            checker_errors = checker.check()
            if checker_errors:
                raise ModuleImportError(resolved, checker_errors, keyword)

            self._check_declarations_only(statements, resolved, keyword)

            nested_base_dir = os.path.dirname(resolved)
            for import_stmt in self._iter_nested_import_stmts(statements):
                self.import_module_with_locals(
                    import_stmt.path.literal, import_stmt.keyword, base_dir=nested_base_dir
                )
        finally:
            self._importing.pop()

        self._module_cache[resolved] = (statements, checker.locals)
        return self._module_cache[resolved]

    def _check_declarations_only(self, statements, resolved, keyword):
        """최상위 문장이 전부 선언(import/함수/변수/클래스 선언)인지 검사한다.

        요구사항_정리/import.md: "그 외 구문 처리는 팀 자율" 조항 중 이
        팀은 오류 처리를 선택했다.
        """
        illegal = list(self._find_illegal_statements(statements))
        if not illegal:
            return

        errors = [
            CheckerError(
                "Import target file can only contain declarations "
                f"(import/function/variable/class), found {type(statement).__name__}.",
                statement,
            )
            for statement in illegal
        ]
        raise ModuleImportError(resolved, errors, keyword)

    @classmethod
    def _find_illegal_statements(cls, statements):
        """허용된 선언이 아닌 문장을 찾는다. if/block은 선언은 아니지만
        import를 감싸는 용도로 허용되므로 투명하게 뚫고 내려간다
        (_iter_nested_import_stmts와 같은 기준).
        """
        for statement in statements:
            if isinstance(statement, cls._ALLOWED_TOP_LEVEL_STATEMENTS):
                continue
            children_of = cls._ALWAYS_EXECUTED_CHILDREN.get(type(statement))
            if children_of is not None:
                yield from cls._find_illegal_statements(children_of(statement))
                continue
            yield statement

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
