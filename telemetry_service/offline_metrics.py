import pandas as pd  
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import redis
import json
import faiss
from tqdm import tqdm
import pandas as pd
import random
from sqlalchemy import create_engine
from sqlalchemy import text 
from cbf import TrainCBF


class DataIngestion:
    def __init__(self, db_url):
        db_url = db_url
        self.engine = create_engine(db_url)

    def fetch_weights(self, relevant_threshold, min_relevant):
        ratings_df_query = "SELECT * FROM public.ratings_df"
        ratings_df = pd.read_sql(ratings_df_query, self.engine)

        train_data, test_data = self.split_train_test(ratings_df, relevant_threshold, min_relevant)

        movies_df_query = "SELECT * FROM public.movie_df"
        movie_df = pd.read_sql(movies_df_query, self.engine)

        movie_df_subset, movie_ids_to_keep = self.get_test_movies(movie_df, test_data)
        movie_df_index = self.get_index(movie_df_subset)

        ratings_df_query = "SELECT * FROM public.ratings_df"
        ratings_df = pd.read_sql(ratings_df_query, self.engine)


        return train_data , test_data, movie_df_index, movie_df, movie_ids_to_keep

    def split_train_test(self, ratings_df, relevant_threshold, min_relevant):
        train_data = []
        test_data = []

        print("Splitting data...")

        for user, user_df in ratings_df.groupby("user_id"):
            # Filter ratings >= relevant_threshold
            high_ratings = user_df[user_df["rating"] >= relevant_threshold]
            
            # Sort by timestamp
            high_ratings = high_ratings.sort_values(by="timestamp")
            
            # If the user has enough high ratings, split them
            if len(high_ratings) >= min_relevant:  # Ensure at least min_relevant ratings before splitting
                test_size = max(1, int(0.2 * len(high_ratings)))  # At least 1 row in test if possible
                test_rows = high_ratings.iloc[-test_size:]  # Take last 20%
                train_rows = user_df.drop(test_rows.index)  # Rest in train
            else:
                train_rows = user_df  # All rows in train if not enough high ratings
                test_rows = pd.DataFrame(columns=ratings_df.columns)  # Empty test set
            
            train_data.append(train_rows)
            test_data.append(test_rows)
        
        # Filter out empty dataframes before concatenation to avoid the FutureWarning
        train_data_nonempty = [df for df in train_data if not df.empty]
        test_data_nonempty  = [df for df in test_data  if not df.empty]

        # Concatenate results; if all are empty, produce an empty dataframe with the same columns
        if train_data_nonempty:
            train_df = pd.concat(train_data_nonempty, ignore_index=True)
        else:
            train_df = pd.DataFrame(columns=ratings_df.columns)

        if test_data_nonempty:
            test_df = pd.concat(test_data_nonempty, ignore_index=True)
        else:
            test_df = pd.DataFrame(columns=ratings_df.columns)

        return train_df, test_df


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
    
    def get_test_movies(self, movie_df, test_data):
        print("Building test set of movies...")

        movie_ids_to_keep = test_data['movie_id'].unique().tolist()
        test_movies = movie_df[movie_df['movie_id'].isin(movie_ids_to_keep)]
        return test_movies, movie_ids_to_keep

class Model:
    def __init__(self, utitlity_functions, movie_df, movie_df_index, train_data, popular_model, test_data, movie_ids_to_keep):
        self.movie_df = movie_df
        self.train_data = train_data
        self.movie_ids_to_keep = movie_ids_to_keep
        self.df_user = None
        self.movie_df_index = movie_df_index
        self.popular_model = popular_model
        self.utitlity_functions = utitlity_functions
        self.test_data = test_data

    def train(self, cb = False, cbf = False):
        if cb:
            print("Training Content Based Model...")
            # Step 1: Merge train_data with movie_df on movie_id
            merged_df = self.train_data.merge(self.movie_df, left_on='movie_id', right_on='movie_id')

            merged_df['adjusted_rating'] =   np.log(merged_df['rating'])
            # Step 2: Multiply features by the rating
            merged_df['vector'] = merged_df.apply(
                lambda row: np.array(row['vector']) * row['adjusted_rating'], axis=1
            )

            # Step 3: Group by user_id and sum across features
            user_features = merged_df.groupby('user_id')['vector'].sum().reset_index()
            self.df_user = user_features

            self.df_user["vector"] = self.df_user["vector"].apply(lambda row: row.tolist())
        
        if cbf:
            pipeline = TrainCBF.TrainPipelineCBF()
            pipeline.build_pipeline(train_data=self.train_data)
            self.movie_latent_index , self.dict_latent, self.last_liked_list = pipeline.train(self.movie_ids_to_keep)

    def recommend(self, user_id, cb, cbf, pb, rd):
        if cb:
            recs = self.recommend_cb(user_id)
        if cbf:
            recs = self.recommend_cbf(user_id)
        if pb:
            recs = self.popular_model.recommend(user_id)
        if rd:
            recs = self.recommend_random()
        return recs

    def recommend_cb(self, user_id, n_rec=20):
        # Get user vector and seen movie IDs
        seen_movie_ids = self.utitlity_functions.get_seen_movies_from_train_data(user_id)
        user_vector = np.array(self.df_user.loc[self.df_user.user_id == user_id, 'vector'].values[0], dtype=np.float32).reshape(1, -1)

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
    
        _, recs_cb = self.movie_df_index.search(user_vector, n_rec, params=search_params)

        recs_cb_df = pd.DataFrame(recs_cb[0], columns=["movie_id"])
        recs_cb_df = recs_cb_df[recs_cb_df["movie_id"] != -1]
        recs_cb_df = recs_cb_df.reset_index(drop=True)

        recs_list = recs_cb_df.values
        flat_list = [int(item[0]) for item in recs_list]

        return flat_list
    
    def recommend_random(self):
        ids = self.test_data['movie_id'].unique().tolist()
        return random.sample(ids, 20)
    
    def recommend_cbf(self, userId, n_rec=20):

        last_liked = self.last_liked_list.get(userId, None)
        
        if last_liked is not None:
            recs_cbf = self._get_similar_movies(last_liked, userId, n_rec)
        else:
            recs_cbf = []
        
        return recs_cbf


    def _get_similar_movies(self, movieIds,userId, n_rec=20):
        seen_movie_ids = self.utitlity_functions.get_seen_movies_from_train_data(userId)

        weights = np.exp(-np.arange(len(movieIds)))  # Exponential decay
        weights /= np.sum(weights)  # Normalize

        movie_latent = [self.dict_latent[key] for key in movieIds if key in self.dict_latent]
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
        flat_similar_movie_ids = [item for sublist in similar_movie_ids for item in sublist]
        return flat_similar_movie_ids

class PopularityBasedModel:
    def __init__(self, redis_client, utility_functions):
        self.redis_client = redis_client
        self.utility_functions = utility_functions
        self.popular_movies = None
        self.fetch_movies()

    def fetch_movies(self):
        popular_movies_key = 'popular_movies:03'
        popular_movies_json = self.redis_client.get(popular_movies_key)
        if popular_movies_json:
            popular_movies_json_load = json.loads(popular_movies_json)
            self.popular_movies = [movie['movie_id'] for movie in popular_movies_json_load]
            print("Popular Model Ready!")
        else:
            self.popular_movies = []
    
    def recommend(self, user_id):  
        seen_movies = set(self.utility_functions.get_seen_movies_from_train_data(user_id))
        recs_list = [tup for tup in self.popular_movies if tup not in seen_movies]
        random.shuffle(recs_list)
        return recs_list

class UtilityFunctions:
    def __init__(self, redis_client, train_data):
        self.redis_client = redis_client
        self.user_seen_movies = None
        self.train_data = train_data

    def get_seen_movies_from_train_data(self, user_id):
        user_movies = self.train_data.loc[self.train_data['user_id'] == user_id, 'movie_id']
        return user_movies.tolist()

class Metrics:
    def __init__(self, model, test_data):
        self.model = model
        self.test_data = test_data

    def precision(self, cb=False, cbf=False, pb=False, rd=False, k=10):
        if cb:
            print("Evaluating Content Based Model")
        if cbf:
            print("Evaluating Collaborative Based Model")
        if pb:
            print("Evaluating Popular Model")
        if rd:
            print("Evaluating Random")

        users = self.model.train_data['user_id'].unique().tolist()
        test_data = self.test_data

        def compute_user_precision(user_id): 
            recommended_movies = self.model.recommend(user_id, cb, cbf, pb, rd)[:k]
            user_test_data = test_data[test_data['user_id'] == user_id]
            relevant_movie_ids = set(user_test_data['movie_id'].tolist())
            relevant_recommendations = len(
                [movie for movie in recommended_movies if movie in relevant_movie_ids]
            )
            return relevant_recommendations / k

        results = []
        for user_id in tqdm(users, desc="Computing Precision"):
            precision = compute_user_precision(user_id)
            results.append(precision)

        # Filter None results
        valid_results = [r for r in results if r is not None]

        # Compute the average precision
        average_precision = sum(valid_results) / len(valid_results) if valid_results else 0.0

        print(f"Average Precision@{k}: {average_precision:.8f}")
        return average_precision
    

    def recall(self, cb=False, cbf=False, pb=False, rd=False, k=10):
        if cb:
            print("Evaluating Content Based Model")
        if cbf:
            print("Evaluating Collaborative Based Model")
        if pb:
            print("Evaluating Popular Model")
        if rd:
            print("Evaluating Random")

        total_recall = 0
        user_count = 0
        
        # Get the list of unique users
        users = self.model.train_data['user_id'].unique().tolist()
        
        # Wrap the users list with tqdm to add a progress bar
        for user_id in tqdm(users, desc="Computing Recall"):
            if len(self.model.utitlity_functions.get_seen_movies_from_train_data(user_id)) > 20:
                # Get the recommended list of movie IDs for the user
                recommended_movies = self.model.recommend(user_id, cb, cbf, pb, rd)[:k]  # Only consider top-K recommendations

                # Get the user's test data
                user_test_data = self.test_data[self.test_data['user_id'] == user_id]
                relevant_movies = user_test_data[user_test_data['rating'] >= 4]  # Movies the user liked

                # Filter relevant movie IDs
                relevant_movie_ids = set(relevant_movies['movie_id'].to_list())

                # Compute Recall@K
                relevant_recommendations = len([
                    movie for movie in recommended_movies 
                    if movie in relevant_movie_ids
                ])
                recall = (relevant_recommendations / len(relevant_movie_ids)
                        if len(relevant_movie_ids) > 0 else 0)

                # Update the total recall and user count
                total_recall += recall
                user_count += 1

        # Calculate the average recall across all users
        average_recall = (total_recall / user_count) if user_count > 0 else 0
        print(f"Average Recall@{k}: {average_recall:.8f}")
        
        return average_recall

class InferencePipeline:
    def __init__(self):
        self.redis_client = redis.StrictRedis(host='127.0.0.1', port=6379, decode_responses=True)
        db_url = "postgresql://postgres:postgre123@postgresinstance.cpyqmeeock79.eu-north-1.rds.amazonaws.com:5432/postgresdb"
        self.data_ingestion = DataIngestion(db_url)
        

    def build_pipeline(self, relevant_threshold, min_relevant):
        print("Downloading and loading data...")
        self.train_data , self.test_data, self.movie_df_index, self.movie_df, self.movie_ids_to_keep = self.data_ingestion.fetch_weights(relevant_threshold, min_relevant)
        self.utility_functions = UtilityFunctions(self.redis_client, self.train_data)
        self.popular_model = PopularityBasedModel(self.redis_client, self.utility_functions)
        self.model = Model(self.utility_functions, self.movie_df, self.movie_df_index, self.train_data, self.popular_model, self.test_data, self.movie_ids_to_keep)
        self.metric = Metrics(self.model, self.test_data)
        print("Inference Pipline Ready!")

    def train(self, cb=False, cbf=False):
        self.model.train(cb=cb, cbf=cbf)
        print("Model Trained!")

    

def main():
    pipeline = InferencePipeline()

    # Design dependent variables
    relevant_threshold = 4 # minimum rating for a movie to be considered relevant
    min_relevant = 5 # minimum number of relevant movies per user

    pipeline.build_pipeline(relevant_threshold, min_relevant)
    pipeline.train(cb=True, cbf=True)

    params = ['cb', 'cbf', 'pb', 'rd']

    # Loop through each parameter value
    for param in params:
        # Create a dictionary with all parameters set to False
        kwargs = {'cb': False, 'cbf': False, 'pb': False, 'rd': False}
        
        # Set the current parameter to True
        kwargs[param] = True
        
        # Call precision and recall with the current parameter set to True
        pipeline.metric.precision(k=10, **kwargs)
        pipeline.metric.recall(k=10, **kwargs)


main()