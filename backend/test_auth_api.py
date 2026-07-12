import requests

def test_auth_endpoint():
    print("Testing /api/auth/login endpoint...")
    url = "http://127.0.0.1:8999/api/auth/login"
    try:
        # We don't need valid credentials just to check connectivity and CORS/Response types
        # OAuth2PasswordRequestForm expects data as form-data
        data = {"username": "test@example.com", "password": "password"}
        response = requests.post(url, data=data, timeout=5)
        print(f"Status Code: {response.status_code}")
        print(f"Response Body: {response.json()}")
        
        if response.status_code in [200, 401]:
            print("SUCCESS: Endpoint is reachable and responding correctly.")
        else:
            print(f"Unexpected status code: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("ERROR: Connection refused. Is the backend running on port 8999?")
    except Exception as e:
        print(f"ERROR: An unexpected error occurred: {e}")

if __name__ == "__main__":
    test_auth_endpoint()
