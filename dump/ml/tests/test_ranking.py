from app.ml.inference.ranking_engine import SchemeRankingEngine


engine = SchemeRankingEngine()

farmer_profile = {
    "income": 100000,
    "land_size": 1.5,
    "state": "maharashtra",
    "crop": "cotton",
    "irrigation": "no",
    "farmer_type": "small"
}

results = engine.rank_schemes(farmer_profile)

print("\nRecommended schemes:\n")

for r in results:
    print(f"{r['scheme_id']} | {r['scheme_name']} | Probability: {r['success_probability']:.2f}")