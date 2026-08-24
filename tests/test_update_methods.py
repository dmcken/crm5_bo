from unittest.mock import patch

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
