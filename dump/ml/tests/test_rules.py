from pathlib import Path
from app.ml.rules.rules_engine import RulesEngine

BASE_DIR = Path(__file__).resolve().parent

RULES_PATH = BASE_DIR / "rules" / "schemes_rules.yaml"

engine = RulesEngine(RULES_PATH)

farmer = {
    "income": 120000,
    "land_size": 1.5,
    "farmer_type": "small",
    "irrigation": "no",
    "crop": "cotton"
}

eligible = engine.filter_schemes(farmer)

print("Eligible schemes:")

for scheme in eligible:
    print(f"{scheme['scheme_id']} - {scheme['name']}")