import requests

BASE_URL = "http://127.0.0.1:8999"

def test_recommendations():
    print("\n--- Testing Recommendations ---")
    farmer_data = {
        "full_name": "Test Farmer",
        "email": "test@example.com",
        "farmer_type": "Small",
        "land_size_hectares": 1.5,
        "annual_income": 100000,
        "irrigation_type": "Rainfed",
        "state": "Maharashtra",
        "district": "Pune"
    }
    
    response = requests.post(f"{BASE_URL}/api/farmers/", json=farmer_data)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 201:
        data = response.json()
        print(f"Farmer ID: {data.get('_id')}")
        rec = data.get("recommended_schemes", [])
        print(f"Recommendations count: {len(rec)}")
        for s in rec[:2]:
            print(f"- {s['scheme_name']} ({s['success_probability']})")
    else:
        print(f"Error: {response.text}")

if __name__ == "__main__":
    try:
        test_recommendations()
    except Exception as e:
        print(f"Request failed: {e}")
