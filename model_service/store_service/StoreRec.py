import json
from sqlalchemy import create_engine
from sqlalchemy import text 
import schedule
import redis
from datetime import datetime, timezone, timedelta
import threading
import time
import os

DB_HOST = os.getenv('DB_HOST', 'postgresinstance.cpyqmeeock79.eu-north-1.rds.amazonaws.com')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgre123')
DB_NAME = os.getenv('DB_NAME', 'postgresdb')
REDIS_HOST = os.getenv('REDIS_HOST', '127.0.0.1')
REDIS_PORT = os.getenv('REDIS_PORT', '6379')


class StoreRec:
    def __init__(self):
        db_url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        self.redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        self.engine = create_engine(db_url)

        self.start_cleanup_scheduler()

    def recs(self, recs):
        user_id = recs["user_id"]
        self.save_recs_redis(user_id, recs)
        self.save_recs_db(recs)
        
    
    def save_recs_redis(self, user_id, recs):
        key = f"user:{user_id}:recs"
        self.redis_client.set(key, json.dumps(recs), ex=21600)


    def save_recs_db(self, recs):
        ttl = 86400  # 24 hours in seconds
        
        query = text("""
            INSERT INTO user_recs (user_id, recommendations, timestamp, expires_at)
            VALUES (:user_id, :recommendations, :timestamp, NOW() + INTERVAL '24 hours')
            ON CONFLICT (user_id) DO UPDATE 
            SET recommendations = EXCLUDED.recommendations, 
                timestamp = EXCLUDED.timestamp, 
                expires_at = NOW() + INTERVAL '24 hours'
        """
        )

        with self.engine.connect() as connection:
            connection.execute(query, {
                "user_id": recs["user_id"],
                "recommendations":  json.dumps(recs["recommendations"]),
                "timestamp": datetime.fromtimestamp(int(recs["timestamp"]), tz=timezone.utc)
            })
            connection.commit()

    def cleanup_expired_recs(self):
        query = text("DELETE FROM user_recs WHERE expires_at < NOW()")
        with self.engine.connect() as connection:
            connection.execute(query)
            connection.commit()
        print("Expired records cleaned up at", datetime.now())

    def start_cleanup_scheduler(self):
        self.cleanup_expired_recs()
        schedule.every(1).hours.do(self.cleanup_expired_recs)
        
        def run_scheduler():
            while True:
                schedule.run_pending()
                time.sleep(60)  
        thread = threading.Thread(target=run_scheduler, daemon=True)
        thread.start()

