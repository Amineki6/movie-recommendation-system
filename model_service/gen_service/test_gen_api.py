import requests

# Define the URL and the payload
url = "http://127.0.0.1:6060/generate"
payload = {"user_id": 611}


# Send POST request
response = requests.post(url, json=payload)

# Print response
if response.status_code == 200:
    print("Recommendations:", response.json())
else:
    print("Error:", response.status_code, response.json())
