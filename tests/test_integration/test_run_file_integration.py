"""cli.run_file()을 통해 파일 전체를 한 번에 읽어 실행하는 경로의 블랙박스 테스트.

기존 tests/test_integration/의 나머지 테스트들은 모두 PromptShell(REPL)을
통해 소스 문자열을 실행하는데, run_file()은 REPL의 "다음 줄을 더 기다린다"
버퍼링 로직 없이 Pipeline을 곧바로 호출한다(수정 전에는 run_file이
PromptShell을 재사용해서, 파일이 이미 다 읽혔는데도 "더 기다리는 중"으로
오판해 조용히 아무 것도 출력하지 않고 끝나버리는 버그가 있었다).
tests/test_cli/test_file_mode.py에 있는 기존 테스트들은 이 버그에 대해
`!= ""`라는 느슨한 assertion만 쓰는데, 여기서는 실제 오류 메시지까지
정확히 검증한다.
"""

from cli import run_file


def test_run_file_executes_a_complex_program_with_recursion_and_array(tmp_path, capsys):
    """재귀 함수(fib) + 정적 배열 + for 루프가 섞인 여러 줄짜리 프로그램도
    한 번에 정상적으로 실행되어야 한다.
    """
    script = tmp_path / "fib.txt"
    script.write_text(
        """
        Func fib(n) {
          if (n < 2) return n;
          return fib(n - 1) + fib(n - 2);
        }
        var arr = Array(3);
        for (var i = 0; i < 3; i = i + 1) {
          arr[i] = fib(i);
        }
        print arr;
        """,
        encoding="utf-8",
    )

    run_file(str(script))

    assert capsys.readouterr().out == "[0, 1, 1]\n"


def test_run_file_reports_precise_error_for_unclosed_block(tmp_path, capsys):
    """블록의 '{'가 파일 끝까지 닫히지 않으면, 실제 줄 번호와 메시지가 있는
    Assembler 오류가 나와야 한다 (단순히 뭔가 출력됐는지만 보는 것이 아니라).
    """
    script = tmp_path / "script.txt"
    script.write_text('print 1;\nif (true) {\n', encoding="utf-8")

    run_file(str(script))

    assert capsys.readouterr().out == "[Assembler] Line 3: Expected '}' after block\n"


def test_run_file_reports_precise_error_for_if_without_body_at_eof(tmp_path, capsys):
    """then_branch 없이 파일이 끝난 if문은 EOF 토큰을 만난 채 파싱이
    실패해야 하고, 그 오류 메시지가 그대로 출력되어야 한다.
    """
    script = tmp_path / "script.txt"
    script.write_text("if (true)", encoding="utf-8")

    run_file(str(script))

    assert (
        capsys.readouterr().out
        == "[Assembler] Line 1: Unexpected token: Token(type=<TokenType.EOF: 45>, lexeme='', literal=None, line=1)\n"
    )
