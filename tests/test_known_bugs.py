"""Regression tests for known bugs, pinned with strict xfail.

Each test below asserts the *correct* behavior. They currently fail (xfail)
because of a real bug in crm5_bo.py; once the underlying bug is fixed the
test will start passing, and pytest's `strict=True` will flag that as an
XPASS failure - a nudge to delete the xfail marker rather than the bug
silently staying "fixed" with no test catching a regression.
"""
from unittest.mock import patch

import pytest

from helpers import FakeResponse, make_page


@pytest.mark.xfail(
    strict=True,
    reason=(
        "_fetch_all_parallel_search_max returns a bare page number instead "
        "of a (page, size) tuple whenever the exponential probe's first "
        "checked page is already the last page with data (e.g. any "
        "single-page result set). Callers do "
        "`max_page, last_page_size = self._fetch_all_parallel_search_max(...)`, "
        "which raises TypeError. See crm5_bo.py _fetch_all_parallel_search_max."
    ),
)
def test_search_max_returns_a_tuple_for_a_single_page_dataset(api):
    page = make_page([{'id': 1}, {'id': 2}], size=2, has_more=False)

    with patch.object(api, '_fetch_page', return_value=page):
        max_page, last_page_size = api._fetch_all_parallel_search_max(
            {}, 'GET', '/contacts', get_params={'size': 10},
        )

    assert (max_page, last_page_size) == (1, 2)


@pytest.mark.xfail(
    strict=True,
    reason=(
        "_fetch_all_parallel computes paging.total as "
        "`max_page * get_params['size'] + last_page_size`, which counts the "
        "last (possibly partial) page as a full page, overcounting the true "
        "total by one page size. See crm5_bo.py _fetch_all_parallel."
    ),
)
def test_fetch_all_parallel_total_matches_fetched_content_length(api):
    def fake_fetch_page(*, method, url, json_data, headers, get_params, page_num=None):
        page_size = 10
        total_records = 25
        page_num = page_num or 1
        start = (page_num - 1) * page_size
        end = min(start + page_size, total_records)
        content = [{'id': i} for i in range(start, end)] if start < total_records else []
        return make_page(content=content, page=page_num, size=len(content), has_more=end < total_records)

    with patch.object(api, '_fetch_page', side_effect=fake_fetch_page):
        result = api._fetch_all_parallel('GET', '/contacts', get_params={'size': 10})

    assert result['paging']['total'] == len(result['content'])


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
