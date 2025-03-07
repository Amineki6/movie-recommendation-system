from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from ui import UserInterface
from prometheus_client import generate_latest
import sys
import os
import uuid
from waitress import serve

# Adjusting sys path for one level up
#sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from telemetry_service.metrics import Metrics
from telemetry_service.log_handler import setup_mongo_logging

app = Flask(__name__)
CORS(app)

# Service Name
SERVICE_NAME = "ui_service"

# Set up MongoDB logging using the shared module
DB_URI = os.environ.get('DB_URI', 'mongodb://localhost:27017')
logger = setup_mongo_logging(SERVICE_NAME, db_uri=DB_URI)

# Initialize Metrics for this Service
metrics = Metrics(SERVICE_NAME)

DB_HOST = os.getenv('DB_HOST', 'postgresinstance.cpyqmeeock79.eu-north-1.rds.amazonaws.com')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgre123')
DB_NAME = os.getenv('DB_NAME', 'postgresdb')

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = db_url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Database model
class Movie(db.Model):
    __tablename__ = 'movies'
    movie_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=True)
    poster_path = db.Column(db.String(200), nullable=True)
    vote_average = db.Column(db.Float, nullable=True)
    director = db.Column(db.String(200), nullable=True)
    overview = db.Column(db.String(500), nullable=True)
    genres = db.Column(db.String(200), nullable=True)
    release_date = db.Column(db.Date, nullable=True)
    tmdbid = db.Column(db.Float, nullable=True)

# Initialize UserInterface and pass the db and Movie model
ui = UserInterface(db, Movie)

@app.route('/api/movies', methods=['GET'])
def get_movies():
    request_id = str(uuid.uuid4())
    logger.info("Request received", extra={'custom': {"request_id": request_id, "endpoint": "/api/movies"}})
    with metrics.track_latency(endpoint='/api/movies'):
        metrics.track_request(method='GET', endpoint='/api/movies')

        movies_data = ui.get_movies_posters(request)  
        return jsonify(movies_data)  # Convert response to JSON

@app.route('/api/recent_release', methods=['GET'])
def get_recent_release():
    request_id = str(uuid.uuid4())
    logger.info("Request received", extra={'custom': {"request_id": request_id, "endpoint": "/api/recent_release"}})
    with metrics.track_latency(endpoint='/api/recent_release'):
        metrics.track_request(method='GET', endpoint='/api/recent_release')

        data = ui.get_new_release()
        return jsonify(data if data else {"message": "No recent releases found"})

@app.route('/metrics', methods=['GET'])
def metrics_endpoint():
    logger.info("Metrics endpoint accessed", extra={'custom': {"endpoint": "/metrics"}})
    return generate_latest(), 200, {'Content-Type': 'text/plain; charset=utf-8'}

if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=3030, threads=4)
