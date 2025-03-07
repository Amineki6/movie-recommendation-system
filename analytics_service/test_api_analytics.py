import requests

BASE_URL = "http://127.0.0.1:3040"

# Test /user/history endpoint
def test_user_history():
    endpoint = f"{BASE_URL}/user/history"
    payload = {
        "user_id": "22"  # Replace with a valid user_id if required
    }
    try:
        response = requests.post(endpoint, json=payload)
        print("/user/history Response:")
        print(response.status_code)
        print(response.json())
    except Exception as e:
        print(f"Error testing /user/history: {e}")

# Test /user/preferences endpoint
def test_user_preferences():
    endpoint = f"{BASE_URL}/user/preferences"
    payload = {
        "user_id": "22"  # Replace with a valid user_id if required
    }
    try:
        response = requests.post(endpoint, json=payload)
        print("/user/preferences Response:")
        print(response.status_code)
        print(response.json())
    except Exception as e:
        print(f"Error testing /user/preferences: {e}")

if __name__ == "__main__":
    print("Testing API endpoints...")
    test_user_history()
    test_user_preferences()
