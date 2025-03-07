import requests

# Define the URL and the payload
url = "http://127.0.0.1:6090/feedback"
payload = {
    "user_id": 611,
    "movie_id": 3301,
    "rating": 5,
    "source": "02"
}

# Send POST request
response = requests.post(url, json=payload)

# Print response
if response.status_code == 200:
    print("Success:", response.json())
else:
    print("Error:", response.status_code, response.json())
