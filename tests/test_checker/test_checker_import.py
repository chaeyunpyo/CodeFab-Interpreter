from checker import CheckerUnit
from nodes.stmt import BlockStmt, ForStmt

from checker_helpers import make_function, make_import, make_var_decl

# import 오류 검사 (요구사항_정리/import.md) - 같은 scope 중복/alias 충돌/반복문 내부 3개만 다룬다 (나머지는 Assembler 담당).


def test_check_allows_imports_with_different_paths_and_aliases():
    # import "a.txt" alias a; import "b.txt" alias b;
    statements = [make_import(path="a.txt", alias="a"), make_import(path="b.txt", alias="b")]
    checker = CheckerUnit(statements)

    assert checker.check() == []


def test_check_detects_duplicate_import_of_same_path_in_same_scope():
    # import "a.txt" alias a; import "a.txt" alias b;  -- alias가 달라도 같은 파일 재import는 금지.
    statements = [make_import(path="a.txt", alias="a"), make_import(path="a.txt", alias="b")]
    checker = CheckerUnit(statements)

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Already imported this file in this scope."


def test_check_detects_duplicate_import_inside_nested_block():
    # { import "a.txt" alias a; import "a.txt" alias b; }
    statements = [
        BlockStmt(statements=[make_import(path="a.txt", alias="a"), make_import(path="a.txt", alias="b")]),
    ]
    checker = CheckerUnit(statements)

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Already imported this file in this scope."


def test_check_detects_alias_name_conflict_between_two_imports():
    # import "a.txt" alias x; import "b.txt" alias x;  -- 경로는 달라도 alias가 겹치면 금지.
    statements = [make_import(path="a.txt", alias="x"), make_import(path="b.txt", alias="x")]
    checker = CheckerUnit(statements)

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Already a variable with this name in this scope."


def test_check_detects_alias_name_conflict_with_existing_variable():
    # var x = 1; import "a.txt" alias x;
    statements = [make_var_decl("x"), make_import(path="a.txt", alias="x")]
    checker = CheckerUnit(statements)

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Already a variable with this name in this scope."


def test_check_allows_same_alias_in_different_scopes():
    # import "a.txt" alias x; { import "b.txt" alias x; }  -- 서로 다른 스코프라 충돌이 아니다.
    statements = [
        make_import(path="a.txt", alias="x"),
        BlockStmt(statements=[make_import(path="b.txt", alias="x")]),
    ]
    checker = CheckerUnit(statements)

    assert checker.check() == []


def test_check_detects_import_inside_for_loop_body():
    # for (;;) { import "a.txt" alias a; }
    statements = [
        ForStmt(
            initializer=None,
            condition=None,
            increment=None,
            body=BlockStmt(statements=[make_import(path="a.txt", alias="a")]),
        ),
    ]
    checker = CheckerUnit(statements)

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Can't use import statement inside a loop."


def test_check_detects_import_as_bare_for_body():
    # for (;;) import "a.txt" alias a;  (body가 블록 없이 바로 import)
    statements = [
        ForStmt(initializer=None, condition=None, increment=None, body=make_import(path="a.txt", alias="a")),
    ]
    checker = CheckerUnit(statements)

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Can't use import statement inside a loop."


def test_check_allows_import_outside_loop_body():
    # import "a.txt" alias a; for (;;) { }
    statements = [
        make_import(path="a.txt", alias="a"),
        ForStmt(initializer=None, condition=None, increment=None, body=BlockStmt(statements=[])),
    ]
    checker = CheckerUnit(statements)

    assert checker.check() == []


def test_check_detects_import_inside_nested_loop():
    # for (;;) { for (;;) { import "a.txt" alias a; } }
    inner_for = ForStmt(
        initializer=None,
        condition=None,
        increment=None,
        body=BlockStmt(statements=[make_import(path="a.txt", alias="a")]),
    )
    outer_for = ForStmt(initializer=None, condition=None, increment=None, body=BlockStmt(statements=[inner_for]))
    checker = CheckerUnit([outer_for])

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Can't use import statement inside a loop."


def test_check_does_not_leak_loop_context_to_sibling_statement():
    # for (;;) { } import "a.txt" alias a;  -- "반복문 안" 상태가 새면 안 된다.
    statements = [
        ForStmt(initializer=None, condition=None, increment=None, body=BlockStmt(statements=[])),
        make_import(path="a.txt", alias="a"),
    ]
    checker = CheckerUnit(statements)

    assert checker.check() == []


# 상위 level 중복 import 금지 (요구사항_정리/import.md 세부 규칙)


def test_check_detects_duplicate_import_in_enclosing_scope():
    # import "a.txt" alias a; { import "a.txt" alias b; }  -- alias가 달라도 상위에서 이미 import됨.
    statements = [
        make_import(path="a.txt", alias="a"),
        BlockStmt(statements=[make_import(path="a.txt", alias="b")]),
    ]
    checker = CheckerUnit(statements)

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Already imported this file in an enclosing scope."


def test_check_detects_duplicate_import_in_deeply_nested_enclosing_scope():
    # import "a.txt" alias a; { { import "a.txt" alias b; } }
    statements = [
        make_import(path="a.txt", alias="a"),
        BlockStmt(statements=[BlockStmt(statements=[make_import(path="a.txt", alias="b")])]),
    ]
    checker = CheckerUnit(statements)

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Already imported this file in an enclosing scope."


def test_check_detects_duplicate_import_in_enclosing_scope_from_function_body():
    # import "a.txt" alias a; Func foo() { import "a.txt" alias b; }
    fn = make_function(body=[make_import(path="a.txt", alias="b")])
    statements = [make_import(path="a.txt", alias="a"), fn]
    checker = CheckerUnit(statements)

    errors = checker.check()

    assert len(errors) == 1
    assert errors[0].message == "Already imported this file in an enclosing scope."


def test_check_allows_same_path_imported_in_sibling_scopes():
    # { import "a.txt" alias a; } { import "a.txt" alias b; }  -- 서로 조상-자손 관계가 아니다.
    statements = [
        BlockStmt(statements=[make_import(path="a.txt", alias="a")]),
        BlockStmt(statements=[make_import(path="a.txt", alias="b")]),
    ]
    checker = CheckerUnit(statements)

    assert checker.check() == []


def test_check_allows_different_path_in_nested_scope():
    # import "a.txt" alias a; { import "b.txt" alias b; }
    statements = [
        make_import(path="a.txt", alias="a"),
        BlockStmt(statements=[make_import(path="b.txt", alias="b")]),
    ]
    checker = CheckerUnit(statements)

    assert checker.check() == []
