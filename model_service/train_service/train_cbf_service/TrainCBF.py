import pandas as pd 
import numpy as np
from sqlalchemy import create_engine
import redis
import numpy as np
import torch
torch.manual_seed(1284)
from sqlalchemy import Table, Column, BigInteger, ARRAY, Float, MetaData
from sqlalchemy.dialects.postgresql import insert

from  train_cbf_service import CollaborativeModel
import json
import threading
import os

# Get database connection details from environment variables
DB_HOST = os.getenv('DB_HOST', 'postgresinstance.cpyqmeeock79.eu-north-1.rds.amazonaws.com')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgre123')
DB_NAME = os.getenv('DB_NAME', 'postgresdb')
REDIS_HOST = os.getenv('REDIS_HOST', '127.0.0.1')
REDIS_PORT = os.getenv('REDIS_PORT', '6379')

class DataIngestion:
    def __init__(self, db_url):
        self.engine = create_engine(db_url)
    
    def load_data_100k(self):
        # Load dataset
        ratings_query = "SELECT * FROM public.ratings_df"
        ratings_df = pd.read_sql(ratings_query, self.engine)

        ratings_df = ratings_df.rename(columns={
            'user_id': 'userId',
            'movie_id': 'movieId'
        })

        ratings_df['movieId'] = ratings_df['movieId'].astype(int)
    
        # Extract unique user and movie IDs
        unique_users = np.unique(ratings_df['userId'])
        unique_movies = np.unique(ratings_df['movieId'])

        n_u = len(unique_users)  # Number of unique users
        n_m = len(unique_movies)  # Number of unique movies
        n_ratings = ratings_df.shape[0]  # Total number of ratings

        # Create mappings from userId/movieId to matrix indices
        user_map = {uid: i for i, uid in enumerate(unique_users)}
        movie_map = {mid: i for i, mid in enumerate(unique_movies)}

        # Initialize rating matrix
        data_r = np.zeros((n_m, n_u), dtype='float32')

        # Populate the matrix
        for _, row in ratings_df.iterrows():
            user_idx = user_map[row['userId']]
            movie_idx = movie_map[row['movieId']]
            data_r[movie_idx, user_idx] = row['rating']

        # Create a mask matrix (1 if rating exists, 0 otherwise)
        data_m = (data_r > 0).astype('float32')

        print('Data matrix loaded')
        print(f'Num of users: {n_u}')
        print(f'Num of movies: {n_m}')
        print(f'Num of ratings: {n_ratings}')

        return n_m, n_u, data_r, data_m, movie_map, user_map, ratings_df, list(unique_movies)


class TrainPipelineCBF:
    def __init__(self):
        db_url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        self.redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True) 
        self.data_ingestion = DataIngestion(db_url)
        self.engine = create_engine(db_url)
        
        self.ratings_df = None
        self.movie_df = None
        self.users = None
        self.data_r = None
        self.data_m = None

        self.pubsub = self.redis_client.pubsub()
        self.pubsub.subscribe("nodes_version")

    def build_pipeline(self):
        n_m, n_u, self.data_r, self.data_m, self.movie_map, self.user_map, self.ratings_df, self.movie_ids= self.data_ingestion.load_data_100k()
        self.cbf = CollaborativeModel.Glocal(n_u, n_m)
        print("CBF Training Pipline Ready!")

    def train(self, num_nodes, online = False):
        self.cbf.pre_train(self.data_r, self.data_m)
        self.cbf.finetune(self.data_r, self.data_m)
        self.index_latent()
        if online:
            current_version = self.redis_client.get("version")
            if current_version is None:
                new_version = 1
            else:
                new_version = int(current_version) + 1
            self.redis_client.set("version", str(new_version))
            self.start_worker(num_nodes)
            
    def finetune(self):
        self.cbf.finetune(self.data_r, self.data_m)

    def index_latent(self):
        print("Saving Latent vectors to Database...")
        latent_vectors = self.cbf.get_latent().astype(np.float32)
        
        # Save vectors to DB
        metadata = MetaData()
        latent_table = Table(
            "latent_vectors", metadata,
            Column("movie_id", BigInteger, primary_key=True),
            Column("vector", ARRAY(Float))
        )

        # Insert or update records
        with self.engine.connect() as conn:
            for movie_id, vector in zip(self.movie_ids, latent_vectors):
                stmt = insert(latent_table).values(
                    movie_id=int(movie_id),  # Convert np.int64 to int
                    vector=vector.tolist()   # Convert np.array to list
                )
                stmt = stmt.on_conflict_do_update(
                    index_elements=['movie_id'], 
                    set_={'vector': stmt.excluded.vector}
                )
                conn.execute(stmt)
            conn.commit()

        print("Latent vectors saved to PostgreSQL")

    def cbf_init_redis(self):
        # Filter movies with rating 4 or above (liked movies)
        liked_movies = self.ratings_df[self.ratings_df['rating'] >= 4]

        # Sort by userId and timestamp to get the most recent first
        liked_movies = liked_movies.sort_values(by=['userId', 'timestamp'], ascending=[True, False])
        
        # Group by userId and keep the last 5 liked movies
        last_5_liked_movies = liked_movies.groupby('userId').head(5)
        
        # Store in Redis (key: userId, value: JSON-encoded list of movieIds)
        for user_id, group in last_5_liked_movies.groupby('userId'):
            movie_ids = group['movieId'].tolist()[:5]  # Ensure only last 5 movies are kept
            redis_key = f"user:{user_id}:last_liked"
            
            # Clear existing value and store as a JSON string
            self.redis_client.delete(redis_key)
            self.redis_client.set(redis_key, json.dumps(movie_ids))
        
        print("last_liked saved to Redis")
    
    def listen_for_updates(self, count):
        if count == 0:
            print("No updates to listen for. Exiting...")
            return

        print(f"Node listening for {count} nodes update feedback messages...")
        received = 0
        for message in self.pubsub.listen():
            if message["type"] == "message":
                data = message["data"]
                print(f"Received update {received + 1}: {data}")
                received += 1
                if received >= count:
                    break

    
    def start_worker(self, count):
        worker_thread = threading.Thread(target=self.listen_for_updates, args=(count,),daemon=True)
        worker_thread.start()
        worker_thread.join()

