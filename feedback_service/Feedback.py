from sqlalchemy import text 
from sqlalchemy import create_engine
import psycopg2
import redis
import json
import datetime
import numpy as np
import redis
import os

DB_HOST = os.getenv('DB_HOST', 'postgresinstance.cpyqmeeock79.eu-north-1.rds.amazonaws.com')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgre123')
DB_NAME = os.getenv('DB_NAME', 'postgresdb')
REDIS_HOST = os.getenv('REDIS_HOST', '127.0.0.1')
REDIS_PORT = os.getenv('REDIS_PORT', '6379')


db_config = {
    'dbname': DB_NAME,
    'user': DB_USER,
    'password': DB_PASSWORD,
    'host': DB_HOST,
    'port': DB_PORT
}


class ContentBasedModel:
    def __init__(self, redis_client, engine):
        self.redis_client = redis_client
        self.engine = engine

    def update_weights(self, user_id, movie_id, rating, cur):
        try:
            # Get the movie vector 
            movie_vector = self._get_movie_df(movie_id)

            # Scale the movie vector by the rating
            scaled_vector = movie_vector * np.log1p(rating)

            # Find the user's existing vector
            user_vector = self._get_df_user(user_id)

            # Update the user vector
            updated_vector = user_vector + scaled_vector

            self._publish_feedback_db(user_id, updated_vector, cur)
        except IndexError as e:
            raise IndexError(f"IndexError: Unable to find the movie_id or user_id in the DataFrame. Details: {e}")
        except KeyError as e:
            raise KeyError(f"KeyError: Missing key in the DataFrame. Details: {e}")
        except Exception as e:
            raise RuntimeError(f"An unexpected error occurred while updating weights: {e}")

    def _publish_feedback_db(self, user_id, updated_vector, cur):
        try:
            cur.execute(
                "UPDATE df_user SET vector = %s WHERE user_id = %s",
                (updated_vector.tolist(), user_id)
            )
        except Exception as e:
            raise RuntimeError(f"An error occurred in _publish_feedback_db: {e}")
    
    def _get_df_user(self, user_id):
        try:
            query = text('SELECT vector FROM df_user WHERE "user_id" = :userId')

            with self.engine.connect() as connection:
                result = connection.execute(query, {"userId": user_id}).fetchone()   

                if result:
                    user_vector = np.array(result[0], dtype=np.float32)
                else:
                    raise RuntimeError

            return user_vector
        except Exception as e:
            raise RuntimeError(f"Error fetching df_user for user {user_id}: {e}")

    def _get_movie_df(self, movie_id):
        try:
            query = text('SELECT vector FROM movie_df WHERE "movie_id" = :movieId')

            with self.engine.connect() as connection:
                result = connection.execute(query, {"movieId": movie_id}).fetchone()   

                if result:
                    movie_vector = np.array(result[0], dtype=np.float32)
                else:
                    raise RuntimeError

            return movie_vector
        except Exception as e:
            raise RuntimeError(f"Error fetching movie_df for user {movie_id}: {e}")

class HybridModel:
    def __init__(self, redis_client, engine):
        self.content_based_model = ContentBasedModel(redis_client, engine)
        self.redis_client = redis_client
        self.engine = engine

        self.conn = psycopg2.connect(**db_config)
        self.cursor = self.conn.cursor()
        self.redis_pipe = self.redis_client.pipeline() 
    
    def feedback_transaction(self, user_id, movie_id, rating):
        seen_movies = None
        pipe_execution = False

        print(f"Processing Feedback for {user_id}...")
        try:
            with self.conn:
                with self.conn.cursor() as cur:
                    self.conn.autocommit = False 

                    # Step 1: Mark the feedback as "pending" in PostgreSQL
                    try:
                        timestamp = datetime.datetime.now() 
                        cur.execute(
                            "INSERT INTO feedbacks (user_id, movie_id, rating, status, timestamp) VALUES (%s, %s, %s, %s, %s)",
                            (user_id, movie_id, rating, "pending", timestamp),
                        )
                    except Exception as feedbacks_error:
                        raise RuntimeError(f"Failed to update feedbacks: {feedbacks_error}") from feedbacks_error

                    # Step 2: Apply the updates to PostgreSQL
                    try:
                        self._publish_ratings_df(user_id, movie_id, rating, cur)
                    except Exception as ratings_df_error:
                        raise RuntimeError(f"Failed to update ratings_df: {ratings_df_error}") from ratings_df_error

                    # Step 3: Update content-based model weights in DB
                    try:
                        self.content_based_model.update_weights(user_id, movie_id, rating, cur)
                    except Exception as content_error:
                        raise RuntimeError(f"Content-based model update failed: {content_error}") from content_error

                    # Step 5: Update seen_movies in Redis
                    try:
                        seen_movies = self._publish_seen_movies(self.redis_pipe, user_id, movie_id=movie_id)   
                    except Exception as seen_movies_error:
                        raise RuntimeError(f"Seen movies publish failed: {str(seen_movies_error)}") from seen_movies_error

                    # Step 6: Update last_liked in Redis
                    try:
                        if rating >= 4:
                            last_liked = self._publish_last_liked(self.redis_pipe, user_id, movie_id)
                    except Exception as last_liked_error:
                        raise RuntimeError(f"Last liked publish failed: {str(last_liked_error)}") from last_liked_error

                    # Finalize and execute the Redis pipeline
                    try:
                        pipe_execution = True
                        self.redis_pipe.execute()
                    except Exception as redis_error:
                        raise RuntimeError(f"Redis pipeline execution failed: {str(redis_error)}") from redis_error   

                    cur.execute(
                        "UPDATE feedbacks SET status = %s WHERE user_id = %s AND movie_id = %s",
                        ("completed", user_id, movie_id),
                    )
                    self.conn.commit()
            print("Feedback transaction executed successfully.")

        except Exception as e:
            # If anything fails, rollback PostgreSQL and Redis changes
            self.conn.rollback()
            print(f"Error processing feedback: {e}")
            if pipe_execution:
                try:
                    self._rollback_redis(user_id, seen_movies)
                except Exception as rollback_error:
                    print(f"Rollback itself failed for {user_id}, {movie_id}: {rollback_error}")
                    # Flag the transaction in PostgreSQL for manual intervention
                    with self.conn:
                        with self.conn.cursor() as cur:
                            cur.execute(
                                "UPDATE feedbacks SET status = %s WHERE user_id = %s AND movie_id = %s",
                                ("rollback_failed", user_id, movie_id),
                            )

                    # Reraise the error or log it for further inspection
                    raise RuntimeError(f"Critical failure: rollback attempt also failed: {rollback_error}")

            # Raise the error to trigger PostgreSQL rollback (automatically handled by `with conn`)
            raise RuntimeError(f"Feedback processing failed: {str(e)}") from e
        finally:
            self.conn.autocommit = True

    def _rollback_redis(self, user_id, seen_movies):
        rollback_pipe = self.redis_client.pipeline()

        if seen_movies is not None:
            self._publish_seen_movies(rollback_pipe, user_id, movie_list=seen_movies)
            print("Rollback Seen movies update to pipe")

        rollback_pipe.execute()


    def _publish_ratings_df(self, user_id, movie_id, rating, cursor):
        try:
            timestamp = datetime.datetime.now()            
            cursor.execute(
                """
                INSERT INTO ratings_df (user_id, movie_id, rating, timestamp)
                VALUES (%s, %s, %s, %s)
                """,
                (user_id, movie_id, rating, int(timestamp.timestamp()))  
            )

            print(f"New rating row inserted for user {user_id} in ratings_df") 
        except Exception as e:
            raise RuntimeError(f"An error occurred in _publish_ratings_df: {e}")


    def _get_seen_movies_from_redis(self, user_id):
        try:
            seen_movies_json = self.redis_client.get(f'user:{user_id}:seen')
            
            if seen_movies_json:
                seen_movies = json.loads(seen_movies_json)
                return seen_movies
            else:
                return []

        except Exception as e:
            raise RuntimeError(f"Error fetching seen movies for user {user_id}: {e}")

        
    def _publish_seen_movies(self, redis_pipe, user_id, movie_id = None, movie_list = None):
        try:
            if movie_id:
                seen_movies = self._get_seen_movies_from_redis(user_id)
                updated_seen_movies = seen_movies
                if movie_id not in seen_movies:
                    updated_seen_movies.append(movie_id)

                redis_pipe.set(f'user:{user_id}:seen', json.dumps(updated_seen_movies))
                print(f"Added to pipe for user_seen_movies:{user_id}!")
                return seen_movies
            if movie_list:
                redis_pipe.set(f'user_seen_movies:{user_id}', json.dumps(movie_list))
                print(f"Added to pipe for rollback user_seen_movies:{user_id}!")
                
        except Exception as e:
            raise RuntimeError(f"Error updating seen movies for user {user_id}: {e}")
        
    def _publish_last_liked(self, redis_pipe, user_id, movie_id):
        try:
            redis_key = f"user:{user_id}:last_liked"

            # Load the existing list from Redis (using redis_client, not redis_pipe)
            last_liked_data = self.redis_client.get(redis_key)
            last_liked_rollback = json.loads(last_liked_data) if last_liked_data else []

            # Only pop the last element if the length of last_liked_rollback is 5
            if len(last_liked_rollback) == 5:
                last_liked_rollback.pop()
            
            # Create the updated list with the new movie_id at the beginning
            new_last_liked = [movie_id] + last_liked_rollback
            
            # Update the Redis list with the modified version by saving it as a JSON string
            redis_pipe.set(redis_key, json.dumps(new_last_liked))

            return last_liked_rollback
        except Exception as e:
            raise RuntimeError(f"Error updating last_liked for user {user_id}: {e}")



class FeedbackPipeline:
    def __init__(self):
        db_url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        self.redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        self.engine = create_engine(db_url)
        self.hybrid_model = None

        self.movie_df = None

    def build_pipeline(self):
        print("Downloading and loading data...")
        self.hybrid = HybridModel(self.redis_client, self.engine)
        print("Feedback Pipline Ready!")
    
    def feedback(self, user_id, movie_id, rating):
        try:
            self.hybrid.feedback_transaction(user_id, movie_id, rating)
            self._clear_redis_cache(user_id)
            return {"success": True, "message": "Feedback processed successfully."}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _clear_redis_cache(self, user_id):
        try:
            key = f"user:{user_id}:df_user"
            self.redis_client.delete(key)
            print(f"Cleared cache for {key}")
        except Exception as e:
            raise RuntimeError(f"An error occurred while publishing feedback to Redis: {e}")


