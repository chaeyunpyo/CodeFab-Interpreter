"""제어 흐름 시그널.

Python 예외를 빌려 함수 실행 도중 임의의 깊이(중첩 if/for/block)에서
곧바로 호출부까지 값을 들고 빠져나오는 용도로 사용한다.
일반적인 오류(ExecutionError)와 달리 프로그램 오류가 아니라
정상적인 제어 흐름의 일부이므로 별도 타입으로 둔다.
"""

from typing import Any


class ReturnSignal(Exception):
    """ReturnStmt 실행 시 발생시켜 함수 호출부까지 반환값을 전달한다.

    CallExpr 핸들러가 함수 body 실행을 감싸 이 시그널을 잡고
    value를 호출 결과로 사용한다.
    """

    def __init__(self, value: Any = None):
        super().__init__()
        self.value = value
