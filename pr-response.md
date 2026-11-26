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

**My position:** Adopt date-added descending as the default. Break equal
timestamps by title, then film ID, to keep results deterministic.

**Reasoning:** CineLog's watchlist is a queue of intentions rather than the
catalog returned by `/films/`. A user who just saved a recommendation should
find it at the top when opening the queue, even if its title begins with Z.
`get_collection()` already returns recent additions first, so this keeps the
two personal lists consistent while leaving the catalog's alphabetical
browsing behavior intact. Title is only a tie-breaker; it cannot displace a
more recent entry.

**Engagement with reviewer's point:** I agree with the maintainer's specific
point that people often return to something saved recently. Alphabetical
order is better for locating a known title in a long list, and newest-first
does not tell someone which older film they should watch next. Those are
real tradeoffs, but neither justifies keeping an unexplained alphabetical
default for this save-for-later workflow. A future explicit `sort=title`
option or search could serve title lookup; manual ranking would be a separate
product feature. The current decision is implemented and covered by tests,
including equal timestamps; it is not just a promise in the PR description.

## Comment 6 — Rebase

**What conflicted:** Pending.

**How I resolved it:** Pending.

**How I verified no conflict remains:** Pending.

## Stretch Features

### Explicit visibility

`add_to_watchlist(user_id, film_id, public=False)` accepts a visibility flag,
and the POST endpoint forwards the optional JSON `public` value. Omission
keeps the private default. Explicit `true` and `false` are preserved; strings,
numbers, and null are rejected with HTTP 400 rather than coerced to booleans.
A duplicate add does not edit the existing entry's visibility. This toggle
records visibility intent; the limitations in Comment 4 still apply.

## Commit History

Pending final interactive rebase and screenshot.

## PR Description

Pending final verification.
