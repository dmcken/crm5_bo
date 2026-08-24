"""Regression tests for known bugs, pinned with strict xfail.

Each test below asserts the *correct* behavior. They currently fail (xfail)
because of a real bug in crm5_bo.py; once the underlying bug is fixed the
test will start passing, and pytest's `strict=True` will flag that as an
XPASS failure - a nudge to delete the xfail marker rather than the bug
silently staying "fixed" with no test catching a regression.
"""
from unittest.mock import patch

import pytest

from helpers import FakeResponse


@pytest.mark.xfail(
    strict=True,
    reason=(
        "login() is typed `-> bool` and its docstring promises True/False, "
        "but the method always ends in a bare `return`, so it returns None "
        "on success instead of True. See crm5_bo.py CRM5BackofficeAdmin.login."
    ),
)
def test_login_returns_true_on_success(api):
    response = FakeResponse(json_data={
        'access_token': 'token',
        'refresh_token': 'refresh',
        'expiration_date': '2026-12-31',
        'mode': 'LIVE',
        'lockout_date': None,
        'password_expired': False,
    })

    with patch('crm5_bo.crm5_bo.requests.request', return_value=response):
        result = api.login('user@example.com', 'hunter2', 'api-key', 'secret-key')

    assert result is True
