from unittest.mock import patch

import pytest

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

    def test_returns_a_tuple_when_the_exponential_probe_lands_exactly_on_the_last_page(self, api):
        # A single-page result: the very first probed page (page 1) already
        # has has_more=False and a non-zero size, so the "exact hit" branch
        # is taken rather than the binary search.
        fake_fetch_page = _paged_dataset(total_records=2, page_size=10)

        with patch.object(api, '_fetch_page', side_effect=fake_fetch_page):
            max_page, last_page_size = api._fetch_all_parallel_search_max(
                {}, 'GET', '/contacts', get_params={'size': 10},
            )

        assert (max_page, last_page_size) == (1, 2)


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

    def test_single_page_dataset(self, api):
        # Previously raised TypeError: the exponential probe's exact-hit
        # branch returned a bare int instead of (page, size).
        fake_fetch_page = _paged_dataset(total_records=2, page_size=10)

        with patch.object(api, '_fetch_page', side_effect=fake_fetch_page):
            result = api._fetch_all_parallel('GET', '/contacts', get_params={'size': 10})

        assert result['content'] == [{'id': 0}, {'id': 1}]

    def test_total_matches_fetched_content_length(self, api):
        fake_fetch_page = _paged_dataset(total_records=25, page_size=10)

        with patch.object(api, '_fetch_page', side_effect=fake_fetch_page):
            result = api._fetch_all_parallel('GET', '/contacts', get_params={'size': 10})

        assert result['paging']['total'] == len(result['content']) == 25

    def test_propagates_exception_from_a_failed_page_fetch(self, api):
        # 45 records at 10/page -> pages 2, 3, 4 are fetched in the parallel
        # phase (after the search-max probe already resolved pages 1 and 5).
        dataset = _paged_dataset(total_records=45, page_size=10)

        def flaky_fetch_page(*, page_num=None, **kwargs):
            if page_num == 2:
                raise RuntimeError('boom')
            return dataset(page_num=page_num, **kwargs)

        with patch.object(api, '_fetch_page', side_effect=flaky_fetch_page):
            with pytest.raises(RuntimeError, match='boom'):
                api._fetch_all_parallel('GET', '/contacts', get_params={'size': 10})
