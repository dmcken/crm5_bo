from unittest.mock import patch

from helpers import FakeResponse


class TestProductProvisioningProviders:

    def test_gets_providers_for_product(self, api):
        response = FakeResponse(json_data={'content': [{'id': 'provider-1'}]})
        with patch('crm5_bo.crm5_bo.requests.request', return_value=response) as mock_request:
            result = api.product_provisioning_providers('prod-1')

        assert result == {'content': [{'id': 'provider-1'}]}
        mock_request.assert_called_once_with(
            'GET',
            'https://example.crm.com/backoffice/v2/products/prod-1/providers',
            json=None,
            headers=api._auth_headers(),
            timeout=api._timeout,
        )


class TestProductComponents:

    def test_gets_components_for_product(self, api):
        response = FakeResponse(json_data={'content': [{'id': 'component-1'}]})
        with patch('crm5_bo.crm5_bo.requests.request', return_value=response) as mock_request:
            result = api.product_components('prod-1')

        assert result == {'content': [{'id': 'component-1'}]}
        mock_request.assert_called_once_with(
            'GET',
            'https://example.crm.com/backoffice/v2/products/prod-1/components',
            json=None,
            headers=api._auth_headers(),
            timeout=api._timeout,
        )


class TestProductPrices:

    def test_gets_prices_for_product(self, api):
        response = FakeResponse(json_data={'content': [{'id': 'price-1'}]})
        with patch('crm5_bo.crm5_bo.requests.request', return_value=response) as mock_request:
            result = api.product_prices('prod-1')

        assert result == {'content': [{'id': 'price-1'}]}
        mock_request.assert_called_once_with(
            'GET',
            'https://example.crm.com/backoffice/v2/products/prod-1/prices',
            json=None,
            headers=api._auth_headers(),
            timeout=api._timeout,
        )


class TestProducts:

    def test_lists_all_products_via_section_handler(self, api):
        with patch.object(api, '_section_list_handler') as mock_handler:
            api.products()

        mock_handler.assert_called_once_with('/products', search_params={})

    def test_fetches_single_product_by_id(self, api):
        with patch.object(api, '_section_list_handler') as mock_handler:
            api.products('prod-1')

        mock_handler.assert_called_once_with('/products/prod-1', search_params={})


class TestContacts:

    def test_requests_single_page_with_default_page_size(self, api):
        response = FakeResponse(json_data={'content': [], 'paging': {'page': 1, 'size': 100, 'total': 0}})
        with patch('crm5_bo.crm5_bo.requests.request', return_value=response) as mock_request:
            api.contacts(search_params={'email_address': 'a@b.com'})

        mock_request.assert_called_once_with(
            'GET',
            'https://example.crm.com/backoffice/v2/contacts',
            json=None,
            headers=api._auth_headers(),
            timeout=api._timeout,
            params={'email_address': 'a@b.com', 'size': api._default_page_size},
        )

    def test_fetches_single_contact_by_id(self, api):
        response = FakeResponse(json_data={'id': 'contact-1'})
        with patch('crm5_bo.crm5_bo.requests.request', return_value=response) as mock_request:
            api.contacts('contact-1')

        assert mock_request.call_args.args[1] == \
            'https://example.crm.com/backoffice/v2/contacts/contact-1'

    def test_only_returns_a_single_page_even_when_more_records_exist(self, api):
        # Unlike contacts_list(), contacts() does not walk pagination -
        # it silently returns just the first page.
        response = FakeResponse(json_data={
            'content': [{'id': i} for i in range(100)],
            'paging': {'page': 1, 'size': 100, 'total': 250, 'has_more': True},
        })
        with patch('crm5_bo.crm5_bo.requests.request', return_value=response):
            result = api.contacts()

        assert len(result['content']) == 100
        assert result['paging']['total'] == 250


class TestContactSubscriptionList:

    def test_returns_content_list(self, api):
        response = FakeResponse(json_data={'content': [{'id': 'sub-1'}]})
        with patch('crm5_bo.crm5_bo.requests.request', return_value=response) as mock_request:
            result = api.contact_subscription_list('contact-1')

        assert result == [{'id': 'sub-1'}]
        mock_request.assert_called_once_with(
            'GET',
            'https://example.crm.com/backoffice/v2/contacts/contact-1/subscriptions',
            json=None,
            headers=api._auth_headers(),
            timeout=api._timeout,
        )


class TestContactServicesList:

    def test_returns_full_response_body(self, api):
        response = FakeResponse(json_data={'content': [{'id': 'service-1'}]})
        with patch('crm5_bo.crm5_bo.requests.request', return_value=response) as mock_request:
            result = api.contact_services_list('contact-1')

        assert result == {'content': [{'id': 'service-1'}]}
        mock_request.assert_called_once_with(
            'GET',
            'https://example.crm.com/backoffice/v2/contacts/contact-1/services?include_subscription=true',
            json=None,
            headers=api._auth_headers(),
            timeout=api._timeout,
        )


class TestSubscriptionsDevicesList:

    def test_returns_content_list(self, api):
        response = FakeResponse(json_data={'content': [{'id': 'device-1'}]})
        with patch('crm5_bo.crm5_bo.requests.request', return_value=response) as mock_request:
            result = api.subscriptions_devices_list('sub-1')

        assert result == [{'id': 'device-1'}]
        mock_request.assert_called_once_with(
            'GET',
            'https://example.crm.com/backoffice/v2/subscriptions/sub-1/devices',
            json=None,
            headers=None,
            timeout=api._timeout,
        )


class TestListContactServices:

    def test_requests_expected_query_string(self, api):
        response = FakeResponse(json_data={'content': []})
        with patch('crm5_bo.crm5_bo.requests.request', return_value=response) as mock_request:
            api.list_contact_services('contact-1')

        mock_request.assert_called_once_with(
            'GET',
            'https://example.crm.com/backoffice/v2/contacts/contact-1/services?'
            'include_order_info=true&include_subscription=true&include_total=true',
            json=None,
            headers=api._auth_headers(),
            timeout=api._timeout,
        )


class TestListServiceDevices:

    def test_gets_devices_for_service(self, api):
        response = FakeResponse(json_data={'content': [{'id': 'device-1'}]})
        with patch('crm5_bo.crm5_bo.requests.request', return_value=response) as mock_request:
            result = api.list_service_devices('service-1')

        assert result == {'content': [{'id': 'device-1'}]}
        mock_request.assert_called_once_with(
            'GET',
            'https://example.crm.com/backoffice/v2/services/service-1/devices',
            json=None,
            headers=api._auth_headers(),
            timeout=api._timeout,
        )


class TestSubscription:

    def test_lists_all_subscriptions_when_no_id_given(self, api):
        response = FakeResponse(json_data={'content': []})
        with patch('crm5_bo.crm5_bo.requests.request', return_value=response) as mock_request:
            api.subscription()

        assert mock_request.call_args.args[1] == \
            'https://example.crm.com/backoffice/v2/subscriptions'

    def test_url_encodes_subscription_id(self, api):
        response = FakeResponse(json_data={'id': 'sub/with slash'})
        with patch('crm5_bo.crm5_bo.requests.request', return_value=response) as mock_request:
            api.subscription('sub/with slash')

        assert mock_request.call_args.args[1] == \
            'https://example.crm.com/backoffice/v2/subscriptions/sub%2Fwith+slash'
