"""Checker/Executor가 공통으로 쓰는 오류 베이스.

소스 코드의 특정 토큰(줄)에서 발생한 오류를, 어느 Unit에서 났는지와
함께 표현한다. 하위 클래스에서 UNIT 클래스 변수만 지정하면 된다.
"""


class SourceError(Exception):
    UNIT = "Unknown"

    def __init__(self, message, token=None):
        super().__init__(message)
        self.message = message
        self.token = token

    @property
    def line(self):
        return self.token.line if self.token is not None else None

    def __str__(self):
        location = f"Line {self.line}" if self.token is not None else "Line ?"
        return f"[{self.UNIT}] {location}: {self.message}"
