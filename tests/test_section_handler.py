from unittest.mock import patch

from helpers import FakeResponse, make_page


class TestSectionListHandler:

    def test_fetches_single_entity_by_id(self, api):
        response = FakeResponse(json_data={'id': 'abc-123', 'name': 'Ada'})

        with patch('crm5_bo.crm5_bo.requests.request', return_value=response) as mock_request:
            result = api._section_list_handler('/contacts', section_id='abc-123')

        assert result == {'id': 'abc-123', 'name': 'Ada'}
        mock_request.assert_called_once_with(
            'GET',
            'https://example.crm.com/backoffice/v2/contacts/abc-123',
            json=None,
            headers=api._auth_headers(),
            timeout=api._timeout,
        )

    def test_url_encodes_section_id(self, api):
        response = FakeResponse(json_data={'id': 'sub/with slash'})

        with patch('crm5_bo.crm5_bo.requests.request', return_value=response) as mock_request:
            api._section_list_handler('/subscriptions', section_id='sub/with slash')

        assert mock_request.call_args.args[1] == \
            'https://example.crm.com/backoffice/v2/subscriptions/sub%2Fwith+slash'

    def test_uses_fetch_all_when_no_id_and_not_parallel(self, api):
        page = make_page([{'id': 1}])
        with patch.object(api, '_fetch_all', return_value=page) as mock_fetch_all:
            with patch.object(api, '_fetch_all_parallel') as mock_fetch_all_parallel:
                result = api._section_list_handler('/contacts', search_params={'email_address': 'a@b.com'})

        assert result is page
        mock_fetch_all.assert_called_once()
        mock_fetch_all_parallel.assert_not_called()
        assert mock_fetch_all.call_args.kwargs['get_params'] == {'email_address': 'a@b.com'}

    def test_uses_fetch_all_parallel_when_requested(self, api):
        page = make_page([{'id': 1}])
        with patch.object(api, '_fetch_all_parallel', return_value=page) as mock_fetch_all_parallel:
            with patch.object(api, '_fetch_all') as mock_fetch_all:
                result = api._section_list_handler('/contacts', parallel=True)

        assert result is page
        mock_fetch_all_parallel.assert_called_once()
        mock_fetch_all.assert_not_called()

    def test_list_calls_use_auth_headers(self, api):
        page = make_page([{'id': 1}])
        with patch.object(api, '_fetch_all', return_value=page) as mock_fetch_all:
            api._section_list_handler('/contacts')

        assert mock_fetch_all.call_args.kwargs['headers'] == api._auth_headers()
