"""Watchlist service tests, following the collection's isolated database pattern."""

import pytest

from app import create_app, db
from models import Film, User, WatchlistEntry
from services.collection_service import FilmNotFoundError
from services.watchlist_service import (
    AlreadyInWatchlistError,
    add_to_watchlist,
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
