import logging
from unittest.mock import patch

import pytest

# (deprecated_name, canonical_name, kwargs to call the deprecated method,
#  positional args the alias is expected to forward to the canonical method)
DEPRECATED_ALIASES = [
    ('activities_list', 'activities',
        {'activity_id': 'a1', 'search_params': {'q': 1}, 'parallel': True}, ('a1', {'q': 1}, True)),
    ('contacts_list', 'contacts',
        {'contact_id': 'c1', 'search_params': {'q': 1}, 'parallel': True}, ('c1', {'q': 1}, True)),
    ('contact_services_list', 'contact_services', {'contact_id': 'c1'}, ('c1',)),
    ('list_contact_services', 'contact_services', {'contact_id': 'c1'}, ('c1',)),
    ('contact_subscription_list', 'contact_subscriptions', {'contact_id': 'c1'}, ('c1',)),
    ('devices_list', 'devices',
        {'device_id': 'd1', 'search_params': {'q': 1}, 'parallel': True}, ('d1', {'q': 1}, True)),
    ('journals_list', 'journals',
        {'journal_id': 'j1', 'search_params': {'q': 1}, 'parallel': True}, ('j1', {'q': 1}, True)),
    ('orders_list', 'orders', {'order_id': 'o1', 'search_params': {'q': 1}}, ('o1', {'q': 1})),
    ('products_list', 'products', {'product_id': 'p1', 'search_params': {'q': 1}}, ('p1', {'q': 1})),
    ('sales_model', 'sales_models', {}, ()),
    ('service_device_list', 'service_devices', {'service_id': 's1'}, ('s1',)),
    ('list_service_devices', 'service_devices', {'service_id': 's1'}, ('s1',)),
    ('service_requests_list', 'service_requests',
        {'service_requests_id': 'sr1', 'search_params': {'q': 1}, 'parallel': True}, ('sr1', {'q': 1}, True)),
    ('subscriptions_list', 'subscriptions',
        {'subscriptions_id': 'sub1', 'search_params': {'q': 1}, 'parallel': True}, ('sub1', {'q': 1}, True)),
    ('subscription', 'subscriptions', {'subscription_id': 'sub1'}, ('sub1',)),
    ('subscriptions_devices_list', 'subscription_devices', {'subscription_id': 'sub1'}, ('sub1',)),
    ('teams_list', 'teams', {'user_id': 'u1', 'search_params': {'q': 1}}, ('u1', {'q': 1})),
    ('users_list', 'users', {'user_id': 'u1', 'search_params': {'q': 1}}, ('u1', {'q': 1})),
]


class TestDeprecatedAliasesDelegate:

    @pytest.mark.parametrize('deprecated_name, canonical_name, call_kwargs, expected_args', DEPRECATED_ALIASES)
    def test_forwards_to_the_canonical_method_and_returns_its_result(
        self, api, deprecated_name, canonical_name, call_kwargs, expected_args,
    ):
        sentinel = object()
        with patch.object(api, canonical_name, return_value=sentinel) as mock_canonical, pytest.warns(DeprecationWarning):
            result = getattr(api, deprecated_name)(**call_kwargs)

        assert result is sentinel
        mock_canonical.assert_called_once_with(*expected_args)


class TestDeprecatedAliasesWarn:

    @pytest.mark.parametrize('deprecated_name, canonical_name, call_kwargs, expected_args', DEPRECATED_ALIASES)
    def test_emits_a_deprecation_warning_naming_the_replacement(
        self, api, deprecated_name, canonical_name, call_kwargs, expected_args,
    ):
        with patch.object(api, canonical_name), pytest.warns(DeprecationWarning, match=rf"\.{deprecated_name}\(\).*\.{canonical_name}\(\)"):
            getattr(api, deprecated_name)(**call_kwargs)

    @pytest.mark.parametrize('deprecated_name, canonical_name, call_kwargs, expected_args', DEPRECATED_ALIASES)
    def test_logs_a_warning_naming_the_replacement(
        self, api, deprecated_name, canonical_name, call_kwargs, expected_args, caplog,
    ):
        with patch.object(api, canonical_name), caplog.at_level(logging.WARNING, logger='crm5_bo.crm5_bo'), pytest.warns(DeprecationWarning):
            getattr(api, deprecated_name)(**call_kwargs)

        assert any(
            deprecated_name in record.message and canonical_name in record.message
            for record in caplog.records
        )
