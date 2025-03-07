from sqlalchemy import create_engine
from sqlalchemy import text 
import redis
import json
import time
import random
import time
import os

DB_HOST = os.getenv('DB_HOST', 'postgresinstance.cpyqmeeock79.eu-north-1.rds.amazonaws.com')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgre123')
DB_NAME = os.getenv('DB_NAME', 'postgresdb')
REDIS_HOST = os.getenv('REDIS_HOST', '127.0.0.1')
REDIS_PORT = os.getenv('REDIS_PORT', '6379')


class PopularityBasedModel:
    def __init__(self, redis_client, utility_functions):
        self.redis_client = redis_client
        self.utility_functions = utility_functions
        self.popular_movies = []
        self.fetch_movies()

    def fetch_movies(self):
        if not self.popular_movies:
            popular_movies_key = 'popular_movies:03'
            popular_movies_json = self.redis_client.get(popular_movies_key)
            if popular_movies_json:
                popular_movies_json_load = json.loads(popular_movies_json)
                self.popular_movies = [(movie['movie_id'], movie['source']) for movie in popular_movies_json_load]
    
    def recommend(self, cold=False):      
        self.fetch_movies()
        seen_movies = set(self.utility_functions.user_seen_movies)
        popular_recs = [tup for tup in self.popular_movies if tup[0] not in seen_movies]
        popular_recs_shuffled = random.sample(popular_recs, min(20, len(popular_recs)))

        if cold:
            popular_recs_shuffled = [(num, '03:c') if code == '03' else (num, code) for num, code in popular_recs_shuffled]

        recs = {"timestamp": int(time.time()), "recommendations": popular_recs_shuffled}
        return recs
    
    def recommend_list(self):      
        self.fetch_movies()
        seen_movies = set(self.utility_functions.user_seen_movies)
        recs_list = [tup for tup in self.popular_movies if tup[0] not in seen_movies]
        return recs_list

        

class UtilityFunctions:
    def __init__(self, redis_client, engine):
        self.redis_client = redis_client
        self.user_seen_movies = None
        self.engine = engine

    def get_seen_movies_from_redis(self, user_id):
        try:
            # Fetch the data from Redis
            seen_movies_json = self.redis_client.get(f'user:{user_id}:seen')
            
            # If the key exists, parse the JSON data into a list
            if seen_movies_json:
                self.user_seen_movies = json.loads(seen_movies_json)
                return self.user_seen_movies
            else:
                # Return an empty list if the user has no data in Redis
                return []

        except Exception as e:
            print(f"Error fetching seen movies for user {user_id}: {e}")
            return []
    

class RecFetcher:
    def __init__(self):
        db_url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        self.redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        self.engine = create_engine(db_url)
        self.uf = UtilityFunctions(self.redis_client, self.engine)
        self.popular_model = PopularityBasedModel(self.redis_client, self.uf)

    def recs(self, user_id):
        try:
            seen_movies = self.uf.get_seen_movies_from_redis(user_id)
            
            if len(seen_movies) < 5:
                recs = self.popular_model.recommend(cold=True)    
                return recs

            recs = self.get_recs(user_id)

        except Exception as e:
            print(f"Error occurred while getting recommendation: {e}")
            return self.popular_model.recommend()

        return recs
        

    def get_recs(self, user_id):
        recs = self.redis_client.get(f"user:{user_id}:recs")
        
        if recs is None:
            query = text("SELECT recommendations ,timestamp FROM user_recs WHERE user_id = :user_id")
            with self.engine.connect() as connection:
                result = connection.execute(query, {"user_id": user_id})
                recs_row = result.fetchone()
            
            if recs_row is None:
                recs = self.popular_model.recommend() 
                return recs
            else:
                print("recs from db")
                recs = {
                    "timestamp": int(recs_row.timestamp.timestamp()) if recs_row.timestamp else int(time.time()),
                    "recommendations": recs_row.recommendations
                }

        else:
            print("recs from redis")
            recs = json.loads(recs)

        return recs
    

