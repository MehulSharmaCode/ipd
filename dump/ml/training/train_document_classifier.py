import torch
import torch.nn as nn
from pathlib import Path


# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "models" / "document_classifier.pt"


class SimpleCNN(nn.Module):

    def __init__(self):
        super().__init__()

        self.conv = nn.Conv2d(3, 16, 3)
        self.relu = nn.ReLU()
        self.fc = nn.Linear(16 * 62 * 62, 2)

    def forward(self, x):

        x = self.conv(x)
        x = self.relu(x)
        x = x.view(x.size(0), -1)
        x = self.fc(x)

        return x


def main():

    print("Training placeholder for document classifier...")

    model = SimpleCNN()

    # Save model
    torch.save(model, MODEL_PATH)

    print(f"✅ Document classifier saved at: {MODEL_PATH}")


if __name__ == "__main__":
    main()