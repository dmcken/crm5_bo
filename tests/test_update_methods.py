from unittest.mock import patch

import pytest
from helpers import FakeResponse


class TestActivityUpdate:

    def test_returns_true_when_response_id_matches(self, api):
        response = FakeResponse(json_data={'id': 'activity-1'})
        with patch('crm5_bo.crm5_bo.requests.request', return_value=response) as mock_request:
            result = api.activity_update('activity-1', {'status': 'DONE'})

        assert result is True
        mock_request.assert_called_once_with(
            'PUT',
            'https://example.crm.com/backoffice/v2/activities/activity-1',
            json={'status': 'DONE'},
            headers=api._auth_headers(),
            timeout=api._timeout,
        )

    def test_returns_false_when_response_id_does_not_match(self, api):
        response = FakeResponse(json_data={'id': 'some-other-id'})
        with patch('crm5_bo.crm5_bo.requests.request', return_value=response):
            result = api.activity_update('activity-1', {'status': 'DONE'})

        assert result is False


class TestContactUpdate:

    def test_returns_true_when_response_id_matches(self, api):
        response = FakeResponse(json_data={'id': 'contact-1'})
        with patch('crm5_bo.crm5_bo.requests.request', return_value=response) as mock_request:
            result = api.contact_update('contact-1', {'email_address': 'a@b.com'})

        assert result is True
        mock_request.assert_called_once_with(
            'PUT',
            'https://example.crm.com/backoffice/v2/contacts/contact-1',
            json={'email_address': 'a@b.com'},
            headers=api._auth_headers(),
            timeout=api._timeout,
        )

    def test_returns_false_when_response_id_does_not_match(self, api):
        response = FakeResponse(json_data={'id': 'some-other-id'})
        with patch('crm5_bo.crm5_bo.requests.request', return_value=response):
            result = api.contact_update('contact-1', {'email_address': 'a@b.com'})

        assert result is False


class TestSubscriptionUpdate:

    def test_puts_update_body_and_returns_json(self, api):
        response = FakeResponse(json_data={'id': 'sub-1', 'action': 'CANCEL'})
        with patch('crm5_bo.crm5_bo.requests.request', return_value=response) as mock_request:
            result = api.subscription_update('sub-1', {'action': 'CANCEL'})

        assert result == {'id': 'sub-1', 'action': 'CANCEL'}
        mock_request.assert_called_once_with(
            'PUT',
            'https://example.crm.com/backoffice/v2/subscriptions/sub-1',
            json={'action': 'CANCEL'},
            headers=api._auth_headers(),
            timeout=api._timeout,
        )


class TestServiceRequestUpdate:

    def test_puts_update_body_and_returns_json(self, api):
        response = FakeResponse(json_data={'id': 'sr-1', 'status': 'ESCALATED'})
        with patch('crm5_bo.crm5_bo.requests.request', return_value=response) as mock_request:
            result = api.service_request_update('sr-1', {'status': 'ESCALATED'})

        assert result == {'id': 'sr-1', 'status': 'ESCALATED'}
        mock_request.assert_called_once_with(
            'PUT',
            'https://example.crm.com/backoffice/v2/service_requests/sr-1',
            json={'status': 'ESCALATED'},
            headers=api._auth_headers(),
            timeout=api._timeout,
        )


class TestServiceUpdate:

    def test_puts_update_body_and_returns_json(self, api):
        response = FakeResponse(json_data={'id': 'service-1', 'status': 'ACTIVE'})
        with patch('crm5_bo.crm5_bo.requests.request', return_value=response) as mock_request:
            result = api.service_update('service-1', {'status': 'ACTIVE'})

        assert result == {'id': 'service-1', 'status': 'ACTIVE'}
        mock_request.assert_called_once_with(
            'PUT',
            'https://example.crm.com/backoffice/v2/services/service-1',
            json={'status': 'ACTIVE'},
            headers=api._auth_headers(),
            timeout=api._timeout,
        )

    def test_has_no_merge_custom_fields_option(self, api):
        # Unlike the other *_update methods: there's no GET /services/{id}
        # to fetch a service's current state from, so it can't merge
        # automatically. Sending custom_fields here is always a raw replace.
        response = FakeResponse(json_data={'id': 'service-1'})
        with patch('crm5_bo.crm5_bo.requests.request', return_value=response) as mock_request:
            api.service_update('service-1', {'custom_fields': [{'key': 'a', 'value': 'b'}]})

        assert mock_request.call_count == 1
        assert mock_request.call_args.kwargs['json']['custom_fields'] == [{'key': 'a', 'value': 'b'}]


# (update_method, id, get_method, get_call_args, get_call_kwargs)
CUSTOM_FIELDS_MERGE_CASES = [
    ('activity_update', 'activity-1', 'activities', ('activity-1',), {}),
    ('contact_update', 'contact-1', 'contacts', ('contact-1',), {}),
    ('service_request_update', 'sr-1', 'service_requests', ('sr-1',), {'search_params': {'include_custom_fields': 'true'}}),
    ('subscription_update', 'sub-1', 'subscriptions', ('sub-1',), {}),
]


@pytest.mark.parametrize('update_method, obj_id, get_method, get_args, get_kwargs', CUSTOM_FIELDS_MERGE_CASES)
class TestCustomFieldsMergeByDefault:

    def test_merges_into_existing_custom_fields_by_default(
        self, api, update_method, obj_id, get_method, get_args, get_kwargs,
    ):
        current = {'id': obj_id, 'custom_fields': [{'key': 'existing', 'value': 'old'}]}
        response = FakeResponse(json_data={'id': obj_id})
        with patch.object(api, get_method, return_value=current) as mock_get, \
                patch('crm5_bo.crm5_bo.requests.request', return_value=response) as mock_request:
            getattr(api, update_method)(obj_id, {'custom_fields': {'new_key': 'new_value'}})

        mock_get.assert_called_once_with(*get_args, **get_kwargs)
        sent_custom_fields = mock_request.call_args.kwargs['json']['custom_fields']
        assert sorted(sent_custom_fields, key=lambda cf: cf['key']) == [
            {'key': 'existing', 'value': 'old'},
            {'key': 'new_key', 'value': 'new_value'},
        ]

    def test_accepts_list_shaped_custom_fields_too(
        self, api, update_method, obj_id, get_method, get_args, get_kwargs,
    ):
        current = {'id': obj_id, 'custom_fields': [{'key': 'existing', 'value': 'old'}]}
        response = FakeResponse(json_data={'id': obj_id})
        with patch.object(api, get_method, return_value=current), \
                patch('crm5_bo.crm5_bo.requests.request', return_value=response) as mock_request:
            getattr(api, update_method)(obj_id, {'custom_fields': [{'key': 'existing', 'value': 'new'}]})

        assert mock_request.call_args.kwargs['json']['custom_fields'] == [{'key': 'existing', 'value': 'new'}]

    def test_does_not_fetch_when_body_has_no_custom_fields(
        self, api, update_method, obj_id, get_method, get_args, get_kwargs,
    ):
        response = FakeResponse(json_data={'id': obj_id})
        with patch.object(api, get_method) as mock_get, \
                patch('crm5_bo.crm5_bo.requests.request', return_value=response):
            getattr(api, update_method)(obj_id, {'some_field': 'value'})

        mock_get.assert_not_called()

    def test_merge_custom_fields_false_skips_the_fetch_and_sends_as_is(
        self, api, update_method, obj_id, get_method, get_args, get_kwargs,
    ):
        response = FakeResponse(json_data={'id': obj_id})
        with patch.object(api, get_method) as mock_get, \
                patch('crm5_bo.crm5_bo.requests.request', return_value=response) as mock_request:
            getattr(api, update_method)(
                obj_id, {'custom_fields': [{'key': 'a', 'value': 'b'}]}, merge_custom_fields=False,
            )

        mock_get.assert_not_called()
        assert mock_request.call_args.kwargs['json']['custom_fields'] == [{'key': 'a', 'value': 'b'}]
