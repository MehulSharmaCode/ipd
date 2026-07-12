import pandas as pd
import random
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "crop_recommendation_dataset.csv"

soil_types = ["sandy", "loamy", "clay"]
seasons = ["kharif", "rabi", "zaid"]
irrigation = ["yes", "no"]

crops = ["wheat", "rice", "cotton", "sugarcane", "maize"]

rows = []

for _ in range(3000):

    nitrogen = random.randint(10, 100)
    phosphorus = random.randint(10, 100)
    potassium = random.randint(10, 100)
    rainfall = random.randint(50, 300)
    temperature = random.randint(15, 40)

    soil = random.choice(soil_types)
    season = random.choice(seasons)
    irrigated = random.choice(irrigation)

    crop = random.choice(crops)

    rows.append([
        nitrogen,
        phosphorus,
        potassium,
        rainfall,
        temperature,
        soil,
        season,
        irrigated,
        crop
    ])

df = pd.DataFrame(rows, columns=[
    "nitrogen",
    "phosphorus",
    "potassium",
    "rainfall",
    "temperature",
    "soil",
    "season",
    "irrigation",
    "label"
])

df.to_csv(DATA_PATH, index=False)

print("Crop dataset generated:", DATA_PATH)