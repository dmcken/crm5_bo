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


class TestContactSubscriptions:

    def test_returns_content_list(self, api):
        response = FakeResponse(json_data={'content': [{'id': 'sub-1'}]})
        with patch('crm5_bo.crm5_bo.requests.request', return_value=response) as mock_request:
            result = api.contact_subscriptions('contact-1')

        assert result == [{'id': 'sub-1'}]
        mock_request.assert_called_once_with(
            'GET',
            'https://example.crm.com/backoffice/v2/contacts/contact-1/subscriptions',
            json=None,
            headers=api._auth_headers(),
            timeout=api._timeout,
        )


class TestContactServices:

    def test_requests_expected_query_string(self, api):
        # Paginates via _fetch_all (like products()/contacts()) rather than
        # a one-off request, so a contact with more than one page of
        # services doesn't silently lose everything past page 1 - see
        # CHANGELOG. has_more=False here means a single page is enough to
        # satisfy the fetch-all loop.
        response = FakeResponse(json_data={
            'content': [{'id': 'service-1'}],
            'paging': {'page': 1, 'size': 100, 'total': 1, 'has_more': False},
        })
        with patch('crm5_bo.crm5_bo.requests.request', return_value=response) as mock_request:
            result = api.contact_services('contact-1')

        assert result['content'] == [{'id': 'service-1'}]
        mock_request.assert_called_once_with(
            'GET',
            'https://example.crm.com/backoffice/v2/contacts/contact-1/services',
            json=None,
            headers=api._auth_headers(),
            params={
                'include_order_info': 'true',
                'include_subscription': 'true',
                'include_total': 'true',
                'size': 100,
            },
            timeout=api._timeout,
        )

    def test_fetches_a_second_page_when_has_more(self, api):
        # The actual bug this fixes: a contact with e.g. 15 services and a
        # page size of 10 previously had items 11-15 silently dropped.
        page1 = FakeResponse(json_data={
            'content': [{'id': f'service-{i}'} for i in range(10)],
            'paging': {'page': 1, 'size': 10, 'total': 15, 'has_more': True},
        })
        page2 = FakeResponse(json_data={
            'content': [{'id': f'service-{i}'} for i in range(10, 15)],
            'paging': {'page': 2, 'size': 10, 'total': 15, 'has_more': False},
        })
        with patch('crm5_bo.crm5_bo.requests.request', side_effect=[page1, page2]) as mock_request:
            result = api.contact_services('contact-1')

        assert len(result['content']) == 15
        assert mock_request.call_count == 2
        second_call_params = mock_request.call_args_list[1].kwargs['params']
        assert second_call_params['page'] == 2


class TestSubscriptionDevices:

    def test_returns_content_list(self, api):
        response = FakeResponse(json_data={'content': [{'id': 'device-1'}]})
        with patch('crm5_bo.crm5_bo.requests.request', return_value=response) as mock_request:
            result = api.subscription_devices('sub-1')

        assert result == [{'id': 'device-1'}]
        mock_request.assert_called_once_with(
            'GET',
            'https://example.crm.com/backoffice/v2/subscriptions/sub-1/devices',
            json=None,
            headers=api._auth_headers(),
            timeout=api._timeout,
        )
