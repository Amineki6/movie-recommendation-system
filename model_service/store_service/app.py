from flask import Flask, request, jsonify
from StoreRec import StoreRec
from prometheus_client import generate_latest
import sys
import os
import uuid
from waitress import serve
# Adjusting sys path for one level up
#sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from telemetry_service.metrics import Metrics
from telemetry_service.log_handler import setup_mongo_logging

# Initialize Flask app
app = Flask(__name__)

# Service Name
SERVICE_NAME = "store_service"

# Set up MongoDB logging using the shared module
DB_URI = os.environ.get('DB_URI', 'mongodb://mongodb:27017/ubflix')
logger = setup_mongo_logging(SERVICE_NAME, db_uri=DB_URI)

# Initialize Metrics for this Service
metrics = Metrics(SERVICE_NAME)

# Initialize StoreRec
store = StoreRec()

@app.route('/store', methods=['POST'])
def consume_message():
    """Endpoint to receive messages from Kafka Consumer"""
    request_id = str(uuid.uuid4())
    logger.info("Request received", extra={'custom': {"request_id": request_id, "endpoint": "/store"}})
    with metrics.track_latency(endpoint='/store'):
        metrics.track_request(method='POST', endpoint='/store')

        try:
            recs = request.get_json()
            if not recs:
                metrics.track_error(endpoint='/store', error_type='empty_payload')
                logger.error("Empty payload received", extra={'custom': {"request_id": request_id, "endpoint": "/store"}})
                return jsonify({"error": "Empty payload"}), 400

            store.recs(recs)

            logger.info("Message stored successfully", extra={'custom': {"request_id": request_id, "endpoint": "/store"}})
            return jsonify({"status": "Message received"}), 200
        except Exception as e:
            metrics.track_error(endpoint='/store', error_type='exception')
            logger.exception("Exception occurred while storing message", extra={'custom': {"request_id": request_id, "endpoint": "/store"}})
            return jsonify({"error": "Internal Server Error"}), 500

@app.route('/metrics', methods=['GET'])
def metrics_endpoint():
    logger.info("Metrics endpoint accessed", extra={'custom': {"endpoint": "/metrics"}})
    return generate_latest(), 200, {'Content-Type': 'text/plain; charset=utf-8'}

if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=6061, threads=4)