from flask import Flask, request, jsonify, render_template, make_response
import requests
import json
import os
import logging
from SearchHistory import db, SearchHistory

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///search_history.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)


def load_json_data(filename):
    with open(os.path.join(os.path.dirname(__file__), filename), 'r', encoding='utf-8') as f:
        return json.load(f)


weather_descriptions = load_json_data('data/weather_descriptions.json')
cities = load_json_data('data/cities.json')
city_coordinates = load_json_data('data/cities.json')


def get_coordinates(city):
    return city_coordinates.get(city)


def get_weather(coordinates):
    latitude, longitude = coordinates
    url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current_weather=true"
    response = requests.get(url)
    return response.json()


def get_weather_description(code):
    return weather_descriptions.get(str(code), "Неизвестный код погоды")


def update_search_history(city):
    entry = SearchHistory.query.filter_by(city=city).first()
    if entry:
        entry.count += 1
    else:
        entry = SearchHistory(city=city, count=1)
        db.session.add(entry)
    db.session.commit()


@app.route('/')
def index():
    last_weather = request.cookies.get('last_weather')
    if last_weather:
        try:
            last_weather = json.loads(last_weather)
        except json.JSONDecodeError:
            app.logger.error('JSONDecodeError: Invalid cookie format')
            last_weather = None
    else:
        last_weather = None
    return render_template('index.html', last_weather=last_weather)


@app.route('/autocomplete', methods=['GET'])
def autocomplete():
    query = request.args.get('query')
    matches = [city for city in cities if query.lower() in city.lower()]
    return jsonify(matches)


@app.route('/weather', methods=['POST'])
def weather():
    city = request.form['city']
    coordinates = get_coordinates(city)
    if coordinates:
        weather_data = get_weather(coordinates)
        weather_data['city'] = city
        weather_data['description'] = get_weather_description(weather_data['current_weather']['weathercode'])
        response = make_response(jsonify(weather_data))
        try:
            response.set_cookie('last_weather', json.dumps(weather_data), max_age=30 * 24 * 60 * 60)
        except TypeError as e:
            app.logger.error(f'TypeError: {e}')
        with app.app_context():
            update_search_history(city)
        return response
    else:
        return jsonify({"error": "Город не найден"}), 404


@app.route('/search_history', methods=['GET'])
def search_history():
    history = SearchHistory.query.all()
    result = {entry.city: entry.count for entry in history}
    return jsonify(result)


def setup_logging():
    logging.basicConfig(filename='app.log', level=logging.ERROR)


def main():
    with app.app_context():
        db.create_all()
    setup_logging()
    app.run(debug=True, host="0.0.0.0")


if __name__ == '__main__':
    main()
