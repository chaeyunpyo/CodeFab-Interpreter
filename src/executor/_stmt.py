from typing import Any, Callable, Dict, Type

from nodes import (
    BlockStmt,
    ClassStmt,
    ExpressionStmt,
    ForStmt,
    FunctionStmt,
    IfStmt,
    PrintStmt,
    ReturnStmt,
    Stmt,
    VarDeclStmt,
)
from ._storage import Storage
from ._signals import ReturnSignal
from ._function import Function
from ._class import LoxClass
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
}


def execute(stmt: Stmt, storage: Storage) -> None:
    """Stmt 하나를 실행한다."""
    handler = _STMT_EXECUTORS.get(type(stmt))
    if handler is None:
        raise NotImplementedError(f"{type(stmt).__name__} 실행은 아직 구현되지 않았습니다.")
    handler(stmt, storage)
