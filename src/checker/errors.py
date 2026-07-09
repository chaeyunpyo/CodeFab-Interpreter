from source_error import SourceError


class CheckerError(SourceError):
    """검사 중 발견한 오류 하나를 표현한다."""

    UNIT = "Checker"
