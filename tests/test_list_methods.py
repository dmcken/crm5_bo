from unittest.mock import patch

import pytest

# (method name, rel_url, id kwarg name, supports parallel)
LIST_METHODS = [
    ('activities_list', '/activities', 'activity_id', True),
    ('contacts_list', '/contacts', 'contact_id', True),
    ('devices_list', '/devices', 'device_id', True),
    ('journals_list', '/journals', 'journal_id', True),
    ('orders_list', '/orders', 'order_id', False),
    ('products_list', '/products', 'product_id', False),
    ('service_requests_list', '/service_requests', 'service_requests_id', True),
    ('subscriptions_list', '/subscriptions', 'subscriptions_id', True),
    ('teams_list', '/teams', 'user_id', False),
    ('users_list', '/users', 'user_id', False),
]


class TestListMethodsDelegateToSectionHandler:

    @pytest.mark.parametrize('method_name, rel_url, id_kwarg, supports_parallel', LIST_METHODS)
    def test_forwards_rel_url_id_and_search_params(self, api, method_name, rel_url, id_kwarg, supports_parallel):
        sentinel = object()
        with patch.object(api, '_section_list_handler', return_value=sentinel) as mock_handler:
            kwargs = {id_kwarg: 'the-id', 'search_params': {'q': 'x'}}
            expected_kwargs = {'section_id': 'the-id', 'search_params': {'q': 'x'}}
            if supports_parallel:
                kwargs['parallel'] = True
                expected_kwargs['parallel'] = True
            result = getattr(api, method_name)(**kwargs)

        assert result is sentinel
        mock_handler.assert_called_once_with(rel_url, **expected_kwargs)

    @pytest.mark.parametrize('method_name, rel_url, id_kwarg, supports_parallel', LIST_METHODS)
    def test_defaults_to_no_id_and_no_search_params(self, api, method_name, rel_url, id_kwarg, supports_parallel):
        with patch.object(api, '_section_list_handler') as mock_handler:
            getattr(api, method_name)()

        expected_kwargs = {'section_id': None, 'search_params': None}
        if supports_parallel:
            expected_kwargs['parallel'] = False
        mock_handler.assert_called_once_with(rel_url, **expected_kwargs)


class TestCustomFields:

    def test_lists_all_when_no_id_given(self, api):
        with patch.object(api, '_section_list_handler') as mock_handler:
            api.custom_fields()

        mock_handler.assert_called_once_with('/custom_fields')

    def test_fetches_single_field_when_id_given(self, api):
        with patch.object(api, '_section_list_handler') as mock_handler:
            api.custom_fields('field-123')

        mock_handler.assert_called_once_with('/custom_fields/field-123')


class TestSalesModel:

    def test_delegates_to_section_handler(self, api):
        sentinel = object()
        with patch.object(api, '_section_list_handler', return_value=sentinel) as mock_handler:
            result = api.sales_model()

        assert result is sentinel
        mock_handler.assert_called_once_with('/sales_models')


class TestServiceDeviceList:

    def test_builds_nested_resource_url(self, api):
        with patch.object(api, '_section_list_handler') as mock_handler:
            api.service_device_list('service-123')

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
