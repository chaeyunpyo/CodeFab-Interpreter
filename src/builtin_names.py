"""전역 스코프에 기본으로 등록되는 built-in 이름 목록.

Checker(재선언/재정의 금지 검사)와 Executor(Storage 초기 전역 스코프
등록, `executor/_storage.py`)가 이름 목록 하나를 공유하기 위한 모듈이다.
실제 built-in 값(ArrayBuiltin 등)은 executor 쪽에만 있고, 여기는 이름만
안다 — Checker가 Executor에 의존하면 단방향 계층(Assembler -> Checker
-> Executor)이 깨지기 때문이다.

새 built-in을 추가하면 여기 이름을 추가하고, `executor/_storage.py`의
초기 전역 스코프에도 실제 값을 등록해야 한다. 둘이 어긋나지 않는지는
tests/test_executor/test_storage.py에서 확인한다.
"""

BUILTIN_GLOBAL_NAMES = frozenset({"Array"})
