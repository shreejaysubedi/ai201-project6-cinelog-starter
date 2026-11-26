"""
routes/watchlist/watchlist.py — CineLog

Endpoints for the watchlist feature.
"""

from uuid import UUID

from flask import Blueprint, jsonify, request
from services.watchlist_service import (
    add_to_watchlist,
    get_watchlist,
    remove_from_watchlist,
    AlreadyInWatchlistError,
    NotInWatchlistError,
)
from services.collection_service import FilmNotFoundError

watchlist_bp = Blueprint("watchlist", __name__)


@watchlist_bp.route("/<user_id>", methods=["GET"])
def view_watchlist(user_id):
    """GET /watchlist/<user_id> — Return the user's watchlist."""
    films = get_watchlist(user_id)
    return jsonify(films)


@watchlist_bp.route("/<user_id>/add", methods=["POST"])
def add_film(user_id):
    """
    POST /watchlist/<user_id>/add

    Body: { "film_id": "<uuid>", "public": false } (public optional)
    """
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or "film_id" not in data:
        return jsonify({"error": "film_id is required"}), 400

    try:
        film_id = str(UUID(data["film_id"]))
    except (ValueError, TypeError, AttributeError):
        return jsonify({"error": "film_id must be a UUID string"}), 400

    public = data.get("public", False)
    if not isinstance(public, bool):
        return jsonify({"error": "public must be a boolean"}), 400

    try:
        entry = add_to_watchlist(
            user_id=user_id, film_id=film_id, public=public
        )
        return jsonify(entry.to_dict()), 201
    except FilmNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except AlreadyInWatchlistError as e:
        return jsonify({"error": str(e)}), 409


@watchlist_bp.route("/<user_id>/remove", methods=["DELETE"])
def remove_film(user_id):
    """DELETE /watchlist/<user_id>/remove with {"film_id": "<uuid>"}."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or "film_id" not in data:
        return jsonify({"error": "film_id is required"}), 400

    try:
        film_id = str(UUID(data["film_id"]))
    except (ValueError, TypeError, AttributeError):
        return jsonify({"error": "film_id must be a UUID string"}), 400

    try:
        remove_from_watchlist(user_id=user_id, film_id=film_id)
        return jsonify({"message": "Removed from watchlist"}), 200
    except NotInWatchlistError as e:
        return jsonify({"error": str(e)}), 404
