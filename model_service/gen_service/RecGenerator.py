import pandas as pd  
import numpy as np
from sqlalchemy import create_engine
from sqlalchemy import text 
import redis
import json
import faiss
import threading
import time
import random
from datetime import datetime, timezone, timedelta
import os

DB_HOST = os.getenv('DB_HOST', 'postgresinstance.cpyqmeeock79.eu-north-1.rds.amazonaws.com')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgre123')
DB_NAME = os.getenv('DB_NAME', 'postgresdb')
REDIS_HOST = os.getenv('REDIS_HOST', '127.0.0.1')
REDIS_PORT = os.getenv('REDIS_PORT', '6379')

model_version = None

class DataIngestion:
    def __init__(self, engine, redis_client):
        self.engine = engine
        self.redis_client = redis_client

    def fetch_weights(self):
        movies_df_query = "SELECT * FROM public.movie_df"
        movie_df = pd.read_sql(movies_df_query, self.engine)

        movie_latent_query = "SELECT * FROM public.latent_vectors"
        movie_latent = pd.read_sql(movie_latent_query, self.engine)
        
        movie_latent_index = self.get_index(movie_latent)
        movie_df_index = self.get_index(movie_df)

        users_query = "SELECT user_id FROM public.users"
        users = pd.read_sql(users_query, self.engine)

        global model_version 
        model_version = self.redis_client.get("version")
        print(f"Node running on version {model_version}")

        return movie_latent_index, movie_df_index, users
    
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
    
    

    
class ContentBasedModel:
    def __init__(self, redis_client, engine, movie_df_index, uf):
        self.redis_client = redis_client
        self.engine = engine
        self.movie_df_index = movie_df_index
        self.uf = uf

    def recommend(self, userId, director=None, n_rec=20, noise_scale=0.1):
        if director is None:
            print(f"Recommending for user {userId} (CB)...")
        else:
            print(f"Recommending for user {userId} (CB) with director...")
        
        # Get user vector and seen movie IDs
        seen_movie_ids = self.uf.user_seen_movies
        user_vector = self._get_user_vector(userId).reshape(1, -1)    

        if director is not None:
            # Get movie IDs for the selected director
            director_movie_ids = self.uf.get_movies_by_director(director)
            if not director_movie_ids:
                print(f"No movies found for director {director}.")
                return pd.DataFrame(columns=["movie_id"])

            # Create inclusion filter for director's movies
            director_ids_array = np.array(director_movie_ids, dtype=np.int64)
            director_selector = faiss.IDSelectorArray(len(director_movie_ids), faiss.swig_ptr(director_ids_array))

            if seen_movie_ids:
                # Create exclusion filter for seen movies
                seen_ids_array = np.array(seen_movie_ids, dtype=np.int64)
                seen_selector = faiss.IDSelectorBatch(len(seen_movie_ids), faiss.swig_ptr(seen_ids_array))

                # Exclude seen movies from director's movies
                combined_selector = faiss.IDSelectorAnd(director_selector, faiss.IDSelectorNot(seen_selector))
            else:
                # Only filter by director if no seen movies exist
                combined_selector = director_selector
        else:
            # Default: only exclude seen movies
            if seen_movie_ids:
                seen_ids_array = np.array(seen_movie_ids, dtype=np.int64)
                combined_selector = faiss.IDSelectorNot(faiss.IDSelectorBatch(len(seen_movie_ids), faiss.swig_ptr(seen_ids_array)))
            else:
                combined_selector = None  # No filtering needed

        # Perform search with the correct selector
        search_params = faiss.SearchParameters()
        if combined_selector is not None:
            search_params.sel = combined_selector
        
        top_k = 50
        _, recs_cb = self.movie_df_index.search(user_vector, top_k, params=search_params)

        recs_cb_df = pd.DataFrame(recs_cb[0], columns=["movie_id"])
        recs_cb_df = recs_cb_df[recs_cb_df["movie_id"] != -1]
        recs_cb_df = recs_cb_df.sample(frac=1).reset_index(drop=True)

        return recs_cb_df.head(n_rec)
    
    def _get_user_vector(self, userId):
        # Try fetching from Redis
        user_vector = self.redis_client.get(f"user:{userId}:df_user")

        if user_vector is None:
            # Query the database if not found in Redis
            query = text('SELECT vector FROM df_user WHERE "user_id" = :userId')

            with self.engine.connect() as connection:
                result = connection.execute(query, {"userId": userId}).fetchone()   

                if result:
                    # Convert result to NumPy array (excluding the userId column)
                    user_vector = np.array(result[0], dtype=np.float32)
                
                    # Store vector in Redis as JSON with a 6-hour TTL
                    self.redis_client.set(
                        f"user:{userId}:df_user",
                        json.dumps(user_vector.tolist()),  # Convert to JSON string
                        ex=21600  # 6 hours
                    )
                else:
                    return None  
        else:
            # Convert JSON string back to NumPy array
            user_vector = np.array(json.loads(user_vector), dtype=np.float32)

        return user_vector


class CollaborativeBasedModel:
    def __init__(self, movie_latent_index, redis_client, engine, uf):
        self.movie_latent_index = movie_latent_index
        self.redis_client = redis_client
        self.engine = engine
        self.connection = self.engine.connect()
        self.uf = uf
        
    def recommend(self, userId, n_rec=20):
        print(f"Recommending for user {userId} (CFB)...")

        last_liked = self.redis_client.get(f"user:{userId}:last_liked")
        
        if last_liked is not None:
            recs_cbf = self._get_similar_movies(json.loads(last_liked), n_rec)
        else:
            recs_cbf = [[]]
        
        # Convert to DataFrame
        recs_cbf_df = pd.DataFrame(recs_cbf[0], columns=["movie_id"])
        recs_cbf_df = recs_cbf_df[recs_cbf_df["movie_id"] != -1]
        return recs_cbf_df


    def _get_similar_movies(self, movieIds, n_rec=20):
        seen_movie_ids = self.uf.user_seen_movies

        weights = np.exp(-np.arange(len(movieIds)))  # Exponential decay
        weights /= np.sum(weights)  # Normalize

        query_movie_details = text("""
            SELECT vector FROM latent_vectors WHERE movie_id IN :movieIds
        """)

        result = self.connection.execute(query_movie_details, {"movieIds": tuple(movieIds)}).fetchall()

        # Convert query results to a structured format
        movie_latent = [list(row) for row in result]
        if not movie_latent:
            return None

        feature_vectors = [np.array(movie) for movie in movie_latent]
        feature_vectors = np.array(feature_vectors).astype('float32')
        
        weighted_avg_vector = np.average(feature_vectors, axis=0, weights=weights).reshape(1, -1)  
        weighted_avg_vector = weighted_avg_vector.astype(np.float32)

        if seen_movie_ids:
            seen_ids_array = np.array(seen_movie_ids, dtype=np.int64)
            seen_selector = faiss.IDSelectorBatch(len(seen_movie_ids), faiss.swig_ptr(seen_ids_array))
        else:
            seen_selector = None
        
        # Perform search with exclusion of seen movies
        search_params = faiss.SearchParameters()
        if seen_selector is not None:
            search_params.sel = faiss.IDSelectorNot(seen_selector)
        
        _, similar_movie_ids = self.movie_latent_index.search(weighted_avg_vector, n_rec, params=search_params)
        
        return similar_movie_ids
    

class HybridModel:
    def __init__(self, redis_client, engine, movie_df_index, movie_latent_index, uf, popular_model):
        self.inference_cb = ContentBasedModel(redis_client, engine, movie_df_index, uf)
        self.inference_cbf = CollaborativeBasedModel(movie_latent_index, redis_client, engine, uf)
        self.popular_model = popular_model
        self.uf = uf

    def recommend(self, user_id, director = None, model = None, save = True):  
        
        content_recs = None
        director_recs = None
        collab_recs = None
        final_content = None

        # --- Step 1: Setup how many from each model
        n_content = 10 
        n_director = 5 
        n_collab = 10  

        if model == "01":
            n_content = 20
            n_collab = 0

        if model == "02":
            if director is not None:
                n_content = 5
                n_collab = 15
            else:
                n_content = 0
                n_collab = 20
        
        if model == "03":
            if director is not None:
                n_content = 5
                n_collab = 0
            else:
                n_content = 0
                n_collab = 0

        # --- Step 2: Gather collaborative-based recommendations
        if n_collab != 0:
            collab_recs = self.inference_cbf.recommend(user_id, n_rec=n_collab)

        if collab_recs is not None and isinstance(collab_recs, pd.DataFrame) and not collab_recs.empty:
            collab_recs['source'] = "02"
        else:
            collab_recs = pd.DataFrame(columns=["movie_id"])  # Empty DataFrame if no recommendations
            if model != "03":
                n_content = 20

        # --- Step 3: Gather content-based recommendations
        if director is not None:
            director_recs = self.inference_cb.recommend(
                user_id, 
                director=director,
                n_rec=n_director
            )

            if director_recs is not None and isinstance(director_recs, pd.DataFrame) and not director_recs.empty:
                director_recs['source'] = "01"
            else:
                director_recs = pd.DataFrame(columns=["movie_id"])

            actual_director_count = len(director_recs)

            content_recs = self.inference_cb.recommend(
                user_id, 
                n_rec=n_content
            )

            if content_recs is not None and isinstance(content_recs, pd.DataFrame) and not content_recs.empty:
                content_recs['source'] = "01"
            else:
                content_recs = pd.DataFrame(columns=['movie_id'])

            # Remove any overlap between the director-based and the broader content-based
            content_recs = content_recs[~content_recs['movie_id'].isin(director_recs['movie_id'])]

            # We need n_content total content-based. Some are from director-based, the rest from general content-based.
            needed_from_content = n_content - actual_director_count

            if needed_from_content < 0:
                # Trim director recs to keep only top n_content and ignore the general content-based list
                director_recs = director_recs.head(n_content)
                content_recs = pd.DataFrame(columns=director_recs.columns)
            else:
                # Take as many from the broader content-based list as needed
                content_recs = content_recs.head(needed_from_content)

            # Combine director-based first, then the broader content-based
            final_content = pd.concat([director_recs, content_recs], ignore_index=True)

        else:
            # If no director is specified, just fetch the top 10 from the general content-based
            if n_content != 0:
                final_content = self.inference_cb.recommend(
                    user_id, 
                    n_rec=n_content
                )
            
            if final_content is not None and isinstance(final_content, pd.DataFrame) and not final_content.empty:
                final_content['source'] = "01"
            else:
                final_content = pd.DataFrame(columns=['movie_id'])
        
        # If collab_recs is empty, return only content-based recommendations
        if model != "03":
            if collab_recs is None or collab_recs.empty:
                recs_h = final_content.reset_index(drop=True)
                recs_tuples = list(recs_h.itertuples(index=False, name=None))
                if save:
                    self.uf.save_recs_redis(user_id, recs_tuples)
                    self.uf.save_recs_db(user_id, recs_tuples)
                return recs_tuples

        # --- Step 4: Combine Content and Collaborative
        common_movie_ids = set(final_content['movie_id']).intersection(set(collab_recs['movie_id']))
        collab_recs = collab_recs[~collab_recs['movie_id'].isin(common_movie_ids)]
        
        # Combine (content first, then collaborative)
        combined_recs = pd.concat([final_content, collab_recs], ignore_index=True)

        total_needed = 20  # Expected total recommendations (should be 20)
        current_count = len(combined_recs)

        if current_count < total_needed:
            needed_count = total_needed - current_count
            popular_movies = self.popular_model.recommend_list()  # List of (movieId, "03")
            
            # Convert existing recommendations to a set for quick lookup
            existing_movie_ids = set(combined_recs['movie_id'])

            # Filter out already recommended movies
            additional_recs = [movie for movie in popular_movies if movie[0] not in existing_movie_ids]

            # Take only the required number of additional recommendations
            additional_recs = additional_recs[:needed_count]

            # Convert to DataFrame and append
            if additional_recs:
                additional_recs_df = pd.DataFrame(additional_recs, columns=["movie_id", "source"])
                combined_recs = pd.concat([combined_recs, additional_recs_df], ignore_index=True)

        recs_h = combined_recs.reset_index(drop=True)
        recs_tuples = list(recs_h.itertuples(index=False, name=None))

        if save:
            self.uf.save_recs_redis(user_id, recs_tuples)
            self.uf.save_recs_db(user_id, recs_tuples)

        return recs_tuples


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
    
    def get_movies_by_director(self, director):
        # Step 1: Get movie IDs by the given director
        query_movie_ids = text("""
            SELECT movie_id FROM movies WHERE director = :director
        """)

        with self.engine.connect() as connection:
            movie_ids = connection.execute(query_movie_ids, {"director": director}).fetchall()

        # Extract movie IDs from result
        movie_ids = [row[0] for row in movie_ids]

        return movie_ids
    
    def save_recs_redis(self, user_id, recs):
        timestamp = int(time.time())
        data = {
            "timestamp": timestamp,
            "recommendations": recs
        }

        key = f"user:{user_id}:recs"
        self.redis_client.set(key, json.dumps(data), ex=21600)


    def save_recs_db(self, user_id, recs):
        timestamp = datetime.fromtimestamp(int(time.time()), tz=timezone.utc)
        ttl = 86400  # 24 hours in seconds
        
        data = {
            "timestamp": timestamp,
            "recommendations": recs
        }
        
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
                "user_id": user_id,
                "recommendations": json.dumps(recs),
                "timestamp": timestamp
            })
            connection.commit()
        

    
class RecGenerator:
    def __init__(self):
        db_url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        self.redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        self.engine = create_engine(db_url)
        self.data_ingestion = DataIngestion(self.engine, self.redis_client)
        self.uf = UtilityFunctions(self.redis_client, self.engine)
        self.popular_model = None
        self.is_locked = False 


    def build_pipeline(self):
        print("Downloading and loading data...")
        movie_latent_index, movie_df_index, self.users = self.data_ingestion.fetch_weights()
        self.popular_model = PopularityBasedModel(self.redis_client, self.uf)
        self.hybrid = HybridModel(self.redis_client, self.engine, movie_df_index, movie_latent_index, self.uf, self.popular_model)
        
        print("Inference Pipline Ready!")
           
    def make_recs(self, user_id, director = None, model = None, save = True):
        seen_movies = self.uf.get_seen_movies_from_redis(user_id)
        
        if seen_movies:
            recs_list = self.hybrid.recommend(user_id, director, model, save)
            recs = {"timestamp": int(time.time()), "recommendations": recs_list}
        else :
            recs = {"timestamp": int(time.time()), "recommendations": []}
        return recs

    def recommend_for_all(self):
        for u in self.users['user_id'].to_list():
            self.uf.get_seen_movies_from_redis(u)
            self.make_recs(u)
    
    def deploy_update_check(self):
        print("Node listening for Updates!")
        while True:
            version = self.redis_client.get("version")
            if version is not None and model_version != version:
                self.is_locked = True
                print("Node Updating...")
                # Call your update logic here
                self.build_pipeline()
                print("Node update complete.")
                self.redis_client.publish("nodes_version", f"Node is now version {version}")
                self.is_locked = False
            # Wait for 30 seconds before checking again
            time.sleep(30)
    
    def start_deploy_thread(self):
        deploy_thread = threading.Thread(target=self.deploy_update_check, daemon=True)
        # Start the thread
        deploy_thread.start()


