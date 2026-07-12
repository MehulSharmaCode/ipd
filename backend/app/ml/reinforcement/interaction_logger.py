import json
from datetime import datetime
from pathlib import Path

LOG_FILE = Path("ml/data/interactions.jsonl")


def log_interaction(profile, scheme, reward):

    record = {
        "timestamp": datetime.utcnow().isoformat(),
        "profile": profile,
        "scheme": scheme,
        "reward": reward
    }

    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(record) + "\n")