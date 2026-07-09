import os as _os
from dataclasses import replace as _replace
from typing import Any, Callable, Dict, Type

from nodes import (
    BlockStmt,
    ClassStmt,
    ExpressionStmt,
    ForStmt,
    FunctionStmt,
    IfStmt,
    ImportStmt,
    PrintStmt,
    ReturnStmt,
    Stmt,
    VarDeclStmt,
)
from ._storage import Storage
from ._signals import ReturnSignal
from ._function import Function
from ._class import LoxClass
from ._namespace import LiveModuleScope, LoxNamespace
from .errors import NotAClassError

from ._expr import evaluate, stringify


def _execute_expression_stmt(stmt: ExpressionStmt, storage: Storage) -> None:
    evaluate(stmt.expression, storage)


def _execute_print_stmt(stmt: PrintStmt, storage: Storage) -> None:
    value = evaluate(stmt.expression, storage)
    print(stringify(value))


def _execute_var_decl_stmt(stmt: VarDeclStmt, storage: Storage) -> None:
    value = evaluate(stmt.initializer, storage) if stmt.initializer is not None else None
    storage.define(stmt.name.lexeme, value)


def _execute_block_stmt(stmt: BlockStmt, storage: Storage) -> None:
    # PDF p.82-83 : 블록 진입 시 새 로컬 스코프 생성, 종료 시 소멸.
    storage.push_scope()
    try:
        for inner_stmt in stmt.statements:
            execute(inner_stmt, storage)
    finally:
        storage.pop_scope()


def _execute_if_stmt(stmt: IfStmt, storage: Storage) -> None:
    if evaluate(stmt.condition, storage):
        execute(stmt.then_branch, storage)
    elif stmt.else_branch is not None:
        execute(stmt.else_branch, storage)


def _execute_for_stmt(stmt: ForStmt, storage: Storage) -> None:
    """C-style ForStmt를 실행한다. for (initializer; condition; increment) body"""
    if stmt.initializer is not None:
        execute(stmt.initializer, storage)
    while True:
        if stmt.condition is not None:
            if not evaluate(stmt.condition, storage):
                break
        execute(stmt.body, storage)
        if stmt.increment is not None:
            evaluate(stmt.increment, storage)


def _execute_return_stmt(stmt: ReturnStmt, storage: Storage) -> None:
    # value가 없으면 null 반환. CallExpr가 이 시그널을
    # 잡아 반환값으로 사용하므로, 여기서는 값만 평가해 실어 던진다.
    value = evaluate(stmt.value, storage) if stmt.value is not None else None
    raise ReturnSignal(value)


def _execute_function_stmt(stmt: FunctionStmt, storage: Storage) -> None:
    storage.define(stmt.name.lexeme, Function(stmt))


def _execute_class_stmt(stmt: ClassStmt, storage: Storage) -> None:
    superclass = None
    if stmt.superclass is not None:
        superclass = evaluate(stmt.superclass, storage)
        if not isinstance(superclass, LoxClass):
            raise NotAClassError(stmt.name)

    klass = LoxClass(stmt.name.lexeme, superclass=superclass)
    for method_stmt in stmt.methods:
        klass.methods[method_stmt.name.lexeme] = Function(method_stmt, owner_class=klass)
    storage.define(stmt.name.lexeme, klass)


def _execute_import_stmt(stmt: ImportStmt, storage: Storage) -> None:
    """import 문을 실행한다.

    Importer로 대상 파일을 assemble+check한 뒤, 격리된 Storage에서 실행해
    선언된 이름들을 LoxNamespace로 묶어 alias 변수에 바인딩한다.

    같은 경로를 다른 import문(다이아몬드 import 등)에서 이미 실행한
    적이 있으면 다시 실행하지 않고 그때 만든 namespace를 그대로
    재사용한다(Importer.namespace_cache) - 그래야 여러 곳에서 import한
    같은 모듈이 전역 상태를 공유하는, 진짜 "모듈"다운 동작이 된다.
    재실행하면 각 import 지점마다 독립된 전역 상태를 갖게 되어, 한쪽에서
    바꾼 값을 다른 쪽에서 보지 못하는 문제가 생긴다.

    중첩 import 시 상대 경로를 올바르게 해석하도록 _current_base_dir를 전달하고,
    모듈용 Storage에 이 값을 이어받아 설정한다.
    """
    base_dir = storage._current_base_dir
    path = stmt.path.literal

    # 중첩 import 시 상대 경로의 기준 디렉터리를 계산한다 (Importer가
    # 내부적으로 쓰는 정규화와 동일한 규칙).
    if base_dir and not _os.path.isabs(path):
        resolved = _os.path.normpath(_os.path.join(base_dir, path))
    else:
        resolved = _os.path.normpath(path)

    cached_namespace = storage._importer.namespace_cache.get(resolved)
    if cached_namespace is not None:
        storage.define(stmt.alias.lexeme, cached_namespace)
        return

    statements, module_locals = storage._importer.import_module_with_locals(
        path,
        keyword=stmt.keyword,
        base_dir=base_dir,
    )

    module_base_dir = _os.path.dirname(_os.path.abspath(resolved))

    # 모듈 전용 Storage를 만들고 Importer 캐시를 공유한다. locals를 넘겨야
    # 모듈 안의 변수 조회도 정적 바인딩(O(depth) -> O(1))이 적용된다 —
    # 안 넘기면 checker.locals가 계산되고도 버려져서 매번 스코프 체인을
    # 선형 탐색하는 fallback 경로만 타게 된다.
    module_storage = Storage(locals=module_locals, importer=storage._importer)
    module_storage._current_base_dir = module_base_dir

    # Storage 초기화 직후의 내장 이름(Array 등)은 namespace에 포함하지 않는다.
    initial_names = set(module_storage._scopes[0].keys())

    # 실행 단계 순환 import 안전망 — 정적 사전 순회가 놓친 순환(Func/Class
    # 본문 속 import)이 실제로 실행되며 재귀하면 여기서 CircularImportError로 끊는다.
    with storage._importer.executing(path, keyword=stmt.keyword, base_dir=base_dir):
        for module_stmt in statements:
            execute(module_stmt, module_storage)

    # module_storage._scopes[0]을 복사하지 않고 그대로 공유한다 - 그래야
    # alias.inc() 같은 모듈 안 함수 호출로 전역이 바뀐 뒤에도 alias.counter
    # 처럼 필드에 직접 접근할 때 최신 값을 본다 (LiveModuleScope 참고).
    namespace = LoxNamespace(stmt.alias.lexeme, fields=LiveModuleScope(module_storage._scopes[0], initial_names))

    # 모듈 최상위 함수에 home_storage를 심어 모듈 globals를 볼 수 있게 한다.
    # module_storage에도 업데이트해서 함수 내 재귀 호출 시에도 적용된다.
    for name, value in list(namespace.fields.items()):
        if isinstance(value, Function):
            updated = _replace(value, home_storage=module_storage)
            namespace.fields[name] = updated
            module_storage._scopes[0][name] = updated

    storage._importer.namespace_cache[resolved] = namespace
    storage.define(stmt.alias.lexeme, namespace)


_STMT_EXECUTORS: Dict[Type[Stmt], Callable[[Any, Storage], None]] = {
    ExpressionStmt: _execute_expression_stmt,
    PrintStmt: _execute_print_stmt,
    VarDeclStmt: _execute_var_decl_stmt,
    BlockStmt: _execute_block_stmt,
    IfStmt: _execute_if_stmt,
    ForStmt: _execute_for_stmt,
    ReturnStmt: _execute_return_stmt,
    FunctionStmt: _execute_function_stmt,
    ClassStmt: _execute_class_stmt,
    ImportStmt: _execute_import_stmt,
}


def execute(stmt: Stmt, storage: Storage) -> None:
    """Stmt 하나를 실행한다."""
    handler = _STMT_EXECUTORS.get(type(stmt))
    if handler is None:
        raise NotImplementedError(f"{type(stmt).__name__} 실행은 아직 구현되지 않았습니다.")
    handler(stmt, storage)
