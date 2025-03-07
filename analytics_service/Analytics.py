import redis
import json
import psycopg2
import pickle
import numpy as np
import random
from sqlalchemy import create_engine
from sqlalchemy import text 
import os

# Get database connection details from environment variables
DB_HOST = os.getenv('DB_HOST', 'postgresinstance.cpyqmeeock79.eu-north-1.rds.amazonaws.com')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgre123')
DB_NAME = os.getenv('DB_NAME', 'postgresdb')
REDIS_HOST = os.getenv('REDIS_HOST', '127.0.0.1')
REDIS_PORT = os.getenv('REDIS_PORT', '6379')
MODELS_PATH = os.getenv('MODELS_PATH', '..\database_service\saved_models\pca_model_thousand.pkl')

# Use the environment variables in the configuration dictionary
db_config = {
    'dbname': DB_NAME,
    'user': DB_USER,
    'password': DB_PASSWORD,
    'host': DB_HOST,
    'port': DB_PORT
}

class Analytics:
    def __init__(self):
        db_url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        self.engine = create_engine(db_url)
        self.redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True) 

        model_path = MODELS_PATH
        with open(model_path, 'rb') as file:
            self.pca_model = pickle.load(file)
        
        # Store your columns list once
        self.columns = [
            "vote_average", "release_year", "Adventure", "Animation", "Children",
            "Comedy", "Fantasy", "Romance", "Drama", "Action", "Crime", "Thriller",
            "Horror", "Mystery", "Sci-Fi", "IMAX", "Documentary", "War", "Musical",
            "Western", "Film-Noir", "original_language_en", "original_language_other"
        ]
        
        # Create a dictionary for direct column-index lookup
        self.col_to_idx = {col: i for i, col in enumerate(self.columns)}
        
        # Define your genre and language columns once
        self.genre_columns = [
            "Adventure", "Animation", "Children", "Comedy", "Fantasy",
            "Romance", "Drama", "Action", "Crime", "Thriller", "Horror",
            "Mystery", "Sci-Fi", "IMAX", "Documentary", "War", "Musical",
            "Western", "Film-Noir"
        ]
        self.language_columns = ["original_language_en", "original_language_other"]

    def get_user_history(self, user_id):
        seen_movies = self._get_seen_movies_from_redis(user_id)
        if not seen_movies:
            return {
                "userId": user_id,
                "history": {},
                "movies_seen": 0
            }
        num_seen_movies = len(seen_movies)
        try:
            connection = psycopg2.connect(**db_config)
            cursor = connection.cursor()

            # Batch fetch all movies in a single query
            query = """
                SELECT user_id, movie_id, rating
                FROM ratings_df 
                WHERE user_id = %s AND movie_id = ANY(%s);
            """

            cursor.execute(query, (user_id, seen_movies))
            results = cursor.fetchall()

            if not results:
                return {}

            # Convert query results into a dictionary (movieId -> rating)
            movies = [(movie, float(rating)) for _, movie, rating in results]

            # Group movies by rating
            rating_groups = {}
            for movie, rating in movies:
                if rating not in rating_groups:
                    rating_groups[rating] = []
                rating_groups[rating].append(movie)

            # Sort ratings in descending order
            sorted_ratings = sorted(rating_groups.keys(), reverse=True)

            # Select movies while ensuring randomness within the same rating group
            top_movies = []
            for rating in sorted_ratings:
                movies_at_rating = rating_groups[rating]
                random.shuffle(movies_at_rating)  # Shuffle to add randomness
                top_movies.extend((movie, rating) for movie in movies_at_rating)

                # Stop when we reach 10 movies
                if len(top_movies) >= 10:
                    break

            # Trim to exactly 10 movies
            top_movies = top_movies[:10]

            # Prepare the user history dictionary
            user_history = {
                "userId": user_id,
                "history": {movie: rating for movie, rating in top_movies},
                "movies_seen": num_seen_movies
            }
            return user_history

        except psycopg2.Error as e:
            print(f"Error while querying the database: {e}")
            return None
    
    def _get_seen_movies_from_redis(self, user_id):
        try:
            # Fetch the data from Redis
            seen_movies_json = self.redis_client.get(f'user:{user_id}:seen')

            # If the key exists, parse the JSON data into a list
            if seen_movies_json:
                seen_movies = json.loads(seen_movies_json)
                return seen_movies
            else:
                # Return an empty list if the user has no data in Redis
                return []

        except Exception as e:
            print(f"Error fetching seen movies for user {user_id}: {e}")
            return []
    
    def get_user_genres_language(self, user_id):
        with self.engine.connect() as connection:
            query = text('SELECT vector FROM df_user WHERE "user_id" = :userId')
            result = connection.execute(query, {"userId": user_id}).fetchone()   

            if result is None:
                genre_scores = {}
                genre_scores['userId'] = user_id
                genre_scores['genres'] = {}
                language_scores = {}
                language_scores['userId'] = user_id
                language_scores = {"English":0, "Other":0}
                return genre_scores, language_scores
            
            user_vector = np.array(result[0], dtype=np.float32)
            
            reconstructed = user_vector @ self.pca_model.components_
            if hasattr(self.pca_model, 'mean_'):
                reconstructed += self.pca_model.mean_

            genre_indices = [self.col_to_idx[g] for g in self.genre_columns]
            genre_values = reconstructed[genre_indices]
            genre_scores = {}
            genre_scores['userId'] = user_id
            genre_scores['genres'] = {
                genre: float(score) for genre, score in zip(self.genre_columns, genre_values)
            }
            
            language_indices = [self.col_to_idx[lang] for lang in self.language_columns]
            language_values = reconstructed[language_indices]
            language_scores = {}
            language_scores['userId'] = user_id
            language_scores = {
                "English": float(language_values[0]),
                "Other": float(language_values[1])
            }
            
        return genre_scores, language_scores

    def get_num_users(self):
        query_total = "SELECT COUNT(*) FROM users WHERE password IS NULL OR password <> 'deleted';"
        try:
            connection = psycopg2.connect(**db_config)
            cursor = connection.cursor()

            # Execute queries
            cursor.execute(query_total)
            total_users = cursor.fetchone()[0]

            # Close the cursor and connection
            cursor.close()
            connection.close()

            return total_users

        except psycopg2.Error as e:
            print(f"Database error: {e}")
            return None
    
    def get_num_movies(self):
        query_total = "SELECT COUNT(*) FROM movies;"        
        try:
            connection = psycopg2.connect(**db_config)
            cursor = connection.cursor()

            # Execute queries
            cursor.execute(query_total)
            total_movies = cursor.fetchone()[0]

            # Close the cursor and connection
            cursor.close()
            connection.close()

            return total_movies

        except psycopg2.Error as e:
            print(f"Database error: {e}")
            return None
    
    def mask_email(self, email):
        """Mask an email by keeping the first character and domain visible."""
        try:
            local_part, domain = email.split("@")
            masked_local = local_part[0] + "***" if len(local_part) > 1 else "*"
            return f"{masked_local}@{domain}"
        except ValueError:
            return "Invalid email format"
        
    def profile(self, user_id):
        query = "SELECT firstname, lastname, email FROM users WHERE user_id = %s;"
        try:
            connection = psycopg2.connect(**db_config)
            cursor = connection.cursor()
            
            cursor.execute(query, (user_id,))
            result = cursor.fetchone()

            if result is None:
                return {"error": "User not found"}
            
            firstname, lastname, email = result
            
            # Mask the email (show first character and domain, mask the rest)
            masked_email = self.mask_email(email)
            
            return {
                "userId": user_id,
                "firstname": firstname,
                "lastname": lastname,
                "email": masked_email
            }
        
        except psycopg2.Error as e:
            print(f"Database error: {e}")
            return None

    