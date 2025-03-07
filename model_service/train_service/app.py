from flask import Flask, request, jsonify
from flask_cors import CORS
from train_cbf_service.TrainCBF import TrainPipelineCBF
from train_cb_service.TrainCB import TrainPipelineCB
import uuid
import sys
import os
import json
import threading 
from waitress import serve
from telemetry_service.log_handler import setup_mongo_logging

app = Flask(__name__)
CORS(app, supports_credentials=True)

# Service Name
SERVICE_NAME = "train_service"

# Set up MongoDB logging using the shared module
DB_URI = os.environ.get('DB_URI', 'mongodb://localhost:27017')
logger = setup_mongo_logging(SERVICE_NAME, db_uri=DB_URI)

train_cbf = TrainPipelineCBF()
train_cb = TrainPipelineCB()

train_cb.build_pipeline()
train_cbf.build_pipeline()

# Global Lock for synchronizing training requests
train_lock = threading.Lock()

@app.route('/train', methods=['POST'])
def train():
    request_id = str(uuid.uuid4())  # Unique ID for tracking the request
    logger.info("Request received", extra={'custom': {"request_id": request_id, "endpoint": "/train"}})
    
    if not train_lock.acquire(blocking=False):  # Check if another process is running
        logger.warning("Training request rejected due to ongoing process", extra={'custom': {"request_id": request_id}})
        return jsonify({"error": "Training is already in progress. Please wait until the current process completes."}), 429
    
    try:
        # Extract JSON payload with defaults set to True
        data = request.get_json()
        if len(data) > 4:
            data = data["message"]
            data = json.loads(data)
        
        train_cb_check = data.get('train_cb')
        train_cbf_check = data.get('train_cbf')
        online = data.get('online')
        num_nodes = data.get('num_nodes', 0)

        # Execute the training pipeline with parameters
        if train_cb_check:
            train_cb.train()
            logger.info("CB training completed", extra={'custom': {"request_id": request_id, "model": "CB"}})
        if train_cbf_check:
            train_cbf.train(num_nodes=num_nodes, online=online)
            logger.info("CBF training completed", extra={'custom': {"request_id": request_id, "model": "CBF", "online": online}})

        return jsonify({"message": "Training pipeline executed successfully"}), 200

    except Exception as e:
        logger.exception("Exception occurred during training", extra={'custom': {"request_id": request_id}})
        return jsonify({"error": str(e)}), 500

    finally:
        train_lock.release()  # Ensure the lock is released after execution

@app.route('/initialize', methods=['POST'])
def initialize_cbf():
    request_id = str(uuid.uuid4())
    logger.info("Initialization request received", extra={'custom': {"request_id": request_id, "endpoint": "/initialize-cbf"}})
    try:
        train_cb.cb_init_redis()
        train_cbf.cbf_init_redis()
        logger.info("Pipeline initialized", extra={'custom': {"request_id": request_id}})
        return jsonify({"message": "Pipeline initialized successfully"}), 200
    except Exception as e:
        logger.exception("Exception occurred during initialization", extra={'custom': {"request_id": request_id}})
        return jsonify({"error": str(e)}), 500
    
if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=7070, threads=4)
