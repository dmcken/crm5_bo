# Changelog

This project has three downstream codebases as its consumers, all
maintained by the same person, so this file exists as a working reference
for updating call sites when a version bump changes something — not as a
public release announcement.

## Unreleased

### Added
- CI (`.github/workflows/ci.yml`): runs `ruff check .` and `pytest` on
  every push/PR to `main`, across Python 3.10/3.11/3.12.
- `ruff` wired into the project properly: a `lint` dependency group and a
  pinned `[tool.ruff]` config in `pyproject.toml`, so lint results are the
  same regardless of who runs it or which ruff version's own defaults are.
  (Ruff's true "no config anywhere" default turned out to enable ~920
  rules on the ruff version used here — not reproducible across
  installs, so it's now pinned explicitly.)
- `src/crm5_bo/py.typed` (PEP 561 marker) — the module has real type hints
  now; this tells type checkers in consuming codebases to use them.
  Confirmed it's actually included in the built wheel.

### Removed
- `.pylintrc` — unused; nothing referenced it and ruff has taken over
  linting duties.

## 0.2.1

### Added
- `service_request_update()` — `PUT /service_requests/{id}`, following the
  same pattern as `service_update`/`subscription_update`/etc. Needed for
  bulk-editing service request custom fields (e.g. the
  `activity_for_post_visit` field added upstream).
- `QUIRKS.md` — undocumented/mis-documented live API behavior discovered
  while building the above (a silently-ignored `number` filter on
  `GET /service_requests` that can hang auto-paginating calls, and a
  `GET /custom_fields?entity=...` endpoint that 500s for every entity on
  this account, confirmed unrelated to permissions).

## 0.2.0 — method rename / deduplication

The bulk of the method names had drifted over the library's life —
different resources picked up `_list` suffixes, `list_` prefixes, or bare
nouns at different times as the upstream CRM.com API itself changed, and
a few resources (`contacts`, `products`, `subscriptions`) ended up with
**two independent implementations** under different names that behaved
differently. This version renamed everything to match the actual REST
resource path and collapsed the duplicates down to one implementation
each. The old names still work — they're deprecated aliases that log a
warning identifying the replacement — so this isn't a hard break, but new
code should use the names on the left below going forward.

### Renamed (old → new)

| Old name | New name |
|---|---|
| `activities_list` | `activities` |
| `contacts_list` | `contacts` |
| `contact_services_list`, `list_contact_services` | `contact_services` |
| `contact_subscription_list` | `contact_subscriptions` |
| `devices_list` | `devices` |
| `journals_list` | `journals` |
| `orders_list` | `orders` |
| `products_list` | `products` |
| `sales_model` | `sales_models` |
| `service_device_list`, `list_service_devices` | `service_devices` |
| `service_requests_list` | `service_requests` |
| `subscriptions_list`, `subscription` | `subscriptions` |
| `subscriptions_devices_list` | `subscription_devices` |
| `teams_list` | `teams` |
| `users_list` | `users` |

Where two old names map to the same new one, they were genuine duplicate
implementations of the same endpoint (see below) that have been merged.

### Behavior changes hiding under unchanged names

`contacts()`, `products()`, and `subscription()`/`subscriptions()` existed
as bare-noun methods *before* this version too, but as separate, buggier
implementations that only ever returned a single page of results. They now
share the same fully-paginating implementation as their old `_list`
siblings (`contacts_list`, `products_list`, `subscriptions_list`). No
deprecation warning fires for this since the name didn't change — **any
caller relying on `contacts()`/`products()` silently truncating results
to one page will now get every matching record instead.**

`contact_services()` (merging `contact_services_list` and
`list_contact_services`) now always uses the more complete query
(`include_order_info`, `include_subscription`, `include_total` all `true`)
that `list_contact_services` used — the narrower query
`contact_services_list` used to send is gone.

### Other fixes bundled into this version
- `_section_list_handler` now URL-encodes `section_id` for every resource
  (previously only the old standalone `subscription()` bothered).
- `subscriptions_devices_list` (now `subscription_devices`) was sending
  requests with no auth headers at all; fixed.
- Several correctness bugs from the 0.1.x line (see below) are included.

## 0.1.x — docstrings, type hints, and correctness fixes

No renames in this line — internal cleanup and bug fixes leading up to
0.2.0:
- `login()` always returned `None` instead of `True`/`False` on success.
- `_fetch_all_parallel`'s total-record count was off by one page
  (double-counted the last, possibly-partial page).
- `_fetch_all_parallel_search_max` returned a bare `int` instead of a
  `(page, size)` tuple when its exponential probe landed exactly on the
  last page (e.g. any single-page result set) — raised `TypeError` in the
  caller.
- `_fetch_all_parallel` silently swallowed worker-thread exceptions with a
  bare `print()`, returning incomplete data with no error.
- `_make_request` only accepted exactly HTTP `200`, rejecting valid
  `201`/`202`/`204` responses.
- Several `_fetch_*` methods mutated the caller's `get_params`/
  `search_params` dict in place.
- `logout()` was a no-op stub; now actually calls
  `POST /users/{id}/sign_out` and clears local tokens.
- Added a full test suite (`tests/`, ~140 tests).
- Filled in all the autogenerated placeholder docstrings (`_description_`,
  `_type_`) and added warnings to `debug()`/`dump_auth()`/`load_auth()`
  about credential exposure.
