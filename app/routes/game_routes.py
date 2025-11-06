from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from models.game_model import GameState, WatchSession, MusicSession
from extensions import db

game_bp = Blueprint("games", __name__)

# Private Room
@game_bp.route("/room/<int:conv_id>")
@login_required
def room(conv_id):
    return render_template("room.html", conv_id=conv_id)

# Initialize game state
@game_bp.route("/start/<game>/<int:conv_id>", methods=["POST"])
@login_required
def start_game(game, conv_id):
    existing = GameState.query.filter_by(conv_id=conv_id, game_type=game).first()
    if existing:
        return jsonify({"state": existing.state})

    initial_state = ""

    if game == "tictactoe":
        initial_state = "---------"
    elif game == "chess":
        initial_state = "startpos"
    elif game == "checkers":
        initial_state = "initial"

    new_game = GameState(conv_id=conv_id, game_type=game, state=initial_state)
    db.session.add(new_game)
    db.session.commit()
    return jsonify({"state": initial_state})

# Watch Together initialization
@game_bp.route("/watch/init/<int:conv_id>", methods=["POST"])
@login_required
def init_watch(conv_id):
    session = WatchSession.query.filter_by(conv_id=conv_id).first()
    if not session:
        session = WatchSession(conv_id=conv_id, video_url="", timestamp=0, is_playing=False)
        db.session.add(session)
        db.session.commit()
    return jsonify({"ok": True})

# Music sync initialization
@game_bp.route("/music/init/<int:conv_id>", methods=["POST"])
@login_required
def init_music(conv_id):
    session = MusicSession.query.filter_by(conv_id=conv_id).first()
    if not session:
        session = MusicSession(conv_id=conv_id, track_url="", timestamp=0, is_playing=False)
        db.session.add(session)
        db.session.commit()
    return jsonify({"ok": True})
