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

    def __init__(self, rules_path: str):
        self.rules_path = rules_path
        self.schemes = self.load_rules()

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
        return value

    def evaluate_rule(self, farmer_value, operator, rule_value) -> bool:
        """
        Evaluate a single rule condition.
        """

        farmer_value = self.normalize(farmer_value)
        rule_value = self.normalize(rule_value)

        op_func = self.operators.get(operator)

        if not op_func:
            print(f"Unsupported operator: {operator}")
            return False

        try:
            return op_func(farmer_value, rule_value)
        except Exception:
            return False

    def check_scheme(self, scheme: Dict, farmer_profile: Dict) -> Dict:
        """
        Check if farmer satisfies all scheme rules, returning detailed pass/fail info.
        """
        rules = scheme.get("rules", [])
        passed_rules = []
        failed_rules = []

        for rule in rules:
            field = rule.get("field")
            operator = rule.get("operator")
            value = rule.get("value")

            farmer_value = farmer_profile.get(field)
            
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

        is_eligible = len(failed_rules) == 0

        return {
            "is_eligible": is_eligible,
            "passed_rules": passed_rules,
            "failed_rules": failed_rules
        }

    def filter_schemes(self, farmer_profile: Dict) -> Dict[str, List[Dict]]:
        """
        Categorizes all schemes into eligible and ineligible lists with reasons.
        """
        eligible_schemes = []
        ineligible_schemes = []

        for scheme in self.schemes:
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