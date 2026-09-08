class SchemeExplainer:
    """
    Generates dynamic explanations for scheme recommendations based on passed/failed rules.
    """

    # --- Evidence-based reasoning (added for the scheme requirements/timeline/
    # reasoning feature; see docs/SCHEME_REQUIREMENTS_FEATURE_PLAN.md sec. 5.6-5.7).
    # These are ADDITIVE -- explain_eligible/explain_ineligible/_translate_rule
    # below are unchanged and still power the existing `scheme.explanation` field
    # the Dashboard already renders.

    SIGNAL_TYPE_BY_FIELD = {
        "state": "state_match",
        "district": "district_match",
        "income": "income_within_limit",
        "age": "age_within_range",
        "gender": "gender_match",
        "category": "social_category_match",
        "is_differently_abled": "disability_match",
        "land_size": "land_size_within_limit",
        "farmer_type": "farmer_type_match",
        "crop": "crop_match",
        "occupation_type": "occupation_match",
        "education_level": "education_match",
        "employment_status": "employment_match",
    }

    SIGNAL_PRIORITY = [
        "state_match", "district_match", "social_category_match", "gender_match",
        "disability_match", "age_within_range", "income_within_limit",
        "land_size_within_limit", "farmer_type_match", "occupation_match",
        "education_match", "employment_match", "crop_match", "other_criterion_match",
    ]

    PROFILE_FIELD_BY_RULE_FIELD = {
        "income": "annual_income",
        "land_size": "land_size_hectares",
        "crop": "primary_crops",
        "occupation_type": "occupation",
        "is_differently_abled": "is_differently_abled",
    }

    SIGNAL_FIELD_LABELS = {
        "income": "annual income", "land_size": "land holding", "age": "age",
        "state": "state", "district": "district", "gender": "gender",
        "category": "category", "farmer_type": "farmer category", "crop": "crop",
        "occupation_type": "occupation", "education_level": "education level",
        "employment_status": "employment status",
        "is_differently_abled": "disability status",
    }

    @staticmethod
    def _display_value(value):
        """Render a rule/profile value for embedding in a signal sentence.
        Never changes the underlying value -- only its textual presentation."""
        if isinstance(value, bool):
            return "Yes" if value else "No"
        if isinstance(value, list):
            return ", ".join(str(v).title() if isinstance(v, str) else str(v) for v in value)
        if isinstance(value, str):
            return value.title()
        return value

    @staticmethod
    def _signal_text(field: str, operator: str, value, farmer_value) -> str:
        """
        Build the human-readable sentence for one passed rule. Every number
        or category name in the sentence is read directly from `value` /
        `farmer_value` -- nothing here is invented.
        """
        label = SchemeExplainer.SIGNAL_FIELD_LABELS.get(field, field.replace("_", " "))
        f_disp = SchemeExplainer._display_value(farmer_value)
        v_disp = SchemeExplainer._display_value(value)
        both_numeric = isinstance(value, (int, float)) and not isinstance(value, bool) \
            and isinstance(farmer_value, (int, float)) and not isinstance(farmer_value, bool)

        if operator == "==":
            if field == "gender":
                return f"The scheme is for {v_disp} applicants, matching your profile."
            if field == "category":
                return f"The scheme targets the {v_disp} category, matching your profile."
            if field == "is_differently_abled":
                return "The scheme is for applicants with a disability, matching your profile."
            if field == "state":
                return f"Your state ({f_disp}) matches the scheme's state ({v_disp})."
            return f"Your {label} ({f_disp}) matches the required value ({v_disp})."

        if operator == "in":
            return f"Your {label} ({f_disp}) is one of the eligible values ({v_disp})."

        if operator in ("<", "<="):
            if field == "income" and both_numeric:
                return f"Your annual income (₹{farmer_value:,.0f}) is within the scheme's ₹{value:,.0f} limit."
            if field == "land_size":
                return f"Your land holding ({f_disp} ha) is within the scheme's {v_disp} ha limit."
            if field == "age":
                return f"Your age ({f_disp}) is within the scheme's maximum of {v_disp}."
            return f"Your {label} ({f_disp}) is within the scheme's limit of {v_disp}."

        if operator in (">", ">="):
            if field == "age":
                return f"Your age ({f_disp}) meets the scheme's minimum of {v_disp}."
            return f"Your {label} ({f_disp}) meets the scheme's minimum of {v_disp}."

        if operator in ("!=", "not_in"):
            return f"Your {label} ({f_disp}) is not in the excluded set."

        return f"Meets criteria for {label}."

    @staticmethod
    def build_match_signals(passed_rules: list, rule_provenance: str) -> list:
        """
        Convert a RulesEngine passed_rules[] list into typed MatchSignal dicts
        (section 5.6). One signal per passed rule -- never for a rule the
        profile did not actually satisfy.
        """
        signals = []
        for r in passed_rules or []:
            field = r.get("field", "")
            operator = r.get("operator", "")
            value = r.get("value")
            farmer_value = r.get("farmer_value")
            signal_type = SchemeExplainer.SIGNAL_TYPE_BY_FIELD.get(field, "other_criterion_match")
            profile_field = SchemeExplainer.PROFILE_FIELD_BY_RULE_FIELD.get(field, field)
            signals.append({
                "signal_type": signal_type,
                "field": field,
                "operator": operator,
                "scheme_value": value,
                "profile_value": farmer_value,
                "profile_field": profile_field,
                "text": SchemeExplainer._signal_text(field, operator, value, farmer_value),
                "evidence_source": "scheme_rule",
                "rule_provenance": rule_provenance,
            })
        return signals

    @staticmethod
    def _to_clause(text: str) -> str:
        """Fold a standalone MatchSignal sentence into a lowercase clause for
        the "Recommended because X, Y and Z" summary sentence."""
        clause = text.rstrip(".")
        if clause.startswith("Your "):
            return "your " + clause[5:]
        if clause.startswith("The "):
            return "the " + clause[4:]
        if clause:
            return clause[0].lower() + clause[1:]
        return clause

    NO_SIGNAL_REASON = (
        "This scheme is listed because your profile did not fail any of the "
        "eligibility criteria we could extract from the official scheme page."
    )

    @staticmethod
    def build_reason_summary(signals: list) -> str:
        """
        Deterministically assemble the top-3 (by SIGNAL_PRIORITY) match
        signals into one "Recommended because ..." sentence. No LLM, no
        free generation -- every clause is a signal already computed from
        the rules engine's own passed_rules.
        """
        if not signals:
            return SchemeExplainer.NO_SIGNAL_REASON

        ordered = sorted(
            signals,
            key=lambda s: SchemeExplainer.SIGNAL_PRIORITY.index(s["signal_type"])
            if s.get("signal_type") in SchemeExplainer.SIGNAL_PRIORITY
            else len(SchemeExplainer.SIGNAL_PRIORITY),
        )
        top = ordered[:3]
        clauses = [SchemeExplainer._to_clause(s["text"]) for s in top]

        if len(clauses) == 1:
            body = clauses[0]
        elif len(clauses) == 2:
            body = f"{clauses[0]} and {clauses[1]}"
        else:
            body = f"{', '.join(clauses[:-1])} and {clauses[-1]}"

        summary = f"Recommended because {body}."
        extra = len(signals) - len(top)
        if extra > 0:
            summary += f" (+{extra} more matching criteria)"
        return summary

    @staticmethod
    def compute_reason_confidence(signals: list, scheme: dict) -> str:
        """
        Honest confidence grade for the reason_summary, per section 5.7.
        A heuristically-extracted scheme with few signals can never claim
        "high" confidence -- this is the load-bearing guard against the
        rule_extractor.py false-positive risk documented in the plan's
        section 12.
        """
        if scheme.get("manually_verified") is True:
            return "verified"
        if scheme.get("extraction_method") == "llm" and len(signals) >= 2:
            return "high"
        if scheme.get("extraction_confidence") == "high" and len(signals) >= 3:
            return "high"
        if len(signals) >= 2:
            return "medium"
        return "low"

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