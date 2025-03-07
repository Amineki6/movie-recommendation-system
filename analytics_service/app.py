from flask import Flask, jsonify, request
from Analytics import Analytics  
from flask_cors import CORS
from waitress import serve
from prometheus_client import generate_latest
import sys
import os
import uuid

# Adjusting sys path for one level up
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from telemetry_service.metrics import Metrics
from telemetry_service.log_handler import setup_mongo_logging

app = Flask(__name__)
CORS(app)

# Service Name
SERVICE_NAME = "analytics_service"

# Set up MongoDB logging using the shared module
DB_URI = os.environ.get('DB_URI', 'mongodb://localhost:27017')
logger = setup_mongo_logging(SERVICE_NAME, db_uri=DB_URI)

# Initialize Metrics for this Service
metrics = Metrics(SERVICE_NAME)

analytics = Analytics()

@app.route('/user/history', methods=['POST'])
def get_user_history():
    request_id = str(uuid.uuid4())
    logger.info("Request received", extra={'custom': {"request_id": request_id, "endpoint": "/user/history"}})
    with metrics.track_latency(endpoint='/user/history'):
        metrics.track_request(method='POST', endpoint='/user/history')
        try:
            data = request.get_json()
            user_id = int(data.get('user_id'))

            if not user_id:
                metrics.track_error(endpoint='/user/history', error_type='missing_user_id')
                logger.error("Missing user_id in request", extra={'custom': {"request_id": request_id, "endpoint": "/user/history"}})
                return jsonify({"error": "User ID is required."}), 400

            user_history = analytics.get_user_history(user_id)

            if user_history is None:
                metrics.track_error(endpoint='/user/history', error_type='fetch_failed')
                logger.error("User history fetch failed", extra={'custom': {"request_id": request_id, "endpoint": "/user/history", "user_id": user_id}})
                return jsonify({"error": "Unable to fetch user history."}), 500

            return jsonify(user_history)
        except Exception as e:
            metrics.track_error(endpoint='/user/history', error_type='exception')
            logger.exception("Exception occurred while fetching user history", extra={'custom': {"request_id": request_id, "endpoint": "/user/history"}})
            return jsonify({"error": "Internal server error."}), 500


@app.route('/user/preferences', methods=['POST'])
def get_user_preferences():
    request_id = str(uuid.uuid4())
    logger.info("Request received", extra={'custom': {"request_id": request_id, "endpoint": "/user/preferences"}})
    with metrics.track_latency(endpoint='/user/preferences'):
        metrics.track_request(method='POST', endpoint='/user/preferences')
        try:
            data = request.get_json()

            # Validate user_id
            user_id = data.get('user_id')
            if not user_id:
                metrics.track_error(endpoint='/user/preferences', error_type='missing_user_id')
                logger.error("Missing user_id in request", extra={'custom': {"request_id": request_id, "endpoint": "/user/preferences"}})
                return jsonify({"error": "User ID is required."}), 400
            try:
                user_id = int(user_id)
            except ValueError:
                metrics.track_error(endpoint='/user/preferences', error_type='invalid_user_id')
                logger.error("User ID is not an integer", extra={'custom': {"request_id": request_id, "endpoint": "/user/preferences"}})
                return jsonify({"error": "User ID must be an integer."}), 400

            # Fetch preferences
            genre_scores, language_scores = analytics.get_user_genres_language(user_id)
            
            # Ensure data is in expected format
            if not isinstance(genre_scores, dict) or not isinstance(language_scores, dict):
                metrics.track_error(endpoint='/user/preferences', error_type='invalid_data_format')
                logger.error("Invalid data format from analytics", extra={'custom': {"request_id": request_id, "endpoint": "/user/preferences"}})
                return jsonify({"error": "Invalid data format from analytics."}), 500

            return jsonify({"genres": genre_scores, "languages": language_scores}), 200

        except Exception as e:
            metrics.track_error(endpoint='/user/preferences', error_type='exception')
            logger.exception("Exception occurred while fetching user preferences", extra={'custom': {"request_id": request_id, "endpoint": "/user/preferences"}})
            return jsonify({"error": "Internal server error."}), 500


@app.route('/users/count', methods=['GET'])
def count_users():
    request_id = str(uuid.uuid4())
    logger.info("Request received", extra={'custom': {"request_id": request_id, "endpoint": "/users/count"}})
    with metrics.track_latency(endpoint='/users/count'):
        metrics.track_request(method='GET', endpoint='/users/count')
        try:
            total_users = analytics.get_num_users()

            if total_users is None:
                metrics.track_error(endpoint='/users/count', error_type='fetch_failed')
                logger.error("Database query failed", extra={'custom': {"request_id": request_id, "endpoint": "/users/count"}})
                return jsonify({"error": "Database query failed"}), 500

            return jsonify({"total_users": total_users})

        except Exception as e:
            metrics.track_error(endpoint='/users/count', error_type='exception')
            logger.exception("Exception occurred while fetching user count", extra={'custom': {"request_id": request_id, "endpoint": "/users/count"}})
            return jsonify({"error": "Internal server error."}), 500


@app.route('/movies/count', methods=['GET'])
def count_movies():
    request_id = str(uuid.uuid4())
    logger.info("Request received", extra={'custom': {"request_id": request_id, "endpoint": "/movies/count"}})
    with metrics.track_latency(endpoint='/movies/count'):
        metrics.track_request(method='GET', endpoint='/movies/count')
        try:
            total_movies = analytics.get_num_movies()

            if total_movies is None:
                metrics.track_error(endpoint='/movies/count', error_type='fetch_failed')
                logger.error("Database query failed", extra={'custom': {"request_id": request_id, "endpoint": "/movies/count"}})
                return jsonify({"error": "Database query failed"}), 500

            return jsonify({"total_movies": total_movies})

        except Exception as e:
            metrics.track_error(endpoint='/movies/count', error_type='exception')
            logger.exception("Exception occurred while fetching movie count", extra={'custom': {"request_id": request_id, "endpoint": "/movies/count"}})
            return jsonify({"error": "Internal server error."}), 500
        
@app.route('/profile', methods=['POST'])
def get_profile():
    request_id = str(uuid.uuid4())
    #logger.info("Request received", extra={'custom': {"request_id": request_id, "endpoint": "/profile"}})
    with metrics.track_latency(endpoint='/profile'):
        metrics.track_request(method='POST', endpoint='/profile')
        try:
            data = request.get_json()
            user_id = int(data.get('user_id'))
            
            if not user_id:
                return jsonify({"error": "User ID is required"}), 400
            
            user_profile = analytics.profile(user_id)
            
            if "error" in user_profile:
                metrics.track_error(endpoint='/profile', error_type='user_not_found')
                logger.error("User not found", extra={'custom': {"request_id": request_id, "endpoint": "/profile"}})
                return jsonify(user_profile), 404
            
            return jsonify(user_profile)
        
        except Exception as e:
            metrics.track_error(endpoint='/profile', error_type='exception')
            logger.exception("Exception occurred while fetching user profile", extra={'custom': {"request_id": request_id, "endpoint": "/profile"}})
            return jsonify({"error": "Internal server error."}), 500



@app.route('/metrics', methods=['GET'])
def metrics_endpoint():
    request_id = str(uuid.uuid4())
    logger.info("Metrics endpoint accessed", extra={'custom': {"request_id": request_id, "endpoint": "/metrics"}})
    metrics.track_request(method='GET', endpoint='/metrics')
    return generate_latest(), 200, {'Content-Type': 'text/plain; charset=utf-8'}

if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=3040, threads=4)
