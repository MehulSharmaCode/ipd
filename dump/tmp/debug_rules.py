import sys
import os
import yaml

# Add backend to path
sys.path.append(os.path.abspath('c:/Users/Paresh/foler/agri-sense/backend'))

from app.ml.inference.ranking_engine import SchemeRankingEngine
from app.ml.rules.rules_engine import RulesEngine
from pathlib import Path

def debug_rules():
    engine = SchemeRankingEngine()
    
    # Generic profile that should match multiple schemes
    farmer_profile = {
        "full_name": "Paresh",
        "email": "paresh@example.com",
        "annual_income": 80000,
        "land_size_hectares": 1.2,
        "farmer_type": "Small",
        "irrigation_type": "Rainfed",
        "primary_crops": ["Rice", "Wheat"],
        "state": "Maharashtra"
    }
    
    # Manually check rules to see WHY they fail
    RULES_PATH = Path('c:/Users/Paresh/foler/agri-sense/backend/app/ml/rules/schemes_rules.yaml')
    rules_engine = RulesEngine(str(RULES_PATH))
    
    features = engine.feature_store.build_features(farmer_profile)
    print(f"Cleaned Features: {features}\n")
    
    for scheme in rules_engine.schemes:
        scheme_id = scheme['scheme_id']
        is_eligible = True
        print(f"Checking Scheme: {scheme_id}")
        
        for rule in scheme.get('rules', []):
            field = rule.get('field')
            op = rule.get('operator')
            val = rule.get('value')
            f_val = features.get(field)
            
            res = rules_engine.evaluate_rule(f_val, op, val)
            print(f"  Rule: {field} {op} {val} | Farmer: {f_val} | Result: {res}")
            if not res:
                is_eligible = False
                break
        
        print(f"  FINAL ELIGIBILITY: {is_eligible}\n")

if __name__ == "__main__":
    debug_rules()
