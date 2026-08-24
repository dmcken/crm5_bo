from unittest.mock import patch

import pytest

# (method name, rel_url, id kwarg name)
LIST_METHODS = [
    ('activities', '/activities', 'activity_id'),
    ('contacts', '/contacts', 'contact_id'),
    ('devices', '/devices', 'device_id'),
    ('journals', '/journals', 'journal_id'),
    ('orders', '/orders', 'order_id'),
    ('products', '/products', 'product_id'),
    ('service_requests', '/service_requests', 'service_request_id'),
    ('subscriptions', '/subscriptions', 'subscription_id'),
    ('teams', '/teams', 'user_id'),
    ('users', '/users', 'user_id'),
]


class TestListMethodsDelegateToSectionHandler:

    @pytest.mark.parametrize('method_name, rel_url, id_kwarg', LIST_METHODS)
    def test_forwards_rel_url_id_and_search_params(self, api, method_name, rel_url, id_kwarg):
        sentinel = object()
        with patch.object(api, '_section_list_handler', return_value=sentinel) as mock_handler:
            result = getattr(api, method_name)(**{id_kwarg: 'the-id'}, search_params={'q': 'x'}, parallel=True)

        assert result is sentinel
        mock_handler.assert_called_once_with(
            rel_url,
            section_id='the-id',
            search_params={'q': 'x'},
            parallel=True,
        )

    @pytest.mark.parametrize('method_name, rel_url, id_kwarg', LIST_METHODS)
    def test_defaults_to_no_id_no_search_params_and_no_parallel(self, api, method_name, rel_url, id_kwarg):
        with patch.object(api, '_section_list_handler') as mock_handler:
            getattr(api, method_name)()

        mock_handler.assert_called_once_with(
            rel_url,
            section_id=None,
            search_params=None,
            parallel=False,
        )


class TestCustomFields:

    def test_lists_all_when_no_id_given(self, api):
        with patch.object(api, '_section_list_handler') as mock_handler:
            api.custom_fields()

        mock_handler.assert_called_once_with('/custom_fields')

    def test_fetches_single_field_when_id_given(self, api):
        with patch.object(api, '_section_list_handler') as mock_handler:
            api.custom_fields('field-123')

        mock_handler.assert_called_once_with('/custom_fields/field-123')


class TestSalesModels:

    def test_delegates_to_section_handler(self, api):
        sentinel = object()
        with patch.object(api, '_section_list_handler', return_value=sentinel) as mock_handler:
            result = api.sales_models()

        assert result is sentinel
        mock_handler.assert_called_once_with('/sales_models', search_params=None, parallel=False)


class TestServiceDevices:

    def test_builds_nested_resource_url(self, api):
        with patch.object(api, '_section_list_handler') as mock_handler:
            api.service_devices('service-123')

        mock_handler.assert_called_once_with('/services/service-123/devices')


class TestServiceRecommendation:

    def test_filters_to_accepted_params_only(self, api):
        with patch.object(api, '_section_list_handler') as mock_handler:
            api.service_recommendation(product_id='p-1', service_id='s-1', bogus='ignored')

        mock_handler.assert_called_once_with(
            '/services/recommendation',
            search_params={'product_id': 'p-1', 'service_id': 's-1'},
        )

    def test_omits_missing_optional_params(self, api):
        with patch.object(api, '_section_list_handler') as mock_handler:
            api.service_recommendation(product_id='p-1')

        mock_handler.assert_called_once_with(
            '/services/recommendation',
            search_params={'product_id': 'p-1'},
        )
