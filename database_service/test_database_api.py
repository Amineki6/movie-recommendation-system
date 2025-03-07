import requests

if True:
    # Define the URL and the payload for adding a movie
    url = "http://127.0.0.1:3303/add_movie"
    payload = {
        "title": "Back in Action (2025)",
        "genres": "Action|Comedy",
        "imdbId": 999999,
        "tmdbId": 993710,
        "most_popular_cast": "Jamie Foxx",
        "director": "Seth Gordon",
        "original_language": "en",
        "overview": "Fifteen years after vanishing from the CIA to start a family, elite spies Matt and Emily jump back into the world of espionage when their cover is blown.",
        "popularity": 28.184,
        "release_date": "2025-01-17",
        "poster_path": "/mLxIlIf2Gopht23v5VFNpQZ2Rue.jpg",
        "vote_average": 7.6
    }

    # Send POST request
    response = requests.post(url, json=payload)

    # Print response
    if response.status_code == 201:
        print("Movie Added:", response.json())
    else:
        print("Error:", response.status_code, response.json())

if False:
    # Define the URL and the payload
    url = "http://127.0.0.1:5000/add_user"
    payload = {
        "firstname": "Amine",
        "lastname": "Kina",
        "email": "amine.kina99@gmail.com",
        "plain_password": "SuperSecurePassword123!"
    }


    # Send POST request
    response = requests.post(url, json=payload)

    # Print response
    if response.status_code == 200:
        print("User Added")
    else:
        print("Error:", response.status_code, response.json())


if False:
    # Define the URL with the user_id to delete
    user_id_to_delete = 200940  # Replace with the actual user ID to test
    url = f"http://127.0.0.1:5000/delete_user/{user_id_to_delete}"

    # Send DELETE request
    response = requests.delete(url)

    # Print response
    if response.status_code == 200:
        response_data = response.json()
        if response_data.get("success"):
            print(f"User {user_id_to_delete} deleted successfully.")
        else:
            print(f"Failed to delete user {user_id_to_delete}. User might not exist or is already deleted.")
    else:
        print("Error:", response.status_code, response.json())