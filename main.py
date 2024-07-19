from flask import Flask, request, jsonify, render_template, make_response
import requests
import json
import os
from flask_sqlalchemy import SQLAlchemy
import logging


def load_weather_descriptions():
    with open(os.path.join(os.path.dirname(__file__), 'data/weather_descriptions.json'), 'r', encoding='utf-8') as f:
        return json.load(f)


def load_cities():
    with open(os.path.join(os.path.dirname(__file__), 'data/cities.json'), 'r', encoding='utf-8') as f:
        return json.load(f)


def get_coordinates(city):
    city_coordinates = {
        "Москва": (55.7558, 37.6176),
        "Лондон": (51.5074, -0.1278),
        "Париж": (48.8566, 2.3522),
        "Нью-Йорк": (40.7128, -74.0060),
        "Лос-Анджелес": (34.0522, -118.2437),
        "Токио": (35.6895, 139.6917),
        "Берлин": (52.5200, 13.4050),
        "Рим": (41.9028, 12.4964),
        "Мадрид": (40.4168, -3.7038),
        "Торонто": (43.651070, -79.347015),
        "Сидней": (33.8688, 151.2093),
        "Пекин": (39.9042, 116.4074),
        "Дели": (28.7041, 77.1025),
        "Стамбул": (41.0082, 28.9784),
        "Кейптаун": (33.9249, 18.4241)
    }
    return city_coordinates.get(city)


def get_weather(coordinates):
    latitude, longitude = coordinates
    url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current_weather=true"
    response = requests.get(url)
    return response.json()


class WeatherApp:
    def __init__(self):
        self.SearchHistory = None
        self.app = Flask(__name__)
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///search_history.db'
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        self.db = SQLAlchemy(self.app)
        self.weather_descriptions = load_weather_descriptions()
        self.cities = load_cities()
        self.setup_db()
        self.setup_routes()
        self.setup_logging()

    def setup_db(self):
        with self.app.app_context():
            class SearchHistory(self.db.Model):
                id = self.db.Column(self.db.Integer, primary_key=True)
                city = self.db.Column(self.db.String(80), nullable=False)
                count = self.db.Column(self.db.Integer, nullable=False, default=1)
            self.SearchHistory = SearchHistory
            self.db.create_all()

    def setup_routes(self):
        @self.app.route('/')
        def index():
            last_weather = request.cookies.get('last_weather')
            if last_weather:
                try:
                    last_weather = json.loads(last_weather)
                except json.JSONDecodeError:
                    self.app.logger.error('JSONDecodeError: Invalid cookie format')
                    last_weather = None
            else:
                last_weather = None
            return render_template('index.html', last_weather=last_weather)

        @self.app.route('/autocomplete', methods=['GET'])
        def autocomplete():
            query = request.args.get('query')
            matches = [city for city in self.cities if query.lower() in city.lower()]
            return jsonify(matches)

        @self.app.route('/weather', methods=['POST'])
        def weather():
            city = request.form['city']
            coordinates = get_coordinates(city)
            if coordinates:
                weather_data = get_weather(coordinates)
                weather_data['city'] = city  # Добавляем город в данные о погоде
                weather_data['description'] = self.get_weather_description(weather_data['current_weather']['weathercode'])
                response = make_response(jsonify(weather_data))
                try:
                    response.set_cookie('last_weather', json.dumps(weather_data), max_age=30*24*60*60)  # Сохранить на 30 дней
                except TypeError as e:
                    self.app.logger.error(f'TypeError: {e}')
                self.update_search_history(city)
                return response
            else:
                return jsonify({"error": "Город не найден"}), 404

        @self.app.route('/search_history', methods=['GET'])
        def search_history():
            history = self.SearchHistory.query.all()
            result = {entry.city: entry.count for entry in history}
            return jsonify(result)

    def get_weather_description(self, code):
        return self.weather_descriptions.get(str(code), "Неизвестный код погоды")

    def update_search_history(self, city):
        with self.app.app_context():
            entry = self.SearchHistory.query.filter_by(city=city).first()
            if entry:
                entry.count += 1
            else:
                entry = self.SearchHistory(city=city, count=1)
                self.db.session.add(entry)
            self.db.session.commit()

    def setup_logging(self):
        logging.basicConfig(filename='app.log', level=logging.ERROR)

    def run(self, debug=True):
        self.app.run(debug=debug)


if __name__ == '__main__':
    weather_app = WeatherApp()
    weather_app.run()
