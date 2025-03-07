import psycopg2
from bcrypt import hashpw, gensalt
import pandas as pd
from transformers import AutoTokenizer, AutoModel
import torch
import joblib
import numpy as np
import pickle
import json
import redis
import os
import copy


REDIS_HOST = os.getenv('REDIS_HOST', '127.0.0.1')
REDIS_PORT = os.getenv('REDIS_PORT', '6379')


class Database:
    def __init__(self, db_config):
        """
        Initializes the mapper and sets up database connection.

        Args:
            db_config (dict): A dictionary containing database connection parameters.
        """
        self.conn = psycopg2.connect(**db_config)
        self.cursor = self.conn.cursor()
        self.redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True) 

        
        # Load the pretrained model and tokenizer
        model_name = "sentence-transformers/all-MiniLM-L6-v2"
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)

        # Load the PCA and scaler models
        with open('saved_models/pca_model_thousand.pkl', 'rb') as pkl_file:
            self.pca = pickle.load(pkl_file)
        with open('saved_models/scaler_thousand.pkl', 'rb') as pkl_file:
            self.pca_scaler = pickle.load(pkl_file)

        # Load the standardizer model for numerical columns
        self.scaler = joblib.load('saved_models/standardizer_model.pkl')
        self.kmeans = joblib.load('saved_models/kmeans_model.pkl')

    def _get_next_user_id(self):
        """Fetches the next available userId."""
        self.cursor.execute("SELECT MAX(user_id) FROM users")
        max_user_id = self.cursor.fetchone()[0]
        return max_user_id + 1 if max_user_id is not None else 1
    
    def _hash_password(self, plain_password):
        """
        Hashes a plain text password using bcrypt.

        Args:
            plain_password (str): The plain text password.

        Returns:
            str: The hashed password.
        """
        hashed_password = hashpw(plain_password.encode('utf-8'), gensalt())
        return hashed_password.decode('utf-8')
    
    def add_new_user(self, firstname, lastname, email, plain_password):
        """
        Adds a new user to the database and initializes their profile in Redis.
        """
        try:
            new_user_id = self._get_next_user_id()
            
            hashed_password = self._hash_password(plain_password)

            self.cursor.execute(
                """
                INSERT INTO users (user_id, firstname, lastname, email, password)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING user_id
                """,
                (new_user_id, firstname, lastname, email, hashed_password)
            )
            user_id = self.cursor.fetchone()[0]
            
            # Initialize the df_user and push it to Redis
            movie_features = [0.0] * 50
            redis_key = f"user:{user_id}:df_user"
            self.redis_client.set(redis_key, json.dumps(movie_features))

            # Initialize the df_user and push it to DB
            self.cursor.execute(
                """
                INSERT INTO df_user (user_id, vector)
                VALUES (%s, %s)
                """,
                (user_id, movie_features)
            )
            self.conn.commit()

            # Initialize the seen and push it to Redis
            redis_key = f"user:{user_id}:seen"
            self.redis_client.set(redis_key, json.dumps([]))

            # Initialize the last_liked and push it to Redis
            redis_key = f"user:{user_id}:last_liked"
            self.redis_client.set(redis_key, json.dumps([]))

            
            return user_id
        except psycopg2.errors.UniqueViolation as e:
            self.conn.rollback()
            if 'email' in str(e):
                raise ValueError("The email address is already in use. Please choose another one.")
            else:
                raise ValueError(f"Failed to insert new user due to a unique constraint violation: {e}")
        except Exception as e:
            self.conn.rollback()
            raise ValueError(f"An unexpected error occurred: {e}")
        
    def delete_user(self, user_id):
        """
        Soft deletes a user from the database by anonymizing personal details but retaining the userId and feedback data.

        Args:
            user_id (int): The ID of the user to be deleted.

        Returns:
            bool: True if the user was deleted successfully, False if the user was not found or already deleted.
        """
        # Check if the user is already deleted
        self.cursor.execute("SELECT email FROM users WHERE user_id = %s", (user_id,))
        result = self.cursor.fetchone()
        if result is None:
            self.conn.rollback()
            return False  # User not found

        email = result[0]
        if email.startswith("deleted_user_"):
            self.conn.rollback()
            return False  # User already deleted

        # Anonymize personal details but retain userId and feedback data
        anonymized_email = f"deleted_user_{user_id}@example.com"
        self.cursor.execute(
            """
            UPDATE users
            SET firstname = 'Deleted', lastname = 'User', email = %s, password = 'deleted'
            WHERE user_id = %s
            """,
            (anonymized_email, user_id)
        )

        self.conn.commit()
        return True
    
    def _generate_embedding(self, text):
        try:
            inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=128)
            with torch.no_grad():
                outputs = self.model(**inputs)
            # Use the mean pooling of the token embeddings
            embeddings = outputs.last_hidden_state.mean(dim=1)
            return embeddings.squeeze().numpy()
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return None
    
    def _flatten_embedding(self, entry, col_name):
        embedding = entry.get(col_name, None)
        if embedding is not None:
            num_dimensions = len(embedding)
            for i in range(num_dimensions):
                entry[f'{col_name}_{i+1}'] = embedding[i]
            entry.pop(col_name, None)
    
    def _process_single_entry(self, new_entry_movie):
        entry = copy.deepcopy(new_entry_movie)
        # Preserve movie_id
        movie_id = entry.get('movie_id', None)
        
        # Step 1: Concatenate title and overview, handling missing values
        entry['title_overview'] = (entry.get('title', '') + " " + entry.get('overview', '')).strip()
        
        # Remove title and overview
        entry.pop('title', None)
        entry.pop('overview', None)

        # Step 2: Remove unnecessary fields
        fields_to_remove = ['poster_path', 'imdbId', 'tmdbId']
        for field in fields_to_remove:
            entry.pop(field, None)

        # Step 3: Extract release year from release_date
        if 'release_date' in entry and entry['release_date']:
            entry['release_year'] = pd.to_datetime(entry['release_date']).year
            entry.pop('release_date', None)

        # Step 4: Handle missing values for most_popular_cast and director
        entry['most_popular_cast'] = entry.get('most_popular_cast', "Unknown")
        entry['director'] = entry.get('director', "Unknown")

        # Step 5: Generate embeddings for specified columns
        columns_to_embed = ["most_popular_cast", "director", "title_overview"]
        for column in columns_to_embed:
            entry[f"{column}_embedding"] = self._generate_embedding(entry.get(column, ""))


        # Step 6: Standardize numerical columns
        columns_to_standardize = ['release_year', 'vote_average', 'popularity']
        features_to_standardize = np.array([[entry.get(col, 0) for col in columns_to_standardize]])
        standardized_features = self.scaler.transform(features_to_standardize)[0]
        
        for i, column in enumerate(columns_to_standardize):
            entry[column] = standardized_features[i]
        
        # Drop the popularity column
        entry.pop('popularity', None)

        # Step 7: Handle genres
        if 'genres' in entry:
            # Define all unique genres
            all_genres = ['Adventure', 'Animation', 'Children',
            'Comedy', 'Fantasy', 'Romance', 'Drama', 'Action', 'Crime', 'Thriller',
            'Horror', 'Mystery', 'Sci-Fi', 'IMAX', 'Documentary', 'War', 'Musical',
            'Western', 'Film-Noir'] 

            # Create one-hot encoding for genres
            genres_split = entry.get('genres', '').split('|')
            for genre in all_genres:
                entry[genre] = 1 if genre in genres_split else 0

            # Handle '(no genres listed)'
            if '(no genres listed)' in genres_split:
                for genre in all_genres:
                    entry[genre] = 0

            # Remove the original genres field
            entry.pop('genres', None)
        
        # Step 8: One-hot encode original_language
        entry['original_language_en'] = 1 if entry.get('original_language') == 'en' else 0
        entry['original_language_other'] = 1 if entry.get('original_language') != 'en' else 0
        entry.pop('original_language', None)

        # Step 9: Remove processed fields to create trainable structure
        fields_to_remove_for_training = ['most_popular_cast', 'director', 'title_overview', 'movie_id']
        for field in fields_to_remove_for_training:
            entry.pop(field, None)

        # Step 10: Flatten embeddings into separate columns
        embedding_columns = ["most_popular_cast_embedding", "director_embedding", "title_overview_embedding"]
        for col_name in embedding_columns:
            self._flatten_embedding(entry, col_name)

        # Step 11: Prepare features for PCA
        pca_input = np.array([[value for key, value in entry.items() if key != 'movie_id']])  # Exclude movie_id
        pca_scaled_input = self.pca_scaler.transform(pca_input)  # Standardize using pca_scaler
        pca_output = self.pca.transform(pca_scaled_input)[0]  # Apply PCA

        for i, value in enumerate(pca_output):
            entry[f'movie_feature_{i+1}'] = value

        # Remove all other original columns except PCA results
        keys_to_remove = [key for key in entry.keys() if not key.startswith('movie_feature_')]
        for key in keys_to_remove:
            entry.pop(key, None)

        # Add back movie_id
        if movie_id is not None:
            entry['movie_id'] = movie_id

        return entry
    
    def _get_next_movie_id(self):
        """Fetches the next available movie_id."""
        self.cursor.execute("SELECT MAX(movie_id) FROM movies")
        max_movie_id = self.cursor.fetchone()[0]
        return max_movie_id + 1 if max_movie_id is not None else 1
    
    def _convert_numpy_types(self, entry):
        return {key: (int(value) if isinstance(value, np.integer) else 
                    float(value) if isinstance(value, np.floating) else 
                    value)
                for key, value in entry.items()}

    def add_new_movie(self, new_entry):
        """
        Adds a new movie to the database with the given details and updates the movies_df table.

        Args:
            new_entry (dict): A dictionary containing the movie details (keys matching the "movies" table columns).

        Returns:
            int: The newly assigned movie_id.

        Raises:
            ValueError: If the operation fails with a specific reason.
        """
        try:
            # Get the next movie_id (assuming a similar method exists)
            new_movie_id = self._get_next_movie_id()

            # Add the new movie_id to the new_entry dictionary
            new_entry["movie_id"] = new_movie_id

            # Insert the movie into the "movies" table
            self.cursor.execute(
                """
                INSERT INTO movies (
                    movie_id, title, genres, imdbId, tmdbId, most_popular_cast, director, 
                    original_language, overview, popularity, release_date, poster_path, vote_average
                )
                VALUES (
                    %(movie_id)s, %(title)s, %(genres)s, %(imdbId)s, %(tmdbId)s, %(most_popular_cast)s, %(director)s, 
                    %(original_language)s, %(overview)s, %(popularity)s, %(release_date)s, %(poster_path)s, %(vote_average)s
                )
                RETURNING movie_id
                """,
                new_entry
            )
            movie_id = self.cursor.fetchone()[0]

            # Process the entry for movies_df
            new_entry_movie_df = self._process_single_entry(new_entry)
            new_entry_movie_df = self._convert_numpy_types(new_entry_movie_df)


            movie_id = new_entry_movie_df.pop("movie_id")

            # Extract feature values
            vector = list(new_entry_movie_df.values())

            # Construct the final dictionary
            result = {"movie_id": movie_id, "vector": vector}

            #Update the movies_df table
            self.cursor.execute(
                """
                INSERT INTO movie_df (
                    "movie_id",
                    "vector"
                )
                VALUES (
                    %(movie_id)s,
                    %(vector)s
                )
                """,
                result
            )

            # # Commit the transaction
            self.conn.commit()
            return movie_id

        except psycopg2.errors.UniqueViolation as e:
            self.conn.rollback()
            if 'title' in str(e):
                raise ValueError("A movie with this title already exists. Please choose another title.")
            else:
                raise ValueError(f"Failed to insert new movie due to a unique constraint violation: {e}")
        except Exception as e:
            self.conn.rollback()
            raise ValueError(f"An unexpected error occurred: {e}")

    
    def delete_movie(self, movie_id):
        """
        Deletes a movie from both the "movies" and "movies_df" tables based on the given movie_id.
        
        Args:
            movie_id (int): The ID of the movie to be deleted.
        
        Returns:
            bool: True if the movie was successfully deleted, False otherwise.
        
        Raises:
            ValueError: If the operation fails for a specific reason.
        """
        try:
            # Delete from movies_df table first to avoid foreign key constraint issues
            self.cursor.execute(
                """
                DELETE FROM movie_df WHERE movie_id = %s
                """,
                (movie_id,)
            )

            # Delete from movies table
            self.cursor.execute(
                """
                DELETE FROM movies WHERE movie_id = %s
                """,
                (movie_id,)
            )
            
            # Commit the transaction
            self.conn.commit()
            return True
        
        except Exception as e:
            self.conn.rollback()
            raise ValueError(f"An error occurred while deleting the movie: {e}")



    
    def close(self):
        """Closes the database connection."""
        self.cursor.close()
        self.conn.close()

