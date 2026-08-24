"""Shared test helpers for building fake HTTP responses and CRM pages."""
import base64
import json


class FakeResponse:
    """Minimal stand-in for requests.Response used in tests."""

    def __init__(self, status_code=200, json_data=None, text=None):
        self.status_code = status_code
        self._json_data = {} if json_data is None else json_data
        self.text = text if text is not None else str(self._json_data)

    def json(self):
        return self._json_data


def make_jwt(claims: dict) -> str:
    """Build a JWT-shaped string carrying the given claims (unsigned)."""

    def b64url(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b'=').decode()

    header = b64url(json.dumps({'alg': 'none', 'typ': 'JWT'}).encode())
    payload = b64url(json.dumps(claims).encode())
    return f'{header}.{payload}.'


def make_page(content, page=1, size=100, total=None, has_more=False):
    """Build a CRM-style paginated response body."""
    return {
        'content': content,
        'paging': {
            'page': page,
            'size': size,
            'total': total if total is not None else len(content),
            'has_more': has_more,
        },
    }
