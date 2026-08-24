"""Shared test helpers for building fake HTTP responses and CRM pages."""


class FakeResponse:
    """Minimal stand-in for requests.Response used in tests."""

    def __init__(self, status_code=200, json_data=None, text=None):
        self.status_code = status_code
        self._json_data = {} if json_data is None else json_data
        self.text = text if text is not None else str(self._json_data)

    def json(self):
        return self._json_data


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
