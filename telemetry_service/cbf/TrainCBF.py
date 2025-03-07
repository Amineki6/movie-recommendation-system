import pandas as pd 
import numpy as np
from sqlalchemy import create_engine
import redis
import os
import numpy as np
import torch
torch.manual_seed(1284)
import pickle
from sqlalchemy import Table, Column, BigInteger, ARRAY, Float, MetaData
from sqlalchemy.dialects.postgresql import insert
import faiss
from cbf import CollaborativeModel
import json
import threading



class DataIngestion:
    def __init__(self, db_url):
        self.engine = create_engine(db_url)
    
    def load_data_100k(self, ratings_df):

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
        db_url = "postgresql://postgres:postgre123@postgresinstance.cpyqmeeock79.eu-north-1.rds.amazonaws.com:5432/postgresdb"
        self.redis_client = redis.StrictRedis(host='localhost', port=6379, decode_responses=True) 
        self.data_ingestion = DataIngestion(db_url)
        self.engine = create_engine(db_url)
        
        self.ratings_df = None
        self.movie_df = None
        self.users = None
        self.data_r = None
        self.data_m = None


    def build_pipeline(self, train_data):
        n_m, n_u, self.data_r, self.data_m, self.movie_map, self.user_map, self.ratings_df, self.movie_ids= self.data_ingestion.load_data_100k(train_data)
        self.cbf = CollaborativeModel.Glocal(n_u, n_m)
        print("CBF Training Pipline Ready!")

    def train(self, movie_ids_to_keep):
        self.cbf.pre_train(self.data_r, self.data_m)
        self.cbf.finetune(self.data_r, self.data_m)
        latent_df, dict_latent, last_5_liked_movies = self.index_latent()
        latent_df = latent_df[latent_df['movie_id'].isin(movie_ids_to_keep)]
        latent_index = self.get_index(latent_df)
        return latent_index, dict_latent, last_5_liked_movies

    def index_latent(self):
        latent_vectors = self.cbf.get_latent().astype(np.float32)
        last_5_liked_movies = self.store_last_liked()
        dict_latent = {int(self.movie_ids[i]): latent_vectors[i] for i in range(len(self.movie_ids))}
        latent_df = pd.DataFrame(dict_latent.items(), columns=['movie_id', 'vector'])
        
        return latent_df, dict_latent, last_5_liked_movies
    
    def store_last_liked(self):
        # Filter movies with rating 4 or above (liked movies)
        liked_movies = self.ratings_df[self.ratings_df['rating'] >= 4]

        # Sort by userId and timestamp to get the most recent first
        liked_movies = liked_movies.sort_values(by=['userId', 'timestamp'], ascending=[True, False])
        
        # Group by userId and keep the last 5 liked movies
        last_5_liked_movies = liked_movies.groupby('userId').head(5)
        
        user_movie_dict = {user_id: group['movieId'].tolist()[:5] for user_id, group in last_5_liked_movies.groupby('userId')}
        
        return user_movie_dict

    def get_index(self, data):
        """Create a FAISS index with explicit ID mapping (no separate metadata needed)."""
        if 'movie_id' not in data.columns:
            raise ValueError("The dataset must contain a 'movie_id' column.")

        movie_ids = data['movie_id'].values.astype(np.int64)  # Convert IDs to int64
        data = data.drop(columns=['movie_id'])  # Drop movie_id from feature data

        # Convert data to numpy array (numerical features only)
        data = np.array(data['vector'].to_list(), dtype=np.float32)

        d = data.shape[1]  # Embedding dimension

        index = faiss.IndexFlatL2(d)  # L2 distance index
        index = faiss.IndexIDMap(index)  # Wrap with ID mapping

        # Add data with explicit IDs
        index.add_with_ids(data, movie_ids)

        return index

