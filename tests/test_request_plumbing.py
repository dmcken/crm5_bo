from unittest.mock import patch

import pytest

from crm5_bo import CRM5APIError

from helpers import FakeResponse, make_page


class TestMakeRequest:

    def test_returns_response_on_200(self, api):
        response = FakeResponse(status_code=200, json_data={'ok': True})

        with patch('crm5_bo.crm5_bo.requests.request', return_value=response) as mock_request:
            result = api._make_request('GET', '/contacts', get_params={'size': 100})

        assert result is response
        mock_request.assert_called_once_with(
            'GET',
            'https://example.crm.com/backoffice/v2/contacts',
            json=None,
            headers=None,
            timeout=api._timeout,
            params={'size': 100},
        )

    def test_omits_params_key_when_get_params_is_none(self, api):
        response = FakeResponse(status_code=200, json_data={'ok': True})

        with patch('crm5_bo.crm5_bo.requests.request', return_value=response) as mock_request:
            api._make_request('GET', '/contacts')

        assert 'params' not in mock_request.call_args.kwargs

    def test_raises_crm5_api_error_on_non_200(self, api):
        response = FakeResponse(status_code=404, text='not found')

        with patch('crm5_bo.crm5_bo.requests.request', return_value=response):
            with pytest.raises(CRM5APIError, match="404.*not found"):
                api._make_request('GET', '/contacts/missing')

    def test_passes_through_method_json_and_headers(self, api):
        response = FakeResponse(status_code=200, json_data={'id': '123'})
        headers = api._auth_headers()

        with patch('crm5_bo.crm5_bo.requests.request', return_value=response) as mock_request:
            api._make_request('PUT', '/contacts/123', json_data={'name': 'x'}, headers=headers)

        mock_request.assert_called_once_with(
            'PUT',
            'https://example.crm.com/backoffice/v2/contacts/123',
            json={'name': 'x'},
            headers=headers,
            timeout=api._timeout,
        )


class TestFetchPage:

    def test_defaults_page_size_when_not_supplied(self, api):
        page = make_page([{'id': 1}])
        with patch.object(api, '_make_request') as mock_request:
            mock_request.return_value.json.return_value = page
            api._fetch_page('GET', '/contacts')

        assert mock_request.call_args.args[-1] == {'size': api._default_page_size}

    def test_adds_page_num_when_given(self, api):
        page = make_page([{'id': 1}])
        with patch.object(api, '_make_request') as mock_request:
            mock_request.return_value.json.return_value = page
            api._fetch_page('GET', '/contacts', get_params={'size': 50}, page_num=3)

        assert mock_request.call_args.args[-1] == {'size': 50, 'page': 3}

    def test_raises_when_content_is_none(self, api):
        page = make_page([], has_more=False)
        page['content'] = None
        with patch.object(api, '_make_request') as mock_request:
            mock_request.return_value.json.return_value = page
            with pytest.raises(CRM5APIError):
                api._fetch_page('GET', '/contacts')

    def test_falls_back_total_to_size_when_total_is_none(self, api):
        page = make_page([{'id': 1}], size=7)
        page['paging']['total'] = None
        with patch.object(api, '_make_request') as mock_request:
            mock_request.return_value.json.return_value = page
            result = api._fetch_page('GET', '/contacts')

        assert result['paging']['total'] == 7


class TestFetchAll:

    def test_single_page_returned_as_is(self, api):
        page = make_page([{'id': 1}, {'id': 2}], has_more=False)
        with patch.object(api, '_fetch_page', return_value=page) as mock_fetch_page:
            result = api._fetch_all('GET', '/contacts')

        assert result['content'] == [{'id': 1}, {'id': 2}]
        mock_fetch_page.assert_called_once()

    def test_collects_all_pages_until_has_more_is_false(self, api):
        pages = [
            make_page([{'id': 1}], has_more=True),
            make_page([{'id': 2}], has_more=True),
            make_page([{'id': 3}], has_more=False),
        ]

        with patch.object(api, '_fetch_page', side_effect=pages) as mock_fetch_page:
            result = api._fetch_all('GET', '/contacts', get_params={'size': 1})

        assert result['content'] == [{'id': 1}, {'id': 2}, {'id': 3}]
        assert result['paging']['total'] == 3
        assert mock_fetch_page.call_count == 3

        # First call has no explicit page_num, subsequent calls walk pages 2, 3.
        assert mock_fetch_page.call_args_list[1].kwargs['page_num'] == 2
        assert mock_fetch_page.call_args_list[2].kwargs['page_num'] == 3
