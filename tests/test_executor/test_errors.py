from executor import ArityMismatchError, NotCallableError
from nodes.token_type import TokenType

from helpers import tok


# ── 함수 호출 관련 런타임 오류 (요구사항_정리/function.md) ─────────────────────────
# CallExpr 핸들러(담당 A)가 실제로 발생시키는 오류지만, 클래스 자체의 메시지/속성은
# 여기서 담당 B가 검증한다.

class TestNotCallableError:
    def test_메시지에_호출_불가_안내가_담긴다(self):
        error = NotCallableError(tok(TokenType.LEFT_PAREN, "("))
        assert "call" in str(error).lower()

    def test_토큰의_줄_번호를_사용한다(self):
        token = tok(TokenType.LEFT_PAREN, "(")
        token.line = 7
        error = NotCallableError(token)
        assert error.line == 7


class TestArityMismatchError:
    def test_기대한_인자_수와_실제_인자_수를_담는다(self):
        error = ArityMismatchError(expected=3, got=2, token=tok(TokenType.LEFT_PAREN, "("))
        assert error.expected == 3
        assert error.got == 2
        assert "3" in str(error) and "2" in str(error)
