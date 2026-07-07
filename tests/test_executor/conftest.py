import pytest

from executor import Storage


@pytest.fixture
def storage() -> Storage:
    return Storage()
