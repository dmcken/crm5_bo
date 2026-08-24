import pytest

from crm5_bo import CRM5BackofficeAdmin


@pytest.fixture
def api():
    """An authenticated client instance, ready to make requests."""
    client = CRM5BackofficeAdmin('example.crm.com')
    client._access_token = 'test-access-token'
    client._secret_key = 'test-secret-key'
    return client
