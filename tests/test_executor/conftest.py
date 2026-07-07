import pytest

from storage import Storage


@pytest.fixture
def storage() -> Storage:
    return Storage()
