"""
Rule Engine for scheme eligibility filtering.

Evaluates farmer profiles against scheme rules defined in YAML.
"""

import yaml
from typing import List, Dict, Any


class RulesEngine:
    """
    Rule-based engine that filters schemes based on eligibility conditions.
    """

    def __init__(self, rules_path: str = None, schemes: List[Dict] = None):
        self.rules_path = rules_path
        self.schemes = schemes if schemes is not None else self.load_rules()

        # Supported operators
        self.operators = {
            "==": lambda a, b: a == b,
            "!=": lambda a, b: a != b,
            "<": lambda a, b: float(a) < float(b),
            "<=": lambda a, b: float(a) <= float(b),
            ">": lambda a, b: float(a) > float(b),
            ">=": lambda a, b: float(a) >= float(b),
            "in": lambda a, b: a in b if isinstance(b, list) else False,
            "not_in": lambda a, b: a not in b if isinstance(b, list) else False,
        }

    def load_rules(self) -> List[Dict]:
        """
        Load scheme rules from YAML file.
        """
        if not self.rules_path:
            return []
        try:
            with open(self.rules_path, "r", encoding="utf-8") as file:
                data = yaml.safe_load(file)
                return data.get("schemes", [])
        except Exception as e:
            print(f"Error loading rules: {e}")
            return []

    def normalize(self, value):
        """
        Normalize values for comparison.
        """
        if isinstance(value, str):
            return value.strip().lower()
        if isinstance(value, list):
            return [self.normalize(v) for v in value]
        return value

    def evaluate_rule(self, farmer_value, operator, rule_value) -> bool:
        """
        Evaluate a single rule condition.
        """
        farmer_val_norm = self.normalize(farmer_value)
        rule_val_norm = self.normalize(rule_value)

        # Handle list farmer_value (e.g. primary_crops) against string or list rule_value
        if isinstance(farmer_val_norm, list) and operator == "in":
            if isinstance(rule_val_norm, list):
                return any(item in rule_val_norm for item in farmer_val_norm)
            return rule_val_norm in farmer_val_norm

        op_func = self.operators.get(operator)

        if not op_func:
            print(f"Unsupported operator: {operator}")
            return False

        try:
            return op_func(farmer_val_norm, rule_val_norm)
        except Exception:
            return False

    def check_scheme(self, scheme: Dict, farmer_profile: Dict) -> Dict:
        """
        Check if farmer satisfies all scheme rules, returning detailed pass/fail info.
        Excludes schemes without structured rules or status != 'published'.
        """
        # Deepcopy rules to avoid mutating DB cache
        import copy
        rules = copy.deepcopy(scheme.get("rules", []))

        status = scheme.get("status", "published")

        # Exclude schemes that have no structured rules or are not published
        if not rules or status != "published":
            return {
                "is_eligible": False,
                "passed_rules": [],
                "failed_rules": [{
                    "field": "rules",
                    "operator": "exists",
                    "value": True,
                    "farmer_value": None,
                    "reason": "Scheme status is not published or has no structured rules"
                }]
            }

        passed_rules = []
        failed_rules = []

        for rule in rules:
            field = rule.get("field")
            operator = rule.get("operator")
            value = rule.get("value")

            farmer_value = farmer_profile.get(field)
            if farmer_value is None:
                if field == "income":
                    farmer_value = farmer_profile.get("annual_income")
                elif field == "land_size":
                    farmer_value = farmer_profile.get("land_size_hectares")
                elif field == "crop":
                    farmer_value = farmer_profile.get("primary_crops")
                elif field == "occupation_type":
                    farmer_value = farmer_profile.get("occupation", "farmer")
                elif field == "is_differently_abled":
                    farmer_value = farmer_profile.get("is_disabled", False)
                elif field == "gender":
                    farmer_value = farmer_profile.get("gender")
                elif field == "category":
                    farmer_value = farmer_profile.get("category")
                else:
                    # Log unrecognized fields falling through
                    print(f"Warning: Scheme rule field '{field}' not found in profile.")
            
            # Keep a record of what we evaluated
            rule_record = {
                "field": field,
                "operator": operator,
                "value": value,
                "farmer_value": farmer_value
            }

            # If profile does not contain the required field
            if farmer_value is None:
                failed_rules.append(rule_record)
                continue

            if not self.evaluate_rule(farmer_value, operator, value):
                failed_rules.append(rule_record)
            else:
                passed_rules.append(rule_record)

        # Strict AND logic: must pass every rule in the array, and no single rule failed
        is_eligible = (len(failed_rules) == 0) and (len(passed_rules) == len(rules))

        return {
            "is_eligible": is_eligible,
            "passed_rules": passed_rules,
            "failed_rules": failed_rules
        }

    def filter_schemes(self, farmer_profile: Dict, schemes: List[Dict] = None) -> Dict[str, List[Dict]]:
        """
        Categorizes all schemes into eligible and ineligible lists with reasons.
        """
        target_schemes = schemes if schemes is not None else self.schemes
        eligible_schemes = []
        ineligible_schemes = []

        for scheme in target_schemes:
            result = self.check_scheme(scheme, farmer_profile)
            
            # Create a rich scheme object containing the evaluation results
            rich_scheme = dict(scheme)
            rich_scheme["passed_rules"] = result["passed_rules"]
            rich_scheme["failed_rules"] = result["failed_rules"]
            
            if result["is_eligible"]:
                eligible_schemes.append(rich_scheme)
            else:
                ineligible_schemes.append(rich_scheme)

        return {
            "eligible": eligible_schemes,
            "ineligible": ineligible_schemes
        }