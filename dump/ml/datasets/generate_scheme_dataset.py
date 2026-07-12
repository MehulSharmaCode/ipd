import pandas as pd
import random
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "scheme_success_dataset.csv"


# Regional crop patterns
STATE_CROPS = {
    "maharashtra": ["cotton", "sugarcane"],
    "punjab": ["wheat", "rice"],
    "up": ["rice", "wheat"],
    "karnataka": ["sugarcane", "rice"],
    "gujarat": ["cotton", "wheat"]
}

# Irrigation likelihood
IRRIGATION_PROB = {
    "maharashtra": 0.5,
    "punjab": 0.8,
    "up": 0.6,
    "karnataka": 0.4,
    "gujarat": 0.5
}

SCHEMES = [
    "pm_kisan",
    "drip_irrigation",
    "crop_insurance",
    "small_farmer_support",
    "medium_farmer_modernization",
    "large_farmer_irrigation_support",
    "cotton_support_scheme",
    "rice_development_scheme",
    "sugarcane_incentive",
    "low_income_farmer_aid"
]

STATES = list(STATE_CROPS.keys())


def generate_farmer():

    state = random.choice(STATES)

    crop = random.choice(STATE_CROPS[state])

    land_size = round(random.uniform(0.5, 6), 2)

    # Farmer type based on land size
    if land_size < 2:
        farmer_type = "small"
    elif land_size < 4:
        farmer_type = "medium"
    else:
        farmer_type = "large"

    # Irrigation probability
    irrigation = "yes" if random.random() < IRRIGATION_PROB[state] else "no"

    # Income estimation
    base_income = land_size * random.randint(30000, 80000)

    if irrigation == "yes":
        base_income *= 1.2

    income = int(base_income)

    scheme = random.choice(SCHEMES)

    approved = simulate_scheme_approval(
        farmer_type,
        income,
        land_size,
        irrigation,
        scheme
    )

    return [
        income,
        land_size,
        state,
        crop,
        irrigation,
        farmer_type,
        scheme,
        approved
    ]


def simulate_scheme_approval(farmer_type, income, land_size, irrigation, scheme):

    if scheme == "pm_kisan":
        if farmer_type == "small" and income < 200000:
            return 1

    if scheme == "drip_irrigation":
        if irrigation == "no" and land_size > 1:
            return random.choice([0, 1])

    if scheme == "crop_insurance":
        return random.choice([0, 1])

    if scheme == "small_farmer_support":
        if farmer_type == "small":
            return 1

    if scheme == "medium_farmer_modernization":
        if farmer_type == "medium":
            return random.choice([0, 1])

    if scheme == "large_farmer_irrigation_support":
        if farmer_type == "large":
            return random.choice([0, 1])

    if scheme == "cotton_support_scheme":
        return random.choice([0, 1])

    if scheme == "rice_development_scheme":
        return random.choice([0, 1])

    if scheme == "sugarcane_incentive":
        return random.choice([0, 1])

    if scheme == "low_income_farmer_aid":
        if income < 120000:
            return 1

    return 0


def generate_dataset(n=100000):

    rows = []

    for _ in range(n):
        rows.append(generate_farmer())

    df = pd.DataFrame(rows, columns=[
        "income",
        "land_size",
        "state",
        "crop",
        "irrigation",
        "farmer_type",
        "scheme",
        "approved"
    ])

    df.to_csv(DATA_PATH, index=False)

    print(f"Dataset generated with {len(df)} rows")
    print(f"Saved at: {DATA_PATH}")


if __name__ == "__main__":
    generate_dataset()