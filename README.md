# crm5_bo
CRM 5 BackOffice Admin API




### Installation

Install from github latest version:
```
pip install git+https://github.com/dmcken/crm5_bo.git
or
python3 -m pip install git+https://github.com/dmcken/crm5_bo.git
```

Local copy for future developement:
```
git clone https://github.com/dmcken/crm5_bo.git
cd <git root dir>
python3 -m pip install --upgrade .
```

### Usage

```python
from crm5_bo import CRM5BackofficeAdmin

api = CRM5BackofficeAdmin('app.crm.com')
api.login(username=..., password=..., api_key=..., secret_key=...)

# Resource methods are named after their REST path and take an optional
# id (fetch one), search_params (filter a listing) and parallel flag
# (fetch multiple pages concurrently).
contact = api.contacts('a-contact-guid')
matches = api.contacts(search_params={'email_address': 'someone@example.com'})
everything = api.contacts(parallel=True)

api.contact_update('a-contact-guid', {'phone_number': '...'})
```

Method names moved to match the underlying REST resource in 0.2.0 (e.g.
`contacts_list` → `contacts`). Old names still work — they log a warning
identifying the replacement and can be grepped out of application logs to
find call sites still needing an update. See
[`CHANGELOG.md`](CHANGELOG.md) for the full old → new mapping and what
else changed release to release.

See [`QUIRKS.md`](QUIRKS.md) for undocumented (or mis-documented) live
API behavior worth knowing before you build against a new endpoint —
e.g. filters that are silently ignored rather than erroring.

### Development

```
uv sync --group test --group lint
uv run pytest
uv run ruff check .
```