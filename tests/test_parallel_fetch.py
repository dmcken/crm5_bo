from unittest.mock import patch

from helpers import make_page


def _paged_dataset(total_records, page_size):
    """A `_fetch_page`-compatible side_effect over a fixed-size dataset."""

    def fake_fetch_page(*, method, url, json_data, headers, get_params, page_num=None):
        page_num = page_num or 1
        start = (page_num - 1) * page_size
        end = min(start + page_size, total_records)
        content = [{'id': i} for i in range(start, end)] if start < total_records else []
        has_more = end < total_records
        return make_page(content=content, page=page_num, size=len(content), has_more=has_more)

    return fake_fetch_page


class TestFetchAllParallelSearchMax:

    def test_binary_search_finds_last_partial_page(self, api):
        # 25 records at 10/page -> 3 pages (10, 10, 5), so the exponential
        # probe (1, 10, ...) overshoots and the binary search must narrow
        # back down to page 3.
        fake_fetch_page = _paged_dataset(total_records=25, page_size=10)

        with patch.object(api, '_fetch_page', side_effect=fake_fetch_page):
            max_page, last_page_size = api._fetch_all_parallel_search_max(
                {}, 'GET', '/contacts', get_params={'size': 10},
            )

        assert (max_page, last_page_size) == (3, 5)

    def test_binary_search_finds_last_full_page(self, api):
        # 30 records at 10/page -> exactly 3 full pages, no empty tail page.
        fake_fetch_page = _paged_dataset(total_records=30, page_size=10)

        with patch.object(api, '_fetch_page', side_effect=fake_fetch_page):
            max_page, last_page_size = api._fetch_all_parallel_search_max(
                {}, 'GET', '/contacts', get_params={'size': 10},
            )

        assert (max_page, last_page_size) == (3, 10)


class TestFetchAllParallel:

    def test_fetches_complete_content_across_pages(self, api):
        fake_fetch_page = _paged_dataset(total_records=25, page_size=10)

        with patch.object(api, '_fetch_page', side_effect=fake_fetch_page):
            result = api._fetch_all_parallel('GET', '/contacts', get_params={'size': 10})

        assert sorted(result['content'], key=lambda r: r['id']) == [{'id': i} for i in range(25)]

    def test_two_page_dataset(self, api):
        # 15 records at 10/page: the exponential probe overshoots to an
        # empty page 10 first, forcing a binary search back down to page 2.
        fake_fetch_page = _paged_dataset(total_records=15, page_size=10)

        with patch.object(api, '_fetch_page', side_effect=fake_fetch_page):
            result = api._fetch_all_parallel('GET', '/contacts', get_params={'size': 10})

        assert sorted(result['content'], key=lambda r: r['id']) == [{'id': i} for i in range(15)]
