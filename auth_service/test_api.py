import requests

if True:
    # Define the URL and payload
    url = "http://127.0.0.1:3300/authenticate"
    payload = {
        "email": "amine.kina77@gmail.com",
        "password": "SuperSecurePassword123!"
    }

    # Send POST request
    response = requests.post(url, json=payload)

    # Print response
    if response.status_code == 200:
        response_data = response.json()
        if response_data.get("authenticated"):
            print("Authentication successful!")
        else:
            print("Authentication failed. Invalid credentials.")
    else:
        print("Error:", response.status_code, response.json())
