class SchemeExplainer:
    """
    Generates dynamic explanations for scheme recommendations based on passed/failed rules.
    """

    @staticmethod
    def _translate_rule(rule_dict: dict, is_failed: bool = False) -> str:
        """
        Translates a single YAML rule dict into a human readable reason.
        """
        field = rule_dict.get("field", "")
        operator = rule_dict.get("operator", "")
        value = rule_dict.get("value", "")
        farmer_value = rule_dict.get("farmer_value", "Unknown")

        # Make fields pretty
        field_names = {
            "income": "Annual Income",
            "land_size": "Land Size (Hectares)",
            "farmer_type": "Farmer Category",
            "crop": "Crop Type",
            "irrigation": "Irrigation Status"
        }
        pretty_field = field_names.get(field, field.replace("_", " ").title())

        # Handle list values (like 'in' operator)
        if isinstance(value, list):
            value_str = ", ".join(str(v).title() for v in value)
        else:
            value_str = str(value).title() if isinstance(value, str) else str(value)
            
        if field == "income":
            value_str = f"₹{value:,}" if isinstance(value, (int, float)) else value_str

        # Generate the sentence
        if is_failed:
            if operator == "==":
                return f"Requires {pretty_field} to be {value_str} (Yours is {str(farmer_value).title()})."
            elif operator == "in":
                return f"Requires {pretty_field} to be one of: {value_str} (Yours is {str(farmer_value).title()})."
            elif operator in ["<", "<="]:
                return f"Requires {pretty_field} to be under {value_str} (Yours is {farmer_value})."
            elif operator in [">", ">="]:
                return f"Requires {pretty_field} to be over {value_str} (Yours is {farmer_value})."
            else:
                return f"Does not meet requirement for {pretty_field}."
        else:
            if operator == "==":
                return f"Your {pretty_field} matches the required {value_str}."
            elif operator == "in":
                return f"Your {pretty_field} ({str(farmer_value).title()}) is an eligible category."
            elif operator in ["<", "<="]:
                return f"Your {pretty_field} ({farmer_value}) is below the {value_str} limit."
            elif operator in [">", ">="]:
                return f"Your {pretty_field} ({farmer_value}) meets the minimum {value_str} requirement."
            else:
                return f"Meets criteria for {pretty_field}."

    @staticmethod
    def explain_eligible(passed_rules: list) -> list:
        """Generates positive reasons for eligible schemes."""
        if not passed_rules:
            return ["You met all general eligibility criteria for this scheme."]
            
        reasons = []
        for r in passed_rules:
            reasons.append(SchemeExplainer._translate_rule(r, is_failed=False))
        return reasons

    @staticmethod
    def explain_ineligible(failed_rules: list) -> list:
        """Generates negative reasons for ineligible schemes."""
        if not failed_rules:
            return ["You did not meet the specific criteria for this scheme."]
            
        reasons = []
        for r in failed_rules:
            reasons.append(SchemeExplainer._translate_rule(r, is_failed=True))
        return reasons