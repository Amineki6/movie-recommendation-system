from locust import HttpUser, task, between
import random

class UISimulation(HttpUser):
    wait_time = between(1, 3)
    user_ids = list(range(1, 101))  # List of user IDs from 1 to 100
    
    # Dummy host to satisfy Locust's requirement (not actually used)
    host = "http://localhost"

    @task
    def simulate_api_calls(self):
        # Randomly select a user_id
        user_id = random.choice(self.user_ids)

        # Make the /fetch request
        fetch_response = self.client.post(
            "http://127.0.0.1:6062/fetch", 
            json={"user_id": user_id}, 
            name="/fetch"
        )
        if fetch_response.status_code != 200:
            print(f"Fetch Request failed: {fetch_response.status_code} - {fetch_response.text}")
        # else:
        #     # Make the /recommend request with the user_id in the request body
        #     recommend_response = self.client.post(
        #         "http://localhost:8080/recommend", 
        #         json={"user_id": user_id, "director": None, "model": None},  # Send user_id as JSON body
        #         name="/recommend"
        #     )
        #     if recommend_response.status_code != 200:
        #         print(f"Recommend Request failed: {recommend_response.status_code} - {recommend_response.text}")
