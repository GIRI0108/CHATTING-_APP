from flask import Blueprint, jsonify, request, render_template
import requests
import os

news_bp = Blueprint("news", __name__)
NEWS_KEY = os.getenv("NEWS_API_KEY")


@news_bp.route("/news")
def news_home():
    return render_template("news.html")


@news_bp.route("/api/news", methods=["GET"])
def get_news():
    category = request.args.get("category", "general")

    url = f"https://newsapi.org/v2/top-headlines?language=en&category={category}&apiKey={NEWS_KEY}"

    res = requests.get(url)
    data = res.json()

    return jsonify(data)
