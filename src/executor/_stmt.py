from typing import Any, Callable, Dict, Type

from nodes import (
    BlockStmt,
    ExpressionStmt,
    ForStmt,
    IfStmt,
    PrintStmt,
    Stmt,
    VarDeclStmt,
)
from ._storage import Storage

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


_STMT_EXECUTORS: Dict[Type[Stmt], Callable[[Any, Storage], None]] = {
    ExpressionStmt: _execute_expression_stmt,
    PrintStmt: _execute_print_stmt,
    VarDeclStmt: _execute_var_decl_stmt,
    BlockStmt: _execute_block_stmt,
    IfStmt: _execute_if_stmt,
    ForStmt: _execute_for_stmt,
}


def execute(stmt: Stmt, storage: Storage) -> None:
    """Stmt 하나를 실행한다."""
    handler = _STMT_EXECUTORS.get(type(stmt))
    if handler is None:
        raise NotImplementedError(f"{type(stmt).__name__} 실행은 아직 구현되지 않았습니다.")
    handler(stmt, storage)
