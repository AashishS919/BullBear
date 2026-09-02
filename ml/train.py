"""Train the LSTM per ticker and persist artifacts.

For each symbol: prepare sequences, train, evaluate (val MSE + directional accuracy),
and save:
  artifacts/<SYMBOL>.keras         - trained model
  artifacts/<SYMBOL>.scaler.pkl    - fitted MinMaxScaler
  artifacts/metrics.json           - per-symbol training metrics

Usage:
  python train.py                       # all symbols, default epochs
  python train.py --epochs 25 NABIL NTC # subset
"""
import json
import sys

import joblib
import numpy as np

from config import ARTIFACTS_DIR, BATCH_SIZE, DEFAULT_EPOCHS, SYMBOLS, WINDOW
from data import prepare
from model import build_lstm


def directional_accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Share of steps where predicted move direction matches the actual move."""
    if len(y_true) < 2:
        return 0.0
    true_dir = np.sign(np.diff(y_true))
    pred_dir = np.sign(y_pred[1:] - y_true[:-1])
    return float(np.mean(true_dir == pred_dir))


def parse_args(argv: list[str]):
    epochs = DEFAULT_EPOCHS
    symbols = []
    i = 0
    while i < len(argv):
        if argv[i] == "--epochs":
            epochs = int(argv[i + 1]); i += 2
        else:
            symbols.append(argv[i].upper()); i += 1
    return epochs, (symbols or SYMBOLS)


def main(argv: list[str]) -> None:
    epochs, symbols = parse_args(argv)
    metrics = {}

    for symbol in symbols:
        print(f"\n=== Training {symbol} (epochs={epochs}) ===")
        X_tr, y_tr, X_val, y_val, scaler, _ = prepare(symbol, WINDOW)
        model = build_lstm(WINDOW)
        model.fit(
            X_tr, y_tr,
            validation_data=(X_val, y_val),
            epochs=epochs, batch_size=BATCH_SIZE, verbose=2,
        )

        val_pred = model.predict(X_val, verbose=0).flatten()
        val_mse = float(np.mean((val_pred - y_val) ** 2))
        dir_acc = directional_accuracy(y_val, val_pred)

        model.save(ARTIFACTS_DIR / f"{symbol}.keras")
        joblib.dump(scaler, ARTIFACTS_DIR / f"{symbol}.scaler.pkl")
        metrics[symbol] = {
            "val_mse": round(val_mse, 6),
            "directional_accuracy": round(dir_acc, 4),
            "epochs": epochs,
            "train_samples": int(len(X_tr)),
            "val_samples": int(len(X_val)),
        }
        print(f"  {symbol}: val_mse={val_mse:.6f} dir_acc={dir_acc:.3f}")

    (ARTIFACTS_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2))
    print(f"\nSaved artifacts to {ARTIFACTS_DIR}")


if __name__ == "__main__":
    main(sys.argv[1:])
