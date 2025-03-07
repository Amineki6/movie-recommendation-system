import pandas as pd  
import numpy as np
from sqlalchemy import create_engine, text
import redis
import json
import faiss
import os
from sqlalchemy import create_engine, Column, BigInteger
from sqlalchemy.dialects.postgresql import ARRAY, FLOAT
from sqlalchemy import Table, MetaData


# Get database connection details from environment variables
DB_HOST = os.getenv('DB_HOST', 'postgresinstance.cpyqmeeock79.eu-north-1.rds.amazonaws.com')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgre123')
DB_NAME = os.getenv('DB_NAME', 'postgresdb')
REDIS_HOST = os.getenv('REDIS_HOST', '127.0.0.1')
REDIS_PORT = os.getenv('REDIS_PORT', '6379')


class DataIngestion:
    def __init__(self, db_url, redis_client):
        self.engine = create_engine(db_url)
        self.redis_client = redis_client

    def fetch_weights(self):
        movies_df_query = "SELECT * FROM public.movie_df"
        movie_df = pd.read_sql(movies_df_query, self.engine)

        ratings_query = "SELECT * FROM public.ratings_df"
        ratings_df = pd.read_sql(ratings_query, self.engine)

        users_query = "SELECT user_id FROM public.users"
        users = pd.read_sql(users_query, self.engine)

        recent_movie_query = text("""
            SELECT tmdbid, title, overview, vote_average, director, movie_id FROM movies
            WHERE release_date IS NOT NULL
            ORDER BY release_date DESC
            LIMIT 50;
        """)

        with self.engine.connect() as conn:
            result = conn.execute(recent_movie_query)
            movies = result.fetchall()
            movie_dicts = [
                    {
                        "tmdbid": int(movie[0]),  # Convert Decimal to int
                        "title": movie[1],
                        "overview": movie[2],
                        "vote_average": float(movie[3]),  # Convert Decimal to float
                        "director": movie[4],
                        "movie_id": int(movie[5])  # Convert Decimal to int
                    }
                    for movie in movies
                ]
            

        self.redis_client.set("recent_movies", json.dumps(movie_dicts))
        
        return movie_df, ratings_df, users
    
class TrainContentBasedModel:
    def __init__(self, db_url, movie_df, ratings_df, uf):
        self.movie_df = movie_df
        self.ratings_df = ratings_df
        self.df_user = None
        self.engine = create_engine(db_url)
        self.uf = uf
    
    def train(self):
        print("Training Content Based Model...")
        # Step 1: Merge ratings_df with movie_df on movie_id
        merged_df = self.ratings_df.merge(self.movie_df, on='movie_id')
        merged_df['adjusted_rating'] =  np.log(merged_df['rating'])
        # Step 2: Multiply features by the rating
        merged_df['vector'] = merged_df.apply(
            lambda row: np.array(row['vector']) * row['adjusted_rating'], axis=1
        )

        # Step 3: Group by user_id and sum across features
        user_features = merged_df.groupby('user_id')['vector'].sum().reset_index()
        self.df_user = user_features

        self.df_user["vector"] = self.df_user["vector"].apply(lambda row: row.tolist())

        metadata = MetaData()
        df_user_table = Table(
            "df_user", metadata,
            Column("user_id", BigInteger, primary_key=True),
            Column("vector", ARRAY(FLOAT))
        )
        metadata.create_all(self.engine)
        self.df_user.to_sql('df_user', con=self.engine, if_exists='replace', index=False, dtype={"vector": ARRAY(FLOAT)})

        self.uf.clear_redis_cache()

class UtilityFunctions:
    def __init__(self, redis_client):
        self.redis_client = redis_client

    def save_seen_movies_to_redis(self, users, ratings_df):
        try:
            # Clear all existing user_seen_movies keys
            keys = self.redis_client.keys('user_seen_movies:*')
            if keys:
                self.redis_client.delete(*keys)
            
            for user_id in users['user_id']:
                seen_movies = ratings_df[ratings_df['user_id'] == user_id]['movie_id'].tolist()
                self.redis_client.set(f'user:{user_id}:seen', json.dumps(seen_movies))

            print("User seen movies saved to Redis.")
        except Exception as e:
            print(f"Error: {e}")

    def save_popular_movies(self, ratings_df):
        try:
            # Calculate movie scores
            movie_scores = ratings_df.groupby('movie_id').agg(
                popularity=('rating', 'count'),
                likeability=('rating', 'mean')
            ).assign(
                popularity_likeability_score=lambda x: x['popularity'] * 0.5 + x['likeability'] * 0.5
            ).sort_values(by='popularity_likeability_score', ascending=False).reset_index()

            # Select the top 50 movies
            top_movies = movie_scores.head(50).loc[:, ['movie_id']]
            top_movies['source'] = "03"

            # Save the movie IDs and source to Redis
            popular_movies = top_movies.to_dict('records')  # Convert to a list of dictionaries
            self.redis_client.set('popular_movies:03', json.dumps(popular_movies))
            print("Popular movies saved to Redis.")
        except Exception as e:
            print(f"Error in saving popular movies: {e}") 
    
    def clear_redis_cache(self):
        keys_to_delete = self.redis_client.keys('user:*:df_user')
        
        # Delete each key
        if keys_to_delete:
            self.redis_client.delete(*keys_to_delete)
            print(f"Cleared df_user cache for {len(keys_to_delete)} keys.")
        else:
            print("No df_user cache found to delete.")


class TrainPipelineCB:
    def __init__(self):
        self.db_url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        self.redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True) 
        self.data_ingestion = DataIngestion(self.db_url, self.redis_client)
    
    def build_pipeline(self):
        self.movie_df, self.ratings_df, self.users = self.data_ingestion.fetch_weights()
        self.uf = UtilityFunctions(self.redis_client)
        self.train_cb = TrainContentBasedModel(self.db_url, self.movie_df, self.ratings_df, self.uf)
        print("CB Training Pipline Ready!")

    def train(self):
        self.train_cb.train()

    def cb_init_redis(self):
        self.uf.save_seen_movies_to_redis(self.users, self.ratings_df)
        self.uf.save_popular_movies(self.ratings_df)

