from app.ml.inference.ranking_engine import SchemeRankingEngine

engine = SchemeRankingEngine()

farmer = {
    "farmer_type": "small",
    "land_size": 1.5,
    "income": 100000,
    "irrigation": "rainfed",
    "state": "maharashtra",
    "district": "pune",
    "age": 30,
    "gender": "male",
    "category": "obc"
}

results_dict = engine.rank_schemes(farmer)
ranked_schemes = results_dict["ranked_schemes"]

print("\n===== AI Recommendation Results =====\n")

for scheme in ranked_schemes:
    print(f"Scheme: {scheme['scheme_id']}")
    print(f"Name: {scheme['scheme_name']}")
    print(f"Success Probability: {round(scheme['success_probability'], 3)}")
    print("-----------------------------------")