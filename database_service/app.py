from flask import Flask, request, jsonify
from Database import Database
from flask_cors import CORS
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
SERVICE_NAME = "database_service"

# Set up MongoDB logging using the shared module
DB_URI = os.environ.get('DB_URI', 'mongodb://mongodb:27017/ubflix')
logger = setup_mongo_logging(SERVICE_NAME, db_uri=DB_URI)

# Initialize Metrics for this Service
metrics = Metrics(SERVICE_NAME)

# Get database connection details from environment variables
DB_HOST = os.getenv('DB_HOST', 'postgresinstance.cpyqmeeock79.eu-north-1.rds.amazonaws.com')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgre123')
DB_NAME = os.getenv('DB_NAME', 'postgresdb')
REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
REDIS_PORT = os.getenv('REDIS_PORT', '6379')

# Use the environment variables in the configuration dictionary
db_config = {
    'dbname': DB_NAME,
    'user': DB_USER,
    'password': DB_PASSWORD,
    'host': DB_HOST,
    'port': DB_PORT
}

ubflix_db = Database(db_config)

@app.route('/add_user', methods=['POST'])
def add_user():
    request_id = str(uuid.uuid4())
    logger.info("Request received", extra={'custom': {"request_id": request_id, "endpoint": "/add_user"}})
    with metrics.track_latency(endpoint='/add_user'):
        metrics.track_request(method='POST', endpoint='/add_user')

        data = request.json
        try:
            user_id = ubflix_db.add_new_user(
                data['firstname'], data['lastname'], data['email'], data['plain_password']
            )
            logger.info("User added successfully", extra={'custom': {"request_id": request_id, "user_id": user_id}})
            return jsonify({"success": True, "user_id": user_id}), 201
        except ValueError as e:
            metrics.track_error(endpoint='/add_user', error_type='value_error')
            logger.error("Value error", extra={'custom': {"request_id": request_id, "error": str(e)}})
            return jsonify({"success": False, "error": str(e)}), 400
        except Exception as e:
            metrics.track_error(endpoint='/add_user', error_type='exception')
            logger.exception("Unexpected error", extra={'custom': {"request_id": request_id}})
            return jsonify({"success": False, "error": "An unexpected error occurred."}), 500

@app.route('/add_movie', methods=['POST'])
def add_movie():
    request_id = str(uuid.uuid4())
    logger.info("Request received", extra={'custom': {"request_id": request_id, "endpoint": "/add_movie"}})
    
    with metrics.track_latency(endpoint='/add_movie'):
        metrics.track_request(method='POST', endpoint='/add_movie')

        data = request.json
        try:
            data['imdbId'] = int(data['imdbId'])
            data['tmdbId'] = int(data['tmdbId'])
            data['popularity'] = float(data['popularity'])
            data['vote_average'] = float(data['vote_average'])
            
            movie_id = ubflix_db.add_new_movie(data)
            logger.info("Movie added successfully", extra={'custom': {"request_id": request_id, "movie_id": movie_id}})
            return jsonify({"success": True, "movie_id": movie_id}), 201
        except ValueError as e:
            metrics.track_error(endpoint='/add_movie', error_type='value_error')
            logger.error("Value error", extra={'custom': {"request_id": request_id, "error": str(e)}})
            return jsonify({"success": False, "error": str(e)}), 400
        except Exception as e:
            metrics.track_error(endpoint='/add_movie', error_type='exception')
            logger.exception("Unexpected error", extra={'custom': {"request_id": request_id}})
            return jsonify({"success": False, "error": "An unexpected error occurred."}), 500

@app.route('/delete_user/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    request_id = str(uuid.uuid4())
    logger.info("Delete user request received", extra={'custom': {"request_id": request_id, "user_id": user_id}})
    try:
        success = ubflix_db.delete_user(user_id)
        logger.info("User deletion status", extra={'custom': {"request_id": request_id, "success": success}})
        return jsonify({"success": success}), 200
    except Exception as e:
        logger.exception("Exception occurred during user deletion", extra={'custom': {"request_id": request_id}})
        return jsonify({"error": str(e)}), 500

@app.route('/delete_movie/<int:movie_id>', methods=['DELETE'])
def delete_movie(movie_id):
    request_id = str(uuid.uuid4())
    logger.info("Delete movie request received", extra={'custom': {"request_id": request_id, "movie_id": movie_id}})
    try:
        success = ubflix_db.delete_movie(movie_id)
        logger.info("Movie deletion status", extra={'custom': {"request_id": request_id, "success": success}})
        return jsonify({"success": success}), 200
    except Exception as e:
        logger.exception("Exception occurred during movie deletion", extra={'custom': {"request_id": request_id}})
        return jsonify({"error": str(e)}), 500

@app.route('/close', methods=['POST'])
def close_connection():
    request_id = str(uuid.uuid4())
    logger.info("Close database connection request received", extra={'custom': {"request_id": request_id}})
    try:
        ubflix_db.close()
        logger.info("Database connection closed", extra={'custom': {"request_id": request_id}})
        return jsonify({"success": True}), 200
    except Exception as e:
        logger.exception("Exception occurred while closing database connection", extra={'custom': {"request_id": request_id}})
        return jsonify({"error": str(e)}), 500

@app.route('/metrics', methods=['GET'])
def metrics_endpoint():
    logger.info("Metrics endpoint accessed", extra={'custom': {"endpoint": "/metrics"}})
    return generate_latest(), 200, {'Content-Type': 'text/plain; charset=utf-8'}

if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=3303, threads=4)