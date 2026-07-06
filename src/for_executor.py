"""ForStmt 실행 확장 모듈.

executor.execute() 가 처리하지 않는 ForStmt 를 추가로 지원한다.

Public API:
    execute_for(stmt, storage) -> None  - ForStmt 하나를 실행
    execute(stmt, storage)     -> None  - executor.execute() + ForStmt 지원 래퍼

팀A executor.py 통합 가이드:
    from for_executor import execute_for
    from nodes import ForStmt

    # executor.py 의 execute() 안에 아래 분기를 추가
    if isinstance(stmt, ForStmt):
        execute_for(stmt, storage)
        return

ForStmt 는 C-style:
    for (initializer; condition; increment) body
    예: for (var i = 0.0; i < 10.0; i = i + 1.0) { ... }

루프 종료 후 loop variable 은 마지막 값을 유지한다 (Python 동일 방식).
"""

from executor import evaluate
from executor import execute as _execute_base
from nodes import BlockStmt, ForStmt, IfStmt
from storage import Storage


def execute(stmt, storage: Storage) -> None:
    """executor.execute() 를 ForStmt 까지 확장한 래퍼.

    ForStmt 는 execute_for() 로 직접 처리한다.

    BlockStmt / IfStmt 는 내부에 ForStmt 를 포함할 수 있는 compound statement 이므로
    이 모듈의 execute() 로 재귀 처리한다. 이를 통해 중첩 ForStmt 가 올바르게 처리된다.

    그 외 leaf statement (ExpressionStmt, PrintStmt, VarDeclStmt 등) 는
    executor.execute() 에 그대로 위임한다.
    """
    if isinstance(stmt, ForStmt):
        execute_for(stmt, storage)

    elif isinstance(stmt, BlockStmt):
        storage.push_scope()
        try:
            for inner in stmt.statements:
                execute(inner, storage)
        finally:
            storage.pop_scope()

    elif isinstance(stmt, IfStmt):
        if evaluate(stmt.condition, storage):
            execute(stmt.then_branch, storage)
        elif stmt.else_branch is not None:
            execute(stmt.else_branch, storage)

    else:
        _execute_base(stmt, storage)


def execute_for(stmt: ForStmt, storage: Storage) -> None:
    """C-style ForStmt 를 실행한다.

    body 실행에 이 모듈의 execute() 를 재사용하므로
    Executor 공통 dispatch(BlockStmt, VarDeclStmt 등)가 그대로 활용되며
    중첩 ForStmt 도 올바르게 처리된다.
    """
    if stmt.initializer is not None:
        execute(stmt.initializer, storage)

    while True:
        if stmt.condition is not None:
            if not evaluate(stmt.condition, storage):
                break

        execute(stmt.body, storage)

        if stmt.increment is not None:
            evaluate(stmt.increment, storage)
