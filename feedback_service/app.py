from flask import Flask, request, jsonify
from Feedback import FeedbackPipeline
from flask_cors import CORS
from prometheus_client import generate_latest, Gauge
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
SERVICE_NAME = "feedback_service"

# Set up MongoDB logging using the shared module
DB_URI = os.environ.get('DB_URI', 'mongodb://localhost:27017')
logger = setup_mongo_logging(SERVICE_NAME, db_uri=DB_URI)

# Initialize Metrics for this Service
metrics = Metrics(SERVICE_NAME)

# Initialize the FeedbackPipeline and build the pipeline
feedback_pipeline = FeedbackPipeline()
feedback_pipeline.build_pipeline()

rating_sum = {
    '01': Gauge('movie_rating_sum_01', 'Sum of ratings for model source 01'),
    '02': Gauge('movie_rating_sum_02', 'Sum of ratings for model source 02'),
    '03': Gauge('movie_rating_sum_03', 'Sum of ratings for model source 03')
}

rating_count = {
    '01': Gauge('movie_rating_count_01', 'Count of ratings for model source 01'),
    '02': Gauge('movie_rating_count_02', 'Count of ratings for model source 02'),
    '03': Gauge('movie_rating_count_03', 'Count of ratings for model source 03')
}


@app.route('/feedback', methods=['POST'])
def feedback():
    request_id = str(uuid.uuid4())
    logger.info("Request received", extra={'custom': {"request_id": request_id, "endpoint": "/feedback"}})
    with metrics.track_latency(endpoint='/feedback'):
        metrics.track_request(method='POST', endpoint='/feedback')

        try:
            data = request.get_json()
            if not data:
                metrics.track_error(endpoint='/feedback', error_type='no_input_data')
                logger.error("No input data provided", extra={'custom': {"request_id": request_id, "endpoint": "/feedback"}})
                return jsonify({"error": "No input data provided"}), 400

            user_id = int(data.get('user_id'))
            movie_id = int(data.get('movie_id'))
            rating = float(data.get('rating'))
            source = data.get('source')

            if user_id is None or movie_id is None or rating is None:
                metrics.track_error(endpoint='/feedback', error_type='missing_fields')
                logger.error("Missing required fields", extra={'custom': {"request_id": request_id, "endpoint": "/feedback"}})
                return jsonify({"error": "user_id, movie_id, and rating are required"}), 400

            
            result = feedback_pipeline.feedback(user_id, movie_id, rating)
            
            rating_sum[source].inc(rating)
            rating_count[source].inc(1)
            

            if not result.get("success", True):
                metrics.track_error(endpoint='/feedback', error_type='processing_error')
                logger.error("Feedback processing error", extra={'custom': {"request_id": request_id, "endpoint": "/feedback","error": result.get("error","Unknown error occurred")}})
                return jsonify({"error": result.get("error", "Unknown error occurred"), "userId": user_id, "movieId": movie_id}), 500

            return jsonify({"userId": user_id, "movieId": movie_id, "message": "Feedback successfully processed"}), 200
        except Exception as e:
            metrics.track_error(endpoint='/feedback', error_type='exception')
            logger.exception("Exception occurred", extra={'custom': {"request_id": request_id, "endpoint": "/feedback", "error": str(e)}})
            return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@app.route('/metrics', methods=['GET'])
def metrics_endpoint():
    logger.info("Metrics endpoint accessed", extra={'custom': {"endpoint": "/metrics"}})
    return generate_latest(), 200, {'Content-Type': 'text/plain; charset=utf-8'}

if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=6090, threads=4)
