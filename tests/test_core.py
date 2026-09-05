import http.client
from unittest.mock import patch

from helpers import FakeResponse, make_jwt

from crm5_bo import CRM5BackofficeAdmin


class TestFieldsToDict:

    def test_converts_key_value_pairs(self, api):
        custom_fields = [
            {'key': 'account_number', 'value': '12345'},
            {'key': 'credit_limit_v4', 'value': '100.0'},
        ]
        assert api.fields_to_dict(custom_fields) == {
            'account_number': '12345',
            'credit_limit_v4': '100.0',
        }

    def test_empty_list(self, api):
        assert api.fields_to_dict([]) == {}

    def test_duplicate_keys_last_wins(self, api):
        custom_fields = [
            {'key': 'a', 'value': '1'},
            {'key': 'a', 'value': '2'},
        ]
        assert api.fields_to_dict(custom_fields) == {'a': '2'}


class TestMergeCustomFields:

    def test_adds_a_new_key_without_dropping_existing_ones(self, api):
        existing = [
            {'key': 'resolution', 'value': 'CUSTOMER CONTACT AND INFORMATION PROVIDED'},
            {'key': 'contractor_interaction', 'value': 'yes'},
        ]

        merged = api.merge_custom_fields(existing, {'activity_for_post_visit': 'A045407'})

        assert api.fields_to_dict(merged) == {
            'resolution': 'CUSTOMER CONTACT AND INFORMATION PROVIDED',
            'contractor_interaction': 'yes',
            'activity_for_post_visit': 'A045407',
        }

    def test_overwrites_an_existing_key_in_place(self, api):
        existing = [{'key': 'activity_for_post_visit', 'value': 'OLD'}]

        merged = api.merge_custom_fields(existing, {'activity_for_post_visit': 'NEW'})

        assert api.fields_to_dict(merged) == {'activity_for_post_visit': 'NEW'}

    def test_starts_from_an_empty_array(self, api):
        merged = api.merge_custom_fields([], {'activity_for_post_visit': 'A045407'})

        assert api.fields_to_dict(merged) == {'activity_for_post_visit': 'A045407'}


class TestBuildUrl:

    def test_builds_https_backoffice_url(self, api):
        assert api._buid_url('/contacts') == 'https://example.crm.com/backoffice/v2/contacts'

    def test_builds_url_for_nested_resource(self, api):
        assert api._buid_url('/contacts/abc-123/services') == \
            'https://example.crm.com/backoffice/v2/contacts/abc-123/services'


class TestAuthHeaders:

    def test_uses_access_token_and_secret_key(self, api):
        assert api._auth_headers() == {
            'authorization': 'test-access-token',
            'api_key': 'test-secret-key',
        }

    def test_reflects_updated_tokens(self, api):
        api._access_token = 'rotated-token'
        api._secret_key = 'rotated-secret'
        assert api._auth_headers() == {
            'authorization': 'rotated-token',
            'api_key': 'rotated-secret',
        }


class TestDebug:

    def test_returns_current_state_when_called_with_none(self, api):
        assert api.debug() is False

    def test_enabling_sets_http_client_debuglevel(self, api):
        try:
            assert api.debug(True) is True
            assert http.client.HTTPConnection.debuglevel == 2
        finally:
            api.debug(False)

    def test_disabling_resets_http_client_debuglevel(self, api):
        api.debug(True)
        try:
            assert api.debug(False) is False
            assert http.client.HTTPConnection.debuglevel == 0
        finally:
            api.debug(False)


class TestAuthCache:

    def test_dump_auth_round_trips_through_load_auth(self, api):
        api._username = 'user@example.com'
        api._password = 'hunter2'
        api._api_key = 'api-key'
        api._refresh_token = 'refresh-token'
        api._expiration_date = '2026-01-01'
        api._lockout_date = None
        api._password_expired = False

        dumped = api.dump_auth()
        assert dumped == {
            'username': 'user@example.com',
            'password': 'hunter2',
            'api_key': 'api-key',
            'secret_key': 'test-secret-key',
            'access_token': 'test-access-token',
            'refresh_token': 'refresh-token',
            'expiration_date': '2026-01-01',
            'lockout_date': None,
            'password_expired': False,
        }

        restored = CRM5BackofficeAdmin('example.crm.com')
        restored.load_auth(dumped)

        assert restored.dump_auth() == dumped


class TestLogin:

    def test_sends_credentials_and_stores_session_state(self, api):
        response = FakeResponse(json_data={
            'access_token': 'new-access-token',
            'refresh_token': 'new-refresh-token',
            'expiration_date': '2026-12-31',
            'mode': 'LIVE',
            'lockout_date': None,
            'password_expired': False,
        })

        with patch('crm5_bo.crm5_bo.requests.request', return_value=response) as mock_request:
            result = api.login('user@example.com', 'hunter2', 'live-api-key', 'live-secret-key')

        mock_request.assert_called_once_with(
            'POST',
            'https://example.crm.com/backoffice/v2/users/authenticate',
            json={
                'provider': 'EMAIL',
                'username': 'user@example.com',
                'password': 'hunter2',
            },
            headers={'api_key': 'live-api-key'},
            timeout=api._timeout,
        )
        assert result is True
        assert api._access_token == 'new-access-token'
        assert api._refresh_token == 'new-refresh-token'
        assert api._expiration_date == '2026-12-31'
        assert api._organization_mod == 'LIVE'
        assert api._lockout_date is None
        assert api._password_expired is False


class TestCurrentUserId:

    def test_decodes_sub_claim_from_access_token(self, api):
        api._access_token = make_jwt({'sub': 'user-guid-1', 'type': 'access'})
        assert api._current_user_id() == 'user-guid-1'


class TestLogout:

    def test_signs_out_current_user_and_clears_tokens(self, api):
        api._access_token = make_jwt({'sub': 'user-guid-1', 'type': 'access'})
        api._refresh_token = 'some-refresh-token'
        expected_headers = api._auth_headers()
        response = FakeResponse(status_code=200, text='')

        with patch('crm5_bo.crm5_bo.requests.request', return_value=response) as mock_request:
            api.logout()

        mock_request.assert_called_once_with(
            'POST',
            'https://example.crm.com/backoffice/v2/users/user-guid-1/sign_out',
            json=None,
            headers=expected_headers,
            timeout=api._timeout,
        )
        assert api._access_token is None
        assert api._refresh_token is None
