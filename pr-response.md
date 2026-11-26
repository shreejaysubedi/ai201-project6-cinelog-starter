# PR Response Doc — CineLog Watchlist Feature

Review source: [CodePath's original watchlist PR #1](https://github.com/codepath/ai201-project6-cinelog-starter/pull/1).
All work is on `feature/watchlist`, rebased onto the fork's `main`.

## AI Usage

I asked OpenAI Codex to complete this assignment in the forked repository.
It read the models, collection service, tests, contribution guide, assignment,
and all six comments on the original PR. It implemented the changes and tests,
ran the test suite and live HTTP checks, resolved the real rebase conflict,
rewrote the history, and drafted this document and PR description.

The arguments for Comments 4 and 5 are also AI-assisted: I did not supply
independently written drafts for a devil's-advocate review. Codex proposed
private visibility metadata and newest-first ordering using this repository's
save-for-later workflow and existing collection behavior. Its review of the
tradeoffs added the distinction between visibility metadata and enforced
privacy, the cost to community discovery, and the loss of alphabetical lookup.
These choices and the response text should be personally reviewed before
submission; this section does not claim the reasoning was written without AI.

For the requested history check, Codex inspected `git log --oneline` for
conventional prefixes and bundled changes. It identified the starter's
nonconventional message and split the inherited blueprint/lookup changes and
the ignore-file/response-document setup into separate logical commits. The
final log was checked against `CONTRIBUTING.md` and for merge commits.

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

**What conflicted:** The fork initially contained only `main`, so I fetched
CodePath's original `feature/watchlist` branch before making changes. After
Comments 1–5 and the stretch changes passed their tests, I ran
`git fetch origin` and `git rebase origin/main`. Git stopped while replaying the starter
watchlist commit: `models.py` had `WatchlistEntry.film_id` as an indexed
integer on the feature branch, while main's UUID refactor (`57ec3f9`) had
changed it to `db.String(36)` without that index.

**How I resolved it:** Kept main's UUID column type and foreign key to
`film.id`, retained the feature's `index=True`, staged `models.py`, and ran
`git rebase --continue`. The remaining commits replayed successfully. After
the rebase I made a separate UUID fix commit: clarified the model declaration,
updated the add/remove service arguments and JSON examples to UUID strings,
and made both write endpoints validate and canonicalize UUID strings.
Malformed IDs (including legacy integers) return 400, while well-formed but
absent UUIDs return the domain-specific 404. Tests create films using the
model's generated UUIDs, with no integer casts or hardcoded integer IDs.

**How I verified no conflict remains:** Ran the full collection and watchlist
suite after rebasing, checked that main is an ancestor, scanned for conflict
markers and obsolete integer-ID references in watchlist source, and checked
that `git rev-list --merges origin/main..HEAD` is empty. The final UUID tests
also check the SQLAlchemy column type and the add/get/remove JSON round trip.

## Stretch Features

### Additional edge case

The extra test `test_same_film_can_belong_to_different_users` checks that
deduplication is scoped to a user's list, not to the catalog film globally.
This is useful for a community app: two people should both be able to save
*Paddington 2*. Each list must return only its own entry. Additional tests
cover ordering, timestamp ties, database uniqueness, visibility defaults and
validation, removal, and HTTP status codes.

### Remove a saved film

Added `remove_from_watchlist(user_id, film_id)` and the matching DELETE
endpoint. Following `remove_from_collection()`, it selects the user/film pair,
raises `NotInWatchlistError` if absent, deletes and commits the matching entry,
and returns `True`. The endpoint returns 200 on success or 404 if absent.
Tests cover success, nonexistent IDs, a repeated removal, re-adding after
removal, and retaining another user's entry for the same film.

### Explicit visibility

`add_to_watchlist(user_id, film_id, public=False)` accepts a visibility flag,
and the POST endpoint forwards the optional JSON `public` value. Omission
keeps the private default. Explicit `true` and `false` are preserved; strings,
numbers, and null are rejected with HTTP 400 rather than coerced to booleans.
A duplicate add does not edit the existing entry's visibility. This toggle
records visibility intent; the limitations in Comment 4 still apply.

## Commit History

After the UUID rebase, I used `git rebase -i origin/main` to reword the
starter's nonconventional commit, separate bundled changes, and improve the
removal commit's wording. Rename, deduplication, visibility, sorting, tests,
and the post-rebase UUID update remain distinct changes.

The screenshot shows actual command output from `git log --oneline` on
`feature/watchlist` after rewriting, together with the branch name, main's
ancestry check, and zero merge commits. The screenshot is captured before
the final documentation commit that adds the image itself.

![Screenshot of rewritten conventional commits with no merge commits](docs/commit-history.png)

Verification: **52 tests passed** using `.venv/bin/python -m pytest tests/ -q`.
A separate live HTTP smoke test against `python app.py` passed the
add/get/remove flow, private default, public opt-in, newest-first ordering,
and 201/400/404/409 responses. The smoke test removed its saved entries.

## PR Description

### What the feature does

Adds a watchlist for films a user wants to watch later, separate from the
collection of films they have already watched. Users can add films by UUID,
retrieve their saved films and metadata, and remove saved films. Duplicate
adds return 409, and a well-formed UUID for a missing film returns 404.

- `GET /watchlist/<user_id>` returns film dictionaries with `date_added` and `public`.
- `POST /watchlist/<user_id>/add` accepts `{"film_id": "<uuid>", "public": false}`;
  `public` is optional. Success returns 201 with the new entry.
- `DELETE /watchlist/<user_id>/remove` accepts `{"film_id": "<uuid>"}`;
  success returns 200, and an absent saved entry returns 404.
- Missing/malformed film IDs or a nonboolean `public` value return JSON errors with 400.

### Design decisions

**Visibility:** New entries default to `public=False` because saving an
unwatched film expresses personal interest rather than an intentional
recommendation to the community. Callers can opt in per entry with
`public=True`. This reduces automatic community discovery, but avoids
silently choosing sharing for users. The flag is currently metadata only:
the starter has no authentication and the GET route returns all entries.
This PR does not enforce private access or change existing rows.

**Ordering:** Lists return newest additions first, matching `get_collection()`
and the maintainer's point that people return to recent saves. Title and
film UUID provide deterministic tie-breakers when timestamps match.
Alphabetical lookup is less convenient; an optional title sort or search
could address that separately.

### How to test manually

1. Set up and seed a local database in the repository root:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install -r requirements.txt
   python seed.py
   python app.py
   ```

   Use a fresh development database for the UUID schema and unique constraint.
   `db.create_all()` does not migrate an older database's columns or constraints.
   The API runs at `http://127.0.0.1:5000`; `/` returning 404 is expected.

2. Open a second terminal in the repository and load demo IDs:

   ```bash
   source .venv/bin/activate
   cinelog_user_id=$(python -c 'from app import create_app; from models import User; app=create_app(); ctx=app.app_context(); ctx.push(); print(User.query.filter_by(username="demo").one().id)')
   cinelog_alien_id=$(python -c 'from app import create_app; from models import Film; app=create_app(); ctx=app.app_context(); ctx.push(); print(Film.query.filter_by(title="Alien").one().id)')
   cinelog_spirited_id=$(python -c 'from app import create_app; from models import Film; app=create_app(); ctx=app.app_context(); ctx.push(); print(Film.query.filter_by(title="Spirited Away").one().id)')
   cinelog_base="http://127.0.0.1:5000/watchlist/$cinelog_user_id"
   curl -sS "$cinelog_base"
   ```

   Expect `[]` for a fresh watchlist.

3. Save *Alien* with the default visibility, then *Spirited Away* explicitly public:

   ```bash
   curl -i -X POST "$cinelog_base/add" -H 'Content-Type: application/json' \
     -d "{\"film_id\":\"$cinelog_alien_id\"}"
   curl -i -X POST "$cinelog_base/add" -H 'Content-Type: application/json' \
     -d "{\"film_id\":\"$cinelog_spirited_id\",\"public\":true}"
   curl -sS "$cinelog_base"
   ```

   Both POSTs return 201. *Alien* has `public: false`; *Spirited Away* has
   `public: true`. GET returns *Spirited Away* before *Alien*, demonstrating
   recency over alphabetical order, with UUID IDs and `date_added` metadata.

4. Check duplicate, missing, and invalid input handling:

   ```bash
   curl -i -X POST "$cinelog_base/add" -H 'Content-Type: application/json' \
     -d "{\"film_id\":\"$cinelog_alien_id\"}"
   curl -i -X POST "$cinelog_base/add" -H 'Content-Type: application/json' \
     -d '{"film_id":"00000000-0000-0000-0000-000000000000"}'
   curl -i -X POST "$cinelog_base/add" -H 'Content-Type: application/json' -d '{}'
   curl -i -X POST "$cinelog_base/add" -H 'Content-Type: application/json' -d '{"film_id":1}'
   curl -i -X POST "$cinelog_base/add" -H 'Content-Type: application/json' \
     -d "{\"film_id\":\"$cinelog_alien_id\",\"public\":\"false\"}"
   ```

   Expect 409, 404, 400, 400, and 400, respectively. GET still returns only
   two entries, and the rejected duplicate does not change *Alien*'s visibility.

5. Remove *Alien*, then repeat the DELETE:

   ```bash
   curl -i -X DELETE "$cinelog_base/remove" -H 'Content-Type: application/json' \
     -d "{\"film_id\":\"$cinelog_alien_id\"}"
   curl -i -X DELETE "$cinelog_base/remove" -H 'Content-Type: application/json' \
     -d "{\"film_id\":\"$cinelog_alien_id\"}"
   curl -sS "$cinelog_base"
   ```

   Expect 200 with `{"message":"Removed from watchlist"}`, then 404. The GET
   result contains only *Spirited Away*. It is possible to add *Alien* again.

6. Run the full suite and history checks:

   ```bash
   python -m pytest tests/ -q
   git merge-base --is-ancestor origin/main HEAD
   git rev-list --count --merges origin/main..HEAD
   git log --oneline
   ```

   Expect **52 passed**, ancestry exit status 0, a merge count of **0**, and
   conventional commit messages including separate rename, deduplication,
   test, and UUID-fix commits. The automated suite also covers removal,
   per-user deduplication, timestamp ties, and explicit visibility values.
