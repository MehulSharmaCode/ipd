import sys
import os

# Add backend to path
sys.path.append(os.path.abspath('c:/Users/Paresh/foler/agri-sense/backend'))

from app.ml.services.recommendation_service import RecommendationService

def test_service():
    # Simulate a profile
    farmer_profile = {
        "full_name": "Test",
        "email": "test@test.com",
        "annual_income": 80000,
        "land_size_hectares": 1.2,
        "farmer_type": "Small",
        "irrigation_type": "Rainfed",
        "primary_crops": ["Rice"],
        "state": "Maharashtra"
    }
    
    print(f"Calling service with: {farmer_profile['annual_income']}, {farmer_profile['land_size_hectares']}")
    recs = RecommendationService.get_recommendations(farmer_profile)
    print(f"\nFound {len(recs)} schemes:")
    for r in recs:
        print(f"- {r['scheme_id']}: {r['scheme_name']} (Prob: {r.get('success_probability')})")

if __name__ == "__main__":
    test_service()
