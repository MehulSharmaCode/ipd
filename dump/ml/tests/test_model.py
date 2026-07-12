from app.ml.inference.success_predictor import SchemeSuccessPredictor

model = SchemeSuccessPredictor()

features = {
    "income": 120000,
    "land_size": 1.5,
    "state": "maharashtra",
    "crop": "cotton",
    "irrigation": "no",
    "farmer_type": "small",
    "scheme": "pm_kisan"
}

prob = model.predict_success(features)

print("Success probability:", prob)