# PR Response Doc — CineLog Watchlist Feature

## AI Usage

In progress; the final entry will describe Codex's implementation, verification,
documentation, and Git assistance accurately.

## Comment 1 — Rename

**What I did:** Renamed `save_to_watchlist()` to `add_to_watchlist()` in the
service and updated the route's import and call. This matches
`add_to_collection()` and the project's `verb_to_noun` convention; it changes
the Python API without changing the HTTP endpoint.

**How I verified:** Searched the Python source for the old name and confirmed
there are no remaining call sites. The final service and route tests exercise
the renamed function.

## Comment 2 — Deduplication

**What I did:** Followed `add_to_collection()` by looking up the film first,
then querying the `(user_id, film_id)` pair before inserting. An existing
entry raises `AlreadyInWatchlistError`, which the route translates to HTTP 409.
The route also translates `FilmNotFoundError` to HTTP 404 instead of leaking
an unhandled exception. A matching database unique constraint protects the
same per-user invariant. The same film can still be saved by different users.

**How I verified:** Service and endpoint tests attempt the same add twice,
assert the expected exception/409 response, and check that exactly one entry
remains. A separate case adds the film for a second user to check that the
deduplication key is per user.

## Comment 3 — Missing test

**What I did:** Added `tests/test_watchlist.py` using the collection tests'
isolated in-memory SQLite app, committed user/film fixtures, application
contexts, and `pytest.raises` pattern. The requested missing-film test passes
the valid but absent UUID `00000000-0000-0000-0000-000000000000`, expects
`FilmNotFoundError`, and verifies that no entry was inserted. Added happy-path
and duplicate tests as required by `CONTRIBUTING.md` for a new service.

**How I verified:** Ran the watchlist tests with the existing collection suite.
The failure case checks the service's domain exception rather than accepting
a database error or an unrelated exception as a passing result.

## Comment 4 — Default visibility

**My position:** Default new entries to `public=False`, and allow callers to
opt in with `public=True` when saving a film.

**Reasoning:** CineLog separates films someone has watched and logged from
films they merely want to watch. Saving an unfamiliar film for later should
not imply that the user recommends it or wants to announce that interest to
the community. This starter has no onboarding flow that asks for a sharing
preference, so inheriting `public=True` would make that choice silently.
The explicit per-entry parameter lets someone share selected recommendations
without applying that assumption to every saved title. The model default
and service default both use `False`, so direct service and model callers
agree with the HTTP endpoint.

**Tradeoff acknowledged:** Public-by-default would help CineLog's community
discovery: more lists would be available without an extra action, and a user
who expects automatic sharing may find the private default inconvenient.
I still favor explicit sharing because an accidental disclosure cannot be
reversed just by changing the flag later. However, this implementation stores
visibility intent only: `GET /watchlist/<user_id>` returns every entry and
there is no authentication or owner/public-view distinction in the starter.
`public=False` does **not** make the data inaccessible. Enforced privacy needs
authenticated ownership and a filtered public view in a separate change.
Changing a Python default also does not update existing rows; an existing
database would need a deliberate migration and user-facing policy.

## Comment 5 — Sort order

**My position:** Pending.

**Reasoning:** Pending.

**Engagement with reviewer's point:** Pending.

## Comment 6 — Rebase

**What conflicted:** Pending.

**How I resolved it:** Pending.

**How I verified no conflict remains:** Pending.

## Stretch Features

Pending.

## Commit History

Pending final interactive rebase and screenshot.

## PR Description

Pending final verification.
