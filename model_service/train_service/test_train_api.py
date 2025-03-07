import requests

# Define the URL and the payload
url = "http://localhost:7070/train"
payload = {"train_cb": True, "train_cbf": True, "online": False}


# Send POST request
response = requests.post(url, json=payload)

# Print response
if response.status_code == 200:
    print("Training:", response.json())
else:
    print("Error:", response.status_code, response.json())
