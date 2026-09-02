"""Shared ML configuration. Reads Mongo connection from env with sane local defaults."""
import os
from pathlib import Path

MONGO_URI = os.environ.get("BB_MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.environ.get("BB_MONGO_DB", "bullbear")

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
ARTIFACTS_DIR.mkdir(exist_ok=True)

# Sequence model hyperparameters.
WINDOW = 60            # look-back days fed into the LSTM
HORIZON = 5            # forecast steps produced per run by iterative rollout
TRAIN_SPLIT = 0.85     # chronological train/val split
DEFAULT_EPOCHS = 15
BATCH_SIZE = 32

SYMBOLS = ["NABIL", "NICA", "NTC", "NRIC", "UPPER", "CHCL", "VLBS", "SBL", "AHL", "ADBL"]
