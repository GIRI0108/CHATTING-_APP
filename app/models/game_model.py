from datetime import datetime
from extensions import db


class GameState(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conv_id = db.Column(db.Integer, nullable=False)
    game_type = db.Column(db.String(20))   # tictactoe, chess, checkers
    state = db.Column(db.Text)             # JSON string board state
    last_move_by = db.Column(db.Integer)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

class WatchSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conv_id = db.Column(db.Integer, nullable=False)
    video_url = db.Column(db.String(300))
    timestamp = db.Column(db.Float, default=0)   # current time in seconds
    is_playing = db.Column(db.Boolean, default=False)

class MusicSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conv_id = db.Column(db.Integer, nullable=False)
    track_url = db.Column(db.String(300))
    timestamp = db.Column(db.Float, default=0)
    is_playing = db.Column(db.Boolean, default=False)
