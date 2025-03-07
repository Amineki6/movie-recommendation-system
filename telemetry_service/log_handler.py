import logging
from pymongo import MongoClient
from datetime import datetime, timezone

class MongoDBHandler(logging.Handler):
    def __init__(self, db_uri, db_name, collection_name):
        super().__init__()
        try:
            self.client = MongoClient(db_uri, serverSelectionTimeoutMS=2000)  # 2 seconds timeout
            self.client.admin.command('ping')  # Check connection
        except Exception as e:
            print(f"Failed to connect to MongoDB: {e}")
            self.client = None

        if self.client:
            self.db = self.client[db_name]
            self.collection = self.db[collection_name]


    def emit(self, record):
        """
        Insert a structured log entry into MongoDB.
        We pull out any fields stored in record.__dict__['custom'] for
        user-defined structured data.
        """
        try:
            custom_fields = record.__dict__.get('custom', {})
            
            # Build the log document
            log_data = {
                'message':    record.getMessage(),
                'timestamp':  datetime.now(timezone.utc),
                'level':      record.levelname,
                'logger':     record.name,
                'module':     record.module,
                'funcName':   record.funcName,
                'lineNo':     record.lineno,
                'custom':     custom_fields
            }
            self.collection.insert_one(log_data)
        except Exception:
            # In case something goes wrong in logging, we don't want to crash the app.
            # Optionally, you could print to stderr or handle differently.
            pass


def setup_mongo_logging(service_name,
                       db_uri="mongodb://localhost:27017",
                       db_name="ubflix"):
    """
    Set up MongoDB logging handler for the service.
    Uses a separate collection for each service.
    """
    collection_name = f"{service_name}_logs"
    logger = logging.getLogger(service_name)

    try:
        mongo_handler = MongoDBHandler(db_uri, db_name, collection_name)
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")

    mongo_handler.setLevel(logging.INFO)

    formatter = logging.Formatter('%(message)s')
    mongo_handler.setFormatter(formatter)

    # Avoid adding multiple handlers if logger is reused
    if not logger.hasHandlers():
        logger.addHandler(mongo_handler)
    logger.setLevel(logging.INFO)

    return logger
