import shutil

import pytest


@pytest.fixture(autouse=True)
def _cleanup_tmp_path(tmp_path):
    """각 테스트가 tmp_path에 만든 import 대상 파일들을 테스트가 끝나면 바로 지운다.

    pytest의 tmp_path는 기본적으로 최근 몇 세션분의 디렉터리를 디스크에
    남겨두므로(사후 디버깅용 보존 정책), 이 파일에서 테스트마다 새로
    만드는 .txt 파일들이 계속 쌓인다. 이 테스트들은 실제 파일 I/O
    자체를 검증하므로, 디스크에 흔적을 남기지 않도록 테스트가 끝나는
    즉시(성공/실패 여부와 무관하게) 정리한다.
    """
    yield
    shutil.rmtree(tmp_path, ignore_errors=True)
