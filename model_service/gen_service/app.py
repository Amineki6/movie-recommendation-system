import requests
from flask import Flask, request, jsonify
from RecGenerator import RecGenerator
from flask_cors import CORS
from prometheus_client import generate_latest
import sys
import os
import uuid
import json
from waitress import serve
#sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from telemetry_service.metrics import Metrics
from telemetry_service.log_handler import setup_mongo_logging

# Initialize Flask app
app = Flask(__name__)
CORS(app, supports_credentials=True)

# Service Name
SERVICE_NAME = "gen_service"

# Set up MongoDB logging using the shared module
DB_URI = os.environ.get('DB_URI', 'mongodb://localhost:27017')
logger = setup_mongo_logging(SERVICE_NAME, db_uri=DB_URI)

# Initialize Metrics for this Service
metrics = Metrics(SERVICE_NAME)

# Initialize Recommendation Pipeline
pipeline = RecGenerator()
pipeline.build_pipeline()
pipeline.start_deploy_thread()

# Add producer controller URL
PRODUCER_API_URL = "http://kafka-service:8080/recommend/response"

# Boolean flag to toggle between Kafka and normal response
USE_KAFKA = True

@app.route('/generate', methods=['POST'])
def generate():
    request_id = str(uuid.uuid4())
    logger.info("Request received", extra={'custom': {"request_id": request_id, "endpoint": "/generate"}})

    try:
        with metrics.track_latency(endpoint='/generate'):
            metrics.track_request(method='POST', endpoint='/generate')

            user_id = request.json.get('user_id')
            director = request.json.get('director')
            model = request.json.get('model')

            if user_id is None:
                metrics.track_error(endpoint='/generate', error_type='missing_user_id')
                logger.error("Missing user_id in request", extra={'custom': {"request_id": request_id, "endpoint": "/generate"}})
                return jsonify({"error": "user_id is required"}), 400

            if not pipeline.is_locked:
                recommendations = pipeline.make_recs(int(user_id), director, model)
            else:
                recommendations = pipeline.popular_model.recommend()

            response_data = {
                "timestamp": recommendations["timestamp"],
                "user_id": str(user_id),  # Convert to string if necessary
                "recommendations": [[movie[0], movie[1]] for movie in recommendations["recommendations"]]
            }

            if USE_KAFKA:
                try:
                    print(response_data)
                    producer_response = requests.post(
                        PRODUCER_API_URL,
                        json=response_data,
                        headers={"Content-Type": "application/json"}
                    )

                    print("Producer Response Code:", producer_response.status_code)  # Debug print
                    print("Producer Response Body:", producer_response.text)  # Debug print

                    if producer_response.status_code == 200:
                        return jsonify(response_data), 200
                    else:
                        metrics.track_error(endpoint='/generate', error_type='producer_error')
                        logger.error("Failed to forward to producer",
                                     extra={'custom': {"request_id": request_id, "endpoint": "/generate"}})
                        return jsonify({"error": "Failed to forward to producer",
                                        "details": producer_response.text}), 500

                except requests.exceptions.RequestException as e:
                    metrics.track_error(endpoint='/generate', error_type='producer_connection_error')
                    logger.exception("Producer connection error",
                                     extra={'custom': {"request_id": request_id, "endpoint": "/generate"}})
                    print("Producer Connection Error:", str(e))  # Debug print
                    return jsonify({"error": "Failed to connect to producer",
                                    "details": str(e)}), 500
            else:
                return jsonify(response_data), 200

    except Exception as e:
        logger.exception("Unhandled exception in /generate",
                         extra={'custom': {"request_id": request_id, "endpoint": "/generate"}})
        print("Unhandled Exception:", str(e))  # Debug print
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500


@app.route('/metrics', methods=['GET'])
def metrics_endpoint():
    logger.info("Metrics endpoint accessed", extra={'custom': {"endpoint": "/metrics"}})
    return generate_latest(), 200, {'Content-Type': 'text/plain; charset=utf-8'}

if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=6060, threads=4)



