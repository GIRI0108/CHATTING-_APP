from flask import Blueprint, jsonify, render_template, request
import requests
import os

weather_bp = Blueprint("weather", __name__)
WEATHER_KEY = os.getenv("WEATHER_API_KEY")


@weather_bp.route("/weather")
def weather_home():
    return render_template("weather.html")


@weather_bp.route("/api/weather")
def get_weather():
    lat = request.args.get("lat")
    lon = request.args.get("lon")

    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&units=metric&appid={WEATHER_KEY}"
    res = requests.get(url)
    return jsonify(res.json())


@weather_bp.route("/api/forecast")
def get_forecast():
    lat = request.args.get("lat")
    lon = request.args.get("lon")

    url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&units=metric&appid={WEATHER_KEY}"
    res = requests.get(url)
    return jsonify(res.json())
