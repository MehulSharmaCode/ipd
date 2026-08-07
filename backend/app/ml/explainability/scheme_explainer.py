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
            field = r.get("field", "")
            value = r.get("value", "")
            
            field_names = {
                "income": "Annual Income",
                "land_size": "Land Size",
                "farmer_type": "Farmer Category",
                "crop": "Crop Type",
                "irrigation": "Irrigation Status",
                "state": "State",
                "gender": "Gender",
                "category": "Category"
            }
            pretty_field = field_names.get(field, field.replace("_", " ").title())
            
            if isinstance(value, list):
                val_str = ", ".join(str(v).title() for v in value)
            else:
                val_str = str(value).title()
                
            if field == "income" and isinstance(value, (int, float)):
                val_str = f"₹{value:,}"
                
            reasons.append(f"{pretty_field}: {val_str}")
            
        if reasons:
            return [f"Matches: {', '.join(reasons)}"]
        return ["You met all general eligibility criteria for this scheme."]

    @staticmethod
    def explain_ineligible(failed_rules: list) -> list:
        """Generates negative reasons for ineligible schemes."""
        if not failed_rules:
            return ["You did not meet the specific criteria for this scheme."]
            
        reasons = []
        for r in failed_rules:
            field = r.get("field", "")
            value = r.get("value", "")
            farmer_val = r.get("farmer_value", "Unknown")
            
            field_names = {
                "income": "Annual Income",
                "land_size": "Land Size",
                "farmer_type": "Farmer Category",
                "crop": "Crop Type",
                "irrigation": "Irrigation Status",
                "state": "State",
                "gender": "Gender",
                "category": "Category"
            }
            pretty_field = field_names.get(field, field.replace("_", " ").title())
            
            if isinstance(value, list):
                req_val = ", ".join(str(v).title() for v in value)
            else:
                req_val = str(value).title()
            
            if field == "income" and isinstance(value, (int, float)):
                req_val = f"₹{value:,}"
                
            reasons.append(f"Requires {pretty_field} = {req_val}, but your profile has {str(farmer_val).title()}")
            
        return ["Not eligible: " + "; ".join(reasons)]