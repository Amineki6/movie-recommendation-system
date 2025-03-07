import requests
import os
import redis
import random
import json


REDIS_HOST = os.getenv('REDIS_HOST', '127.0.0.1')
REDIS_PORT = os.getenv('REDIS_PORT', '6379')

class UserInterface:
    def __init__(self, db, movie_model):
        self.db = db
        self.Movie = movie_model
        self.redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

    def normalize_rating(self, vote_average):
        if vote_average is None:
            return None
        normalized = round((vote_average / 2) * 2) / 2  # Round to the nearest 0.5
        return max(0, min(5, normalized))

    def get_movies_posters(self, request):
        movie_ids = request.args.getlist('movie_id')  # Retrieve movie IDs from query parameters
        include_all = request.args.get('include_all', 'false').lower() == 'true'

        # Conditionally construct the query based on include_all
        query = self.Movie.query.filter(self.Movie.movie_id.in_(map(int, movie_ids)))

        if not include_all:
            query = query.with_entities(
                self.Movie.movie_id, self.Movie.title, self.Movie.poster_path
            )

        movies = query.all()

        # Return raw data (not JSON) to be processed in app.py
        return [
            {
                "movie_id": movie.movie_id,
                "title": movie.title,
                "poster_url": movie.poster_path,
                **({"rating": self.normalize_rating(movie.vote_average)} if include_all else {}),
                **({"director": movie.director} if include_all else {}),
                **({"genres": movie.genres} if include_all else {}),
                **({"overview": movie.overview} if include_all else {})
            }
            for movie in movies
        ]

    def get_new_release(self):
        movies_data = self.redis_client.get("recent_movies")

        if movies_data is None:
            # Query the database for the newest movies
            newest_movies = self.Movie.query.filter(
                self.Movie.release_date.isnot(None)
            ).order_by(self.Movie.release_date.desc()).all()

        newest_movies = json.loads(movies_data)
        first_file_path = None  
        movie_title = None
        movie_overview = None
        random.shuffle(newest_movies)
    
        # Iterate over movies and fetch images
        for movie in newest_movies:
            movie_tmdbid = int(movie['tmdbid'])
            api_url = f"https://api.themoviedb.org/3/movie/{movie_tmdbid}/images"
            headers = {"Authorization": f"Bearer eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiIzYmM1OTZiNzIxZGM2YjE3YWQwYjZlZjg3NjVhZmE1ZiIsIm5iZiI6MTczMjYzNzE2OS43ODMsInN1YiI6IjY3NDVmMWYxNmVlZjViNDNhNWZjYThjOCIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.5Bxuzx7Mgp_H8Q6x9vuv1Um8rcnd6b9hI3XSuSMnzuE"} 
            response = requests.get(api_url, headers=headers)

            if response.status_code == 200:
                backdrops = response.json().get('backdrops', [])
                if backdrops:
                    first_file_path = backdrops[0].get('file_path')
                    movie_title = movie['title']
                    movie_overview = movie['overview']
                    movie_vote_average = movie['vote_average']
                    movie_director = movie['director']
                    movie_id = movie['movie_id']
                    break  # Stop after finding the first valid image

        return {
            "movie_id": movie_id,
            "title": movie_title,
            "overview": movie_overview,
            "image_path": first_file_path,
            "director": movie_director ,
            "vote_average": self.normalize_rating(movie['vote_average'])
        }



