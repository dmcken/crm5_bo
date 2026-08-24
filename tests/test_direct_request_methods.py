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
        response = FakeResponse(json_data={'content': [{'id': 'service-1'}]})
        with patch('crm5_bo.crm5_bo.requests.request', return_value=response) as mock_request:
            result = api.contact_services('contact-1')

        assert result == {'content': [{'id': 'service-1'}]}
        mock_request.assert_called_once_with(
            'GET',
            'https://example.crm.com/backoffice/v2/contacts/contact-1/services?'
            'include_order_info=true&include_subscription=true&include_total=true',
            json=None,
            headers=api._auth_headers(),
            timeout=api._timeout,
        )


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
