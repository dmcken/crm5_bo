# CRM.com API quirks

Undocumented (or mis-documented) behavior discovered while working against
the live `app.crm.com` backoffice v2 API, kept here so it isn't rediscovered
the hard way next time. Findings below were confirmed with read-only `GET`
requests against the live GD account on the date noted in each section.

## ⚠️ `PUT .../{id}` REPLACES the entire `custom_fields` array — it does not merge/patch it

**Confirmed 2026-08-24, and this one caused real data loss before it was caught.**

**Symptom:** Any `*_update` PUT call whose body includes a `custom_fields`
key (e.g. `[{"key": "activity_for_post_visit", "value": "A045407"}]`)
overwrites the record's *entire* `custom_fields` array with exactly what
was sent — every other custom field previously set on that record is
silently deleted, not preserved. This is not a PATCH-style partial update
despite the field being a list of individual key/value pairs, which looks
exactly like something you'd expect to merge.

**Confirmed impact:** `update_sr_activity_for_post_visit.py`'s first version
sent only `{"custom_fields": [{"key": "activity_for_post_visit", "value": ...}]}`
per service request. Re-reading a sample of the updated service requests
afterward showed most of them left with `custom_fields` containing *only*
`activity_for_post_visit` — other fields resolved SRs commonly carry (e.g.
`resolution`, which was the single most common key across an earlier
100-record sample) were gone. Read-only confirmation, 15 SRs sampled from
`sr_to_update.csv` after an `--execute` run:

```
S119442: custom_field_keys=['resolution', 'activity_for_post_visit']   # not clobbered (started empty, both fields set correctly)
S119834: custom_field_keys=['activity_for_post_visit']                 # everything else gone
S120067: custom_field_keys=['activity_for_post_visit']
S120341: custom_field_keys=['activity_for_post_visit']
... (11 more, same pattern)
```

**Scope: this is not specific to service requests.** The same `custom_fields`
array shape and the same PUT-replaces-not-merges behavior applies to every
`*_update` endpoint that accepts custom fields — contacts, activities,
subscriptions, and services, not just service requests. Any code (in this
library's callers, not just this one script) that PUTs a partial
`custom_fields` list to any of these endpoints has the same exposure.

**Workaround:** Never send a partial `custom_fields` list. Always fetch the
record first (with `include_custom_fields=true`), merge your changes into
its *existing* `custom_fields`, and send the full merged array. Use
`CRM5BackofficeAdmin.merge_custom_fields()` for this — it takes the
record's current `custom_fields` array plus a `{key: value}` dict of what
you're changing, and returns the full array ready to PUT:

```python
service_request = api.service_requests(sr_id)  # or search_value lookup
merged = api.merge_custom_fields(
    service_request.get('custom_fields') or [],
    {'activity_for_post_visit': 'A045407'},
)
api.service_request_update(sr_id, {'custom_fields': merged})
```

Every `*_update` method's docstring (`activity_update`, `contact_update`,
`service_request_update`, `service_update`, `subscription_update`) now
carries a warning pointing back here. `update_sr_activity_for_post_visit.py`
was fixed to do this after the fact — the SRs already clobbered by the
original run were **not** automatically recovered; whether that's possible
depends on whatever change history CRM.com itself retains, which hasn't
been checked.

## `GET /service_requests` silently ignores the `number` filter

**Confirmed 2026-08-23.**

**Symptom:** Filtering the service requests list by the human-readable
ticket number (e.g. `S119442`, the value shown in the `number` field of a
service request) using `?number=S119442` does not filter anything. The API
returns `200 OK` with the newest service requests in the account, completely
unfiltered, and `paging.has_more` stays `True` indefinitely.

**Why this matters:** `CRM5BackofficeAdmin.service_requests()` (and the
deprecated `service_requests_list()`) walk pages until `has_more is False`.
Since the (non-)filter never narrows the result set, calling
`api.service_requests(search_params={'number': 'S119442'})` doesn't error —
it just pages through the *entire* service_requests table, which on this
account is large enough that the call effectively hangs.

**Workaround:** Use `search_value` instead, which is a documented free-text
search across contact name, owner, description, ticket number, status,
`date_created`, and `date_closed`:

```python
api.service_requests(search_params={'search_value': 'S119442'})
```

This correctly returns exactly the matching service request with
`has_more: False`. Because `search_value` is free-text (not an exact-match
field filter), always verify the returned record's own `number` field
matches what you searched for — a broad search term could in principle
match on description text too. See `find_service_request()` in
[`update_sr_activity_for_post_visit.py`](update_sr_activity_for_post_visit.py)
for a defensive implementation: it fetches a single bounded page (never
auto-paginates) and requires an exact `number` match, treating more than one
match as ambiguous rather than guessing.

**Response latency:** `search_value` queries were noticeably slower and more
variable than plain listing calls during testing — anywhere from ~1s to
~16s for a single lookup. Budget for this in scripts that loop over many
lookups (don't set an aggressive client-side timeout below the library's
default 60s).

## `GET /custom_fields?entity=<anything>` (the list) returns `500` for every entity — but `GET /custom_fields/{id}` (single item) works fine

**Confirmed 2026-08-23/24.**

**Symptom:** The documented "List Custom Fields" endpoint
(`GET /custom_fields`) requires an `entity` query parameter (enum, e.g.
`SERVICE_REQUESTS`, `CONTACTS`, `DEVICES`, ...) per the API docs. Calling it
with any valid, correctly-cased enum value returns:

```
500 Internal Server Error
{"status":500,"message":null,"error":null,"parameters":null}
```

This was first found while checking `SERVICE_REQUESTS`, but it is **not**
specific to that entity: every documented enum value produces the same
`500` —
`CONTACTS`, `ORDERS`, `ORGANISATIONS`, `DEVICES`, `PAYMENTS`, `REFUNDS`,
`TOP_UPS`, `LEADS`, `ACTIVITIES`, `PASSES`, `SERVICE_REQUESTS`, plus
`ACCOUNTS` and `CREDIT_NOTES` (visible as options in the web UI's "View
Custom Fields for" picker but absent from the enum listed in this
endpoint's own docs). The endpoint appears to be entirely broken on this
account, regardless of which entity is requested.

Wrong casings/spellings (`service_requests`, `ServiceRequests`,
`Service_Requests`) return `404 Not Found` instead of `500`, so the `entity`
param itself *is* being recognized correctly when the casing matches a real
enum value — the 500 is a genuine server-side error, not a request mistake
on our end.

**Not a permissions issue:** confirmed via the CRM.com web UI — custom
fields for every entity checked (including Service Requests and
`activity_for_post_visit` specifically) are visible there without issue, so
the account/API key has read access to this data; the failure is specific
to this API call.

**Calling with no `entity` param at all** (`GET /custom_fields`) does not
error either — it returns `200 OK` with `{"content": null}`, despite the
docs describing `entity` as required and *also* saying custom fields for
all entities are returned if it's omitted. The two behaviors are
inconsistent with each other and with the docs.

**Workaround for confirming a field is populated in practice:** fetch actual
records with `include_custom_fields=true` and inspect their `custom_fields`
arrays, e.g.:

```python
page = api._fetch_page(
    'GET', '/service_requests',
    headers=api._auth_headers(),
    get_params={'resolved': 'true', 'size': 100, 'include_custom_fields': 'true'},
)
keys_seen = {cf['key'] for sr in page['content'] for cf in (sr.get('custom_fields') or [])}
```

Note this only proves a field exists if at least one sampled record has a
value set for it — an unset-everywhere field wouldn't show up this way even
if it's a valid, defined custom field.

**Better workaround, found 2026-09-05 — the *single-item* GET works fine:**
`GET /custom_fields/{id}` is not broken, only the list. It returns the full
field definition, including the `options` array (`key`/`text`/`default`/
`order_number`) for `SELECTION`-type fields:

```python
field = api.custom_fields('b165aef0-0bd9-41f0-b03c-4e094ef80681')
field['options']
# [{'key': 'Debt Collectors Pending', 'text': 'Debt Collectors - Pending', ...}, ...]
```

The catch: you need the field's GUID, and there's no working API path to
look it up by key/entity (that's exactly what's broken above). The GUID is
visible in the admin UI - open the field under Settings > Platform >
Custom Fields, and its edit URL is
`https://app.crm.com/settings/platform/edit-custom-field/{id}`.

This also caught a real bug in this library: `custom_fields(id)` used to
build `f'/custom_fields/{id}'` and call `_section_list_handler(path)` with
no `section_id`, so it took the listing code path (`_fetch_all`) instead of
a direct single-item GET. A field definition's own `content` property
(present, always `null`, for every type except `CONTENT`) was then mistaken
for `_fetch_page`'s pagination-wrapper check and raised
`"Call returned no content, call not implemented"` even though the HTTP
call had actually succeeded. Fixed by passing `section_id=custom_field_id`
properly.
