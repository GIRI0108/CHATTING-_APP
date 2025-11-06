from extensions import db
from datetime import datetime

class WeatherSearch(db.Model):
    __tablename__ = "weather_search"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=True)
    location = db.Column(db.String(255), nullable=False)
    temperature = db.Column(db.String(50))
    details = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
