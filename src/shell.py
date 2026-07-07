"""사용자가 직접 접근하는 대화형 셸(REPL).

여러 줄을 입력받아 Pipeline(Assembler -> CheckerUnit -> Executor)에 넘긴다.

- 실제 콘솔 창에서 타이핑할 때: Alt+Enter는 줄바꿈, Enter는 실행/이어쓰기 판단.
- 붙여넣기/파이프처럼 콘솔 raw 입력을 쓸 수 없는 경우: 자동으로 input()으로
  폴백하고, 중괄호가 안 닫혔거나 문장이 세미콜론(;)/닫는 중괄호(})로 끝나지
  않았으면 계속 다음 줄을 받는 기존 방식으로 판단한다.
"""

import ctypes
import sys
from pathlib import Path

# 모듈마다 import 기준 경로가 달라서(예: assembler.py는 'src.ast_builder',
# checker.py는 'nodes...') src 폴더와 프로젝트 루트를 둘 다 등록해야 뜬다.
# 근본 원인(이중 import 문제)은 아직 고치지 않았다.
SRC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SRC_DIR.parent
sys.path.insert(0, str(SRC_DIR))
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline import Pipeline

PROMPT = "codefab> "
CONTINUATION_PROMPT = "....... "
EXIT_COMMANDS = {"exit", "quit"}


# ── Alt+Enter 인식용 Windows 콘솔 raw 입력 ──────────────────────────────
#
# input()은 Enter를 눌러야만 한 줄을 돌려주고 Alt+Enter인지 그냥 Enter인지
# 구분할 수 없다. 그래서 Windows 콘솔 API(ReadConsoleInputW)로 키 입력을
# 하나씩 직접 읽어서 Alt가 눌린 채로 Enter가 눌렸는지 확인한다.
#
# 실제 콘솔 창이 아닌 경우(붙여넣기 파이프, 리다이렉션, 비-Windows 등)에는
# 이 raw 입력을 쓸 수 없으므로 input()으로 자동 폴백한다.

_KEY_EVENT = 0x0001
_LEFT_ALT_PRESSED = 0x0002
_RIGHT_ALT_PRESSED = 0x0001
_VK_RETURN = 0x0D
_VK_BACK = 0x08


class _KeyEventRecord(ctypes.Structure):
    _fields_ = [
        ("bKeyDown", ctypes.c_long),
        ("wRepeatCount", ctypes.c_ushort),
        ("wVirtualKeyCode", ctypes.c_ushort),
        ("wVirtualScanCode", ctypes.c_ushort),
        ("uChar", ctypes.c_wchar),
        ("dwControlKeyState", ctypes.c_ulong),
    ]


class _InputRecord(ctypes.Structure):
    _fields_ = [
        ("EventType", ctypes.c_ushort),
        ("Event", _KeyEventRecord),
    ]


def _get_console_input_handle():
    """실제 콘솔 창에서 실행 중이면 (kernel32, handle)을, 아니면 None을 반환한다."""
    if sys.platform != "win32" or not sys.stdin.isatty():
        return None
    try:
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-10)  # STD_INPUT_HANDLE
        if not handle or handle == -1:
            return None
        return kernel32, handle
    except OSError:
        return None


def _read_key_event(kernel32, handle):
    record = _InputRecord()
    events_read = ctypes.c_ulong(0)
    while True:
        kernel32.ReadConsoleInputW(handle, ctypes.byref(record), 1, ctypes.byref(events_read))
        if record.EventType == _KEY_EVENT and record.Event.bKeyDown:
            return record.Event


def _read_line_with_alt_enter(kernel32, handle, prompt):
    """Alt+Enter는 줄바꿈으로, Enter는 지금까지 입력한 내용을 반환한다."""
    sys.stdout.write(prompt)
    sys.stdout.flush()
    buffer = []

    while True:
        key = _read_key_event(kernel32, handle)
        alt_pressed = bool(key.dwControlKeyState & (_LEFT_ALT_PRESSED | _RIGHT_ALT_PRESSED))

        if key.wVirtualKeyCode == _VK_RETURN and alt_pressed:
            buffer.append("\n")
            sys.stdout.write("\n" + CONTINUATION_PROMPT)
            sys.stdout.flush()
            continue

        if key.wVirtualKeyCode == _VK_RETURN:
            sys.stdout.write("\n")
            sys.stdout.flush()
            return "".join(buffer)

        if key.wVirtualKeyCode == _VK_BACK:
            if buffer and buffer[-1] != "\n":
                buffer.pop()
                sys.stdout.write("\b \b")
                sys.stdout.flush()
            continue

        char = key.uChar
        if char and char != "\x00":
            buffer.append(char)
            sys.stdout.write(char)
            sys.stdout.flush()


def _make_input_reader():
    """콘솔 창이면 Alt+Enter를 지원하는 reader를, 아니면 input()을 돌려준다."""
    console = _get_console_input_handle()
    if console is None:
        return input

    kernel32, handle = console

    def reader(prompt):
        return _read_line_with_alt_enter(kernel32, handle, prompt)

    return reader


def _is_statement_complete(buffered_lines, brace_balance):
    if brace_balance > 0:
        return False
    last_line = buffered_lines[-1].rstrip()
    return last_line.endswith(";") or last_line.endswith("}")


def run_shell():
    pipeline = Pipeline()
    read_line = _make_input_reader()

    print("CodeFab REPL. 종료하려면 exit 또는 quit을 입력하세요.")
    if read_line is not input:
        print("(Alt+Enter: 줄바꿈, Enter: 실행/이어쓰기)")

    buffered_lines = []
    brace_balance = 0

    while True:
        prompt = CONTINUATION_PROMPT if buffered_lines else PROMPT
        try:
            line = read_line(prompt)
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not buffered_lines:
            if line.strip() in EXIT_COMMANDS:
                break
            if not line.strip():
                continue

        buffered_lines.append(line)
        brace_balance += line.count("{") - line.count("}")

        if not _is_statement_complete(buffered_lines, brace_balance):
            continue

        source = "\n".join(buffered_lines)
        buffered_lines = []
        brace_balance = 0

        try:
            errors = pipeline.run(source)
        except Exception as exc:
            # 한 문장 실행이 실패해도 셸 자체는 계속 입력을 받아야 한다.
            print(f"{type(exc).__name__}: {exc}")
            continue

        for error in errors:
            print(error)


if __name__ == "__main__":
    run_shell()
