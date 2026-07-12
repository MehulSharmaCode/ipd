import torch
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "models" / "document_classifier.pt"


class DocumentClassifier:

    def __init__(self):

        self.model = torch.load(MODEL_PATH)

    def classify(self, image_tensor):

        output = self.model(image_tensor)

        return output.argmax().item()