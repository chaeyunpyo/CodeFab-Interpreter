import pytest

from nodes.tokens import Token
from nodes.token_type import TokenType
from nodes import *
from assembler import (
    AstBuilder,
    InvalidAssignmentTargetError,
    MissingTokenError,
    UnexpectedTokenError,
)


# --- 21단계: import 문 파싱 (요구사항_정리/import.md) ---
#
# 반복문 내부 금지, 같은/상위 scope 중복 import 금지, 순환 import,
# alias 충돌 등은 AST 구조만으로 끝나지 않는(스코프·파일 시스템까지
# 봐야 하는) 정적 검사라 Checker 몫이다. AstBuilder는 문법
# `import` STRING `alias` IDENTIFIER `;`만 정확히 조립하면 되고,
# 반복문 안에 와도 구조적으로는 유효한 문장이라 그대로 파싱해야 한다.

def test_step21_basic_import_statement():
    """소스코드: import "sum.txt" alias sum;"""
    tokens = [
        Token(TokenType.IMPORT, "import"),
        Token(TokenType.STRING, '"sum.txt"', literal="sum.txt"),
        Token(TokenType.ALIAS, "alias"),
        Token(TokenType.IDENTIFIER, "sum"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        ImportStmt(
            keyword=Token(TokenType.IMPORT, "import"),
            path=Token(TokenType.STRING, '"sum.txt"', literal="sum.txt"),
            alias=Token(TokenType.IDENTIFIER, "sum"),
        )
    ]


def test_step21_alias_used_to_access_imported_function():
    """소스코드:
    import "sum.txt" alias sum;
    sum.add(1, 2);
    """
    tokens = [
        Token(TokenType.IMPORT, "import"),
        Token(TokenType.STRING, '"sum.txt"', literal="sum.txt"),
        Token(TokenType.ALIAS, "alias"),
        Token(TokenType.IDENTIFIER, "sum"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.IDENTIFIER, "sum"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "add"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.NUMBER, "1", literal=1.0),
        Token(TokenType.COMMA, ","),
        Token(TokenType.NUMBER, "2", literal=2.0),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        ImportStmt(
            keyword=Token(TokenType.IMPORT, "import"),
            path=Token(TokenType.STRING, '"sum.txt"', literal="sum.txt"),
            alias=Token(TokenType.IDENTIFIER, "sum"),
        ),
        ExpressionStmt(
            expression=CallExpr(
                callee=FieldGetExpr(
                    object=VariableExpr(Token(TokenType.IDENTIFIER, "sum")),
                    name=Token(TokenType.IDENTIFIER, "add"),
                ),
                paren=Token(TokenType.LEFT_PAREN, "("),
                arguments=[LiteralExpr(1.0), LiteralExpr(2.0)],
            )
        ),
    ]


def test_step21_import_inside_block():
    """소스코드: { import "sum.txt" alias sum; }  (블록 안에서도 문법적으로 허용)"""
    tokens = [
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.IMPORT, "import"),
        Token(TokenType.STRING, '"sum.txt"', literal="sum.txt"),
        Token(TokenType.ALIAS, "alias"),
        Token(TokenType.IDENTIFIER, "sum"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        BlockStmt(
            statements=[
                ImportStmt(
                    keyword=Token(TokenType.IMPORT, "import"),
                    path=Token(TokenType.STRING, '"sum.txt"', literal="sum.txt"),
                    alias=Token(TokenType.IDENTIFIER, "sum"),
                )
            ]
        )
    ]


def test_step21_import_inside_for_loop_still_parses():
    """소스코드: for (;;) { import "sum.txt" alias sum; }

    반복문 내부 import 금지는 Checker의 정적 검사 몫이라, AstBuilder는
    구조적으로 유효한 이 문장을 오류 없이 그대로 파싱해야 한다.
    """
    tokens = [
        Token(TokenType.FOR, "for"),
        Token(TokenType.LEFT_PAREN, "("),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RIGHT_PAREN, ")"),
        Token(TokenType.LEFT_BRACE, "{"),
        Token(TokenType.IMPORT, "import"),
        Token(TokenType.STRING, '"sum.txt"', literal="sum.txt"),
        Token(TokenType.ALIAS, "alias"),
        Token(TokenType.IDENTIFIER, "sum"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.RIGHT_BRACE, "}"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        ForStmt(
            initializer=None,
            condition=None,
            increment=None,
            body=BlockStmt(
                statements=[
                    ImportStmt(
                        keyword=Token(TokenType.IMPORT, "import"),
                        path=Token(TokenType.STRING, '"sum.txt"', literal="sum.txt"),
                        alias=Token(TokenType.IDENTIFIER, "sum"),
                    )
                ]
            ),
        )
    ]


def test_step21_multiple_imports_in_sequence():
    """소스코드:
    import "sum.txt" alias sum;
    import "math.txt" alias math;
    """
    tokens = [
        Token(TokenType.IMPORT, "import"),
        Token(TokenType.STRING, '"sum.txt"', literal="sum.txt"),
        Token(TokenType.ALIAS, "alias"),
        Token(TokenType.IDENTIFIER, "sum"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.IMPORT, "import"),
        Token(TokenType.STRING, '"math.txt"', literal="math.txt"),
        Token(TokenType.ALIAS, "alias"),
        Token(TokenType.IDENTIFIER, "math"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    assert builder.build() == [
        ImportStmt(
            keyword=Token(TokenType.IMPORT, "import"),
            path=Token(TokenType.STRING, '"sum.txt"', literal="sum.txt"),
            alias=Token(TokenType.IDENTIFIER, "sum"),
        ),
        ImportStmt(
            keyword=Token(TokenType.IMPORT, "import"),
            path=Token(TokenType.STRING, '"math.txt"', literal="math.txt"),
            alias=Token(TokenType.IDENTIFIER, "math"),
        ),
    ]


def test_step21_import_missing_path_raises_missing_token_error():
    """소스코드: import alias sum;  (경로 문자열 누락)"""
    tokens = [
        Token(TokenType.IMPORT, "import"),
        Token(TokenType.ALIAS, "alias"),
        Token(TokenType.IDENTIFIER, "sum"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    with pytest.raises(MissingTokenError) as excinfo:
        builder.build()

    assert "Expected import path as a string literal" in str(excinfo.value)
    assert excinfo.value.token == Token(TokenType.ALIAS, "alias")


def test_step21_import_path_not_a_string_raises_missing_token_error():
    """소스코드: import 5 alias sum;  (경로 자리에 문자열이 아닌 값)"""
    tokens = [
        Token(TokenType.IMPORT, "import"),
        Token(TokenType.NUMBER, "5", literal=5.0),
        Token(TokenType.ALIAS, "alias"),
        Token(TokenType.IDENTIFIER, "sum"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    with pytest.raises(MissingTokenError) as excinfo:
        builder.build()

    assert "Expected import path as a string literal" in str(excinfo.value)


def test_step21_import_path_missing_quotes_raises_missing_token_error():
    """소스코드: import sum.txt alias sum;  (경로에 따옴표를 빠뜨려 문자열이 아닌
    IDENTIFIER `.` IDENTIFIER 세 토큰으로 쪼개져 들어온 경우)

    실제로 흔한 실수(따옴표 생략)를 재현한다. `sum.txt`는 문자열
    리터럴이 아니라 IDENTIFIER("sum"), DOT, IDENTIFIER("txt")로
    토큰화되므로 경로 자리에서 곧바로 실패해야 한다.
    """
    tokens = [
        Token(TokenType.IMPORT, "import"),
        Token(TokenType.IDENTIFIER, "sum"),
        Token(TokenType.DOT, "."),
        Token(TokenType.IDENTIFIER, "txt"),
        Token(TokenType.ALIAS, "alias"),
        Token(TokenType.IDENTIFIER, "sum"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    with pytest.raises(MissingTokenError) as excinfo:
        builder.build()

    assert "Expected import path as a string literal" in str(excinfo.value)
    assert excinfo.value.token == Token(TokenType.IDENTIFIER, "sum")


def test_step21_import_truncated_right_after_keyword_raises_missing_token_error():
    """소스코드: import  (경로도 없이 곧바로 끝남)"""
    tokens = [
        Token(TokenType.IMPORT, "import"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    with pytest.raises(MissingTokenError) as excinfo:
        builder.build()

    assert "Expected import path as a string literal" in str(excinfo.value)
    assert excinfo.value.token == Token(TokenType.EOF, "")


def test_step21_import_truncated_right_after_path_raises_missing_token_error():
    """소스코드: import "sum.txt"  ('alias' 이하가 통째로 누락되고 곧바로 끝남)"""
    tokens = [
        Token(TokenType.IMPORT, "import"),
        Token(TokenType.STRING, '"sum.txt"', literal="sum.txt"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    with pytest.raises(MissingTokenError) as excinfo:
        builder.build()

    assert "Expected 'alias' after import path" in str(excinfo.value)
    assert excinfo.value.token == Token(TokenType.EOF, "")


def test_step21_import_truncated_right_after_alias_keyword_raises_missing_token_error():
    """소스코드: import "sum.txt" alias  (별칭 이름 없이 곧바로 끝남)"""
    tokens = [
        Token(TokenType.IMPORT, "import"),
        Token(TokenType.STRING, '"sum.txt"', literal="sum.txt"),
        Token(TokenType.ALIAS, "alias"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    with pytest.raises(MissingTokenError) as excinfo:
        builder.build()

    assert "Expected alias name" in str(excinfo.value)
    assert excinfo.value.token == Token(TokenType.EOF, "")


def test_step21_import_missing_alias_keyword_raises_missing_token_error():
    """소스코드: import "sum.txt" sum;  ('alias' 키워드 누락)"""
    tokens = [
        Token(TokenType.IMPORT, "import"),
        Token(TokenType.STRING, '"sum.txt"', literal="sum.txt"),
        Token(TokenType.IDENTIFIER, "sum"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    with pytest.raises(MissingTokenError) as excinfo:
        builder.build()

    assert "Expected 'alias' after import path" in str(excinfo.value)


def test_step21_import_misspelled_alias_keyword_raises_missing_token_error():
    """소스코드: import "sum.txt" alas sum;  ('alias'를 'alas'로 오타 낸 경우)

    'alas'는 등록된 키워드가 아니라 토큰화 단계에서 그냥 IDENTIFIER로
    처리되므로, ALIAS 토큰을 기대하는 자리에서 IDENTIFIER("alas")를
    만나 동일한 MissingTokenError로 걸러져야 한다.
    """
    tokens = [
        Token(TokenType.IMPORT, "import"),
        Token(TokenType.STRING, '"sum.txt"', literal="sum.txt"),
        Token(TokenType.IDENTIFIER, "alas"),
        Token(TokenType.IDENTIFIER, "sum"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    with pytest.raises(MissingTokenError) as excinfo:
        builder.build()

    assert "Expected 'alias' after import path" in str(excinfo.value)
    assert excinfo.value.token == Token(TokenType.IDENTIFIER, "alas")


def test_step21_import_missing_alias_name_raises_missing_token_error():
    """소스코드: import "sum.txt" alias ;  (별칭 이름 누락)"""
    tokens = [
        Token(TokenType.IMPORT, "import"),
        Token(TokenType.STRING, '"sum.txt"', literal="sum.txt"),
        Token(TokenType.ALIAS, "alias"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    with pytest.raises(MissingTokenError) as excinfo:
        builder.build()

    assert "Expected alias name" in str(excinfo.value)
    assert excinfo.value.token == Token(TokenType.SEMICOLON, ";")


def test_step21_import_invalid_alias_name_raises_missing_token_error():
    """소스코드: import "sum.txt" alias 123;  (별칭 자리에 식별자가 아닌 값)

    별칭 이름 자리는 IDENTIFIER만 허용되므로, 숫자 리터럴처럼 유효하지
    않은 이름이 오면 (아예 생략된 경우와 동일하게) MissingTokenError로
    걸러져야 한다.
    """
    tokens = [
        Token(TokenType.IMPORT, "import"),
        Token(TokenType.STRING, '"sum.txt"', literal="sum.txt"),
        Token(TokenType.ALIAS, "alias"),
        Token(TokenType.NUMBER, "123", literal=123.0),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    with pytest.raises(MissingTokenError) as excinfo:
        builder.build()

    assert "Expected alias name" in str(excinfo.value)
    assert excinfo.value.token == Token(TokenType.NUMBER, "123", literal=123.0)


def test_step21_import_reserved_keyword_as_alias_name_raises_missing_token_error():
    """소스코드: import "sum.txt" alias var;  (별칭 자리에 예약어를 사용)

    'var'는 키워드 토큰(VAR)으로 토큰화되어 IDENTIFIER가 아니므로,
    변수 이름 자리와 마찬가지로 별칭 자리에도 쓸 수 없다.
    """
    tokens = [
        Token(TokenType.IMPORT, "import"),
        Token(TokenType.STRING, '"sum.txt"', literal="sum.txt"),
        Token(TokenType.ALIAS, "alias"),
        Token(TokenType.VAR, "var"),
        Token(TokenType.SEMICOLON, ";"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    with pytest.raises(MissingTokenError) as excinfo:
        builder.build()

    assert "Expected alias name" in str(excinfo.value)
    assert excinfo.value.token == Token(TokenType.VAR, "var")


def test_step21_import_missing_semicolon_raises_missing_token_error():
    """소스코드: import "sum.txt" alias sum  (세미콜론 누락)"""
    tokens = [
        Token(TokenType.IMPORT, "import"),
        Token(TokenType.STRING, '"sum.txt"', literal="sum.txt"),
        Token(TokenType.ALIAS, "alias"),
        Token(TokenType.IDENTIFIER, "sum"),
        Token(TokenType.EOF, ""),
    ]
    builder = AstBuilder(tokens)

    with pytest.raises(MissingTokenError) as excinfo:
        builder.build()

    assert "Expected ';' after import statement" in str(excinfo.value)
    assert excinfo.value.token == Token(TokenType.EOF, "")


