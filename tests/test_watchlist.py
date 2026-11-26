"""Watchlist service tests, following the collection's isolated database pattern."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app import create_app, db
from models import Film, User, WatchlistEntry
from services.collection_service import FilmNotFoundError
from services.watchlist_service import (
    AlreadyInWatchlistError,
    NotInWatchlistError,
    add_to_watchlist,
    get_watchlist,
    remove_from_watchlist,
)


@pytest.fixture
def app():
    app = create_app(config={
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def sample_user(app):
    with app.app_context():
        user = User(username="watcher", email="watcher@example.com")
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def sample_film(app):
    with app.app_context():
        film = Film(title="Paddington 2", year=2017, genre="Comedy")
        db.session.add(film)
        db.session.commit()
        return film.id


@pytest.fixture
def other_user(app):
    with app.app_context():
        user = User(username="other", email="other@example.com")
        db.session.add(user)
        db.session.commit()
        return user.id


def test_add_to_watchlist_nonexistent_film_raises(app, sample_user):
    with app.app_context():
        missing_id = "00000000-0000-0000-0000-000000000000"

        with pytest.raises(FilmNotFoundError):
            add_to_watchlist(user_id=sample_user, film_id=missing_id)

        assert WatchlistEntry.query.count() == 0


def test_add_to_watchlist_creates_entry(app, sample_user, sample_film):
    with app.app_context():
        entry = add_to_watchlist(user_id=sample_user, film_id=sample_film)

        assert entry.user_id == sample_user
        assert entry.film_id == sample_film
        db.session.expire_all()
        persisted = WatchlistEntry.query.filter_by(
            user_id=sample_user, film_id=sample_film
        ).one()
        assert persisted.id == entry.id


def test_add_to_watchlist_duplicate_raises(app, sample_user, sample_film):
    with app.app_context():
        original = add_to_watchlist(user_id=sample_user, film_id=sample_film)

        with pytest.raises(AlreadyInWatchlistError):
            add_to_watchlist(user_id=sample_user, film_id=sample_film)

        assert WatchlistEntry.query.filter_by(
            user_id=sample_user, film_id=sample_film
        ).count() == 1
        assert WatchlistEntry.query.one().id == original.id


def test_same_film_can_belong_to_different_users(
    app, sample_user, other_user, sample_film
):
    with app.app_context():
        first = add_to_watchlist(sample_user, sample_film)
        second = add_to_watchlist(other_user, sample_film)

        assert first.id != second.id
        assert WatchlistEntry.query.count() == 2
        assert len(get_watchlist(sample_user)) == 1
        assert len(get_watchlist(other_user)) == 1


def test_database_rejects_duplicate_user_film(app, sample_user, sample_film):
    with app.app_context():
        add_to_watchlist(sample_user, sample_film)
        db.session.add(WatchlistEntry(user_id=sample_user, film_id=sample_film))

        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

        assert WatchlistEntry.query.count() == 1


def test_watchlist_is_empty_for_user_without_entries(app, sample_user):
    with app.app_context():
        assert get_watchlist(sample_user) == []


def test_get_watchlist_returns_newest_first(app, sample_user, other_user):
    with app.app_context():
        earlier = datetime(2026, 1, 1, tzinfo=timezone.utc)
        films = [Film(title="Alien"), Film(title="Spirited Away")]
        db.session.add_all(films)
        db.session.commit()
        db.session.add_all([
            WatchlistEntry(
                user_id=sample_user, film_id=films[0].id,
                date_added=earlier, public=False,
            ),
            WatchlistEntry(
                user_id=sample_user, film_id=films[1].id,
                date_added=earlier + timedelta(days=1), public=True,
            ),
            WatchlistEntry(user_id=other_user, film_id=films[0].id),
        ])
        db.session.commit()

        watchlist = get_watchlist(sample_user)

        assert [film["title"] for film in watchlist] == ["Spirited Away", "Alien"]
        assert [film["public"] for film in watchlist] == [True, False]
        assert all("date_added" in film for film in watchlist)


def test_equal_timestamps_sort_by_title_then_id(app, sample_user):
    with app.app_context():
        same_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
        films = [Film(title="Zodiac"), Film(title="Alien"), Film(title="Alien")]
        db.session.add_all(films)
        db.session.commit()
        db.session.add_all([
            WatchlistEntry(
                user_id=sample_user, film_id=film.id, date_added=same_time
            ) for film in films
        ])
        db.session.commit()

        result = get_watchlist(sample_user)

        assert [film["title"] for film in result] == ["Alien", "Alien", "Zodiac"]
        assert [film["id"] for film in result[:2]] == sorted(
            film.id for film in films if film.title == "Alien"
        )


def test_service_and_model_default_visibility_to_private(
    app, sample_user, other_user, sample_film
):
    with app.app_context():
        service_entry = add_to_watchlist(sample_user, sample_film)
        model_entry = WatchlistEntry(user_id=other_user, film_id=sample_film)
        db.session.add(model_entry)
        db.session.commit()

        assert service_entry.public is False
        assert model_entry.public is False


def test_remove_from_watchlist_removes_only_target_user(
    app, sample_user, other_user, sample_film
):
    with app.app_context():
        add_to_watchlist(sample_user, sample_film)
        add_to_watchlist(other_user, sample_film)

        assert remove_from_watchlist(sample_user, sample_film) is True
        assert get_watchlist(sample_user) == []
        assert len(get_watchlist(other_user)) == 1


def test_remove_from_watchlist_nonexistent_film_raises(app, sample_user):
    with app.app_context():
        with pytest.raises(NotInWatchlistError):
            remove_from_watchlist(sample_user, "00000000-0000-0000-0000-000000000000")


def test_remove_from_watchlist_cannot_remove_other_users_film(
    app, sample_user, other_user, sample_film
):
    with app.app_context():
        add_to_watchlist(other_user, sample_film)

        with pytest.raises(NotInWatchlistError):
            remove_from_watchlist(sample_user, sample_film)

        assert WatchlistEntry.query.one().user_id == other_user


def test_remove_twice_raises_and_film_can_be_added_again(
    app, sample_user, sample_film
):
    with app.app_context():
        original_id = add_to_watchlist(sample_user, sample_film).id
        remove_from_watchlist(sample_user, sample_film)

        with pytest.raises(NotInWatchlistError):
            remove_from_watchlist(sample_user, sample_film)

        assert add_to_watchlist(sample_user, sample_film).id != original_id
        assert WatchlistEntry.query.count() == 1


@pytest.mark.parametrize("visibility", [None, False, True])
def test_add_endpoint_preserves_visibility(app, sample_user, sample_film, visibility):
    body = {"film_id": sample_film}
    if visibility is not None:
        body["public"] = visibility

    client = app.test_client()
    response = client.post(f"/watchlist/{sample_user}/add", json=body)

    assert response.status_code == 201
    assert response.json["public"] is (visibility if visibility is not None else False)
    watchlist = client.get(f"/watchlist/{sample_user}")
    assert watchlist.status_code == 200
    assert len(watchlist.json) == 1
    assert watchlist.json[0]["id"] == sample_film
    assert watchlist.json[0]["public"] == response.json["public"]


@pytest.mark.parametrize("visibility", ["false", "true", 0, 1, None, [], {}])
def test_add_endpoint_rejects_nonboolean_visibility(
    app, sample_user, sample_film, visibility
):
    response = app.test_client().post(
        f"/watchlist/{sample_user}/add",
        json={"film_id": sample_film, "public": visibility},
    )

    assert response.status_code == 400
    assert response.json == {"error": "public must be a boolean"}
    with app.app_context():
        assert WatchlistEntry.query.count() == 0


def test_duplicate_endpoint_returns_409_without_changing_visibility(
    app, sample_user, sample_film
):
    client = app.test_client()
    path = f"/watchlist/{sample_user}/add"
    assert client.post(path, json={"film_id": sample_film}).status_code == 201

    response = client.post(path, json={"film_id": sample_film, "public": True})

    assert response.status_code == 409
    assert "already" in response.json["error"]
    with app.app_context():
        assert WatchlistEntry.query.count() == 1
        assert WatchlistEntry.query.one().public is False


def test_add_endpoint_nonexistent_film_returns_404(app, sample_user):
    response = app.test_client().post(
        f"/watchlist/{sample_user}/add",
        json={"film_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert response.status_code == 404
    assert "No film found" in response.json["error"]


@pytest.mark.parametrize("body", [{}, [], "film", None])
@pytest.mark.parametrize("action,method", [("add", "post"), ("remove", "delete")])
def test_endpoints_require_film_id(app, sample_user, body, action, method):
    response = getattr(app.test_client(), method)(
        f"/watchlist/{sample_user}/{action}", json=body
    )

    assert response.status_code == 400
    assert response.json == {"error": "film_id is required"}


def test_remove_endpoint_returns_200_then_404(app, sample_user, sample_film):
    client = app.test_client()
    assert client.post(
        f"/watchlist/{sample_user}/add", json={"film_id": sample_film}
    ).status_code == 201

    response = client.delete(
        f"/watchlist/{sample_user}/remove", json={"film_id": sample_film}
    )

    assert response.status_code == 200
    assert response.json == {"message": "Removed from watchlist"}
    assert client.get(f"/watchlist/{sample_user}").json == []
    assert client.delete(
        f"/watchlist/{sample_user}/remove", json={"film_id": sample_film}
    ).status_code == 404
