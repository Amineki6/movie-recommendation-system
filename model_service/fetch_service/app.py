import sys
import os
import uuid
from flask import Flask, request, jsonify
from flask_cors import CORS
from prometheus_client import generate_latest
from RecFetcher import RecFetcher
from waitress import serve
#sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from telemetry_service.metrics import Metrics
from telemetry_service.log_handler import setup_mongo_logging



# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Service Name
SERVICE_NAME = "fetch_service"

# Set up MongoDB logging using the shared module
DB_URI = os.environ.get('DB_URI', 'mongodb://localhost:27017')
logger = setup_mongo_logging(SERVICE_NAME, db_uri=DB_URI)

# Initialize Metrics for this Service
metrics = Metrics(SERVICE_NAME)

# Initialize Recommendation Pipeline
fetch_recs = RecFetcher()


@app.route('/fetch', methods=['POST'])
def fetch():
    request_id = str(uuid.uuid4())  # Unique ID for tracking the request
    user_id = request.json.get('user_id')

    # Log incoming request with structured logging.
    logger.info(
        "Request received",
        extra={
            'custom': {
                "request_id": request_id,
                "endpoint": "/fetch",
                "user_id": user_id
            }
        }
    )

    # Track metrics
    with metrics.track_latency(endpoint='/fetch'):
        metrics.track_request(method='POST', endpoint='/fetch')

        if user_id is None:
            metrics.track_error(endpoint='/fetch', error_type='missing_user_id')
            logger.error(
                "Missing user_id in request",
                extra={
                    'custom': {
                        "request_id": request_id,
                        "endpoint": "/fetch"
                    }
                }
            )
            return jsonify({"error": "user_id is required"}), 400

        try:
            # Attempt to parse the user_id as an int
            user_id_int = int(user_id)
        except ValueError:
            # If user_id is not an integer, handle gracefully
            metrics.track_error(endpoint='/fetch', error_type='invalid_user_id')
            logger.error(
                "Invalid user_id provided; must be int",
                extra={
                    'custom': {
                        "request_id": request_id,
                        "endpoint": "/fetch",
                        "user_id": user_id
                    }
                }
            )
            return jsonify({"error": "user_id must be a valid integer"}), 400

        try:
            # Fetch recommendations
            recommendations = fetch_recs.recs(user_id_int)
            
            # Validate the structure we expect from RecFetcher
            if (
                not isinstance(recommendations, dict)
                or "timestamp" not in recommendations
                or "recommendations" not in recommendations
            ):
                raise ValueError("RecFetcher returned an unexpected format.")

            logger.info(
                "Fetched recommendations successfully",
                extra={
                    'custom': {
                        "request_id": request_id,
                        "endpoint": "/fetch",
                        "user_id": user_id,
                        "status": "success",
                        "recommendations_count": len(recommendations["recommendations"])
                    }
                }
            )

            # Create response
            response_data = {
                "timestamp": recommendations["timestamp"],
                "user_id": user_id,
                "recommendations": recommendations["recommendations"]
            }

            return jsonify(response_data), 200

        except Exception as e:
            metrics.track_error(endpoint='/fetch', error_type='exception')
            # Use logger.exception to include stack trace in the logs
            logger.exception(
                "Exception occurred while fetching recommendations",
                extra={
                    'custom': {
                        "request_id": request_id,
                        "endpoint": "/fetch",
                        "user_id": user_id
                    }
                }
            )
            return jsonify({"error": str(e)}), 500


@app.route('/metrics', methods=['GET'])
def metrics_endpoint():
    # Log the access with minimal fields
    logger.info(
        "Metrics endpoint accessed",
        extra={
            'custom': {
                "endpoint": "/metrics"
            }
        }
    )
    return generate_latest(), 200, {'Content-Type': 'text/plain; charset=utf-8'}


if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=6062, threads=4)
