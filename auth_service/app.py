from flask import Flask, request, jsonify
from Auth import Auth
from flask_cors import CORS
from prometheus_client import generate_latest
import sys
import os
from waitress import serve
import uuid
from datetime import datetime
# Adjusting sys path for one level up
#sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from telemetry_service.metrics import Metrics
from telemetry_service.log_handler import setup_mongo_logging

app = Flask(__name__)
CORS(app)

# Service Name 
SERVICE_NAME = "auth_service"

# Set up MongoDB logging using the shared module
DB_URI = os.environ.get('DB_URI', 'mongodb://localhost:27017')
logger = setup_mongo_logging(SERVICE_NAME, db_uri=DB_URI)

# Initialize Metrics for this Service
metrics = Metrics(SERVICE_NAME)

# Get database connection details from environment variables
DB_HOST = os.getenv('DB_HOST', 'postgresinstance.cpyqmeeock79.eu-north-1.rds.amazonaws.com')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgre123')
DB_NAME = os.getenv('DB_NAME', 'postgresdb')

# Use the environment variables in the configuration dictionary
db_config = {
    'dbname': DB_NAME,
    'user': DB_USER,
    'password': DB_PASSWORD,
    'host': DB_HOST,
    'port': DB_PORT
}


user_table = Auth(db_config)


@app.route('/authenticate', methods=['POST'])
def authenticate_user():
    request_id = str(uuid.uuid4())

    logger.info("Request received", extra={'custom': {"request_id": request_id, "endpoint": "/authenticate"}})

    with metrics.track_latency(endpoint='/authenticate'):
        metrics.track_request(method='POST', endpoint='/authenticate')

        data = request.json
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            metrics.track_error(endpoint='/authenticate', error_type='missing_credentials')
            logger.error("Missing credentials", extra={'custom': {"request_id": request_id, "endpoint": "/authenticate"}})
            return jsonify({"error": "Email and password are required."}), 400

        authenticated, user_id = user_table.authenticate_user(email, password)
        
        return jsonify({
            "authenticated": authenticated,
            "user_id": user_id
        })


@app.route('/authenticate/admin', methods=['POST'])
def authenticate_admin():
    request_id = str(uuid.uuid4())
    logger.info("Request received", extra={'custom': {"request_id": request_id, "endpoint": "/authenticate/admin"}})
    with metrics.track_latency(endpoint='/authenticate/admin'):
        metrics.track_request(method='POST', endpoint='/authenticate/admin')

        data = request.json
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            metrics.track_error(endpoint='/authenticate/admin', error_type='missing_credentials')
            logger.error("Missing admin credentials", extra={'custom': {"request_id": request_id, "endpoint": "/authenticate/admin"}})
            return jsonify({"error": "Username and password are required."}), 400

        authenticated = user_table.authenticate_admin(username, password)
        return jsonify({
            "authenticated": authenticated
        })

@app.route('/metrics', methods=['GET'])
def metrics_endpoint():
    logger.info("Metrics endpoint accessed", extra={'custom': {"endpoint": "/metrics"}})
    return generate_latest(), 200, {'Content-Type': 'text/plain; charset=utf-8'}

if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=3300, threads=4)
