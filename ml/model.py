"""LSTM network definition.

Stacked LSTM with Dropout layers to curb overfitting on the 5-year series, and a Dense
head producing the next-day (scaled) close. Kept compact for fast CPU training.
"""
from tensorflow.keras import Input, Sequential
from tensorflow.keras.layers import Dense, Dropout, LSTM


def build_lstm(window: int) -> Sequential:
    model = Sequential([
        Input(shape=(window, 1)),
        LSTM(64, return_sequences=True),
        Dropout(0.2),
        LSTM(32),
        Dropout(0.2),
        Dense(16, activation="relu"),
        Dense(1),
    ])
    model.compile(optimizer="adam", loss="mean_squared_error", metrics=["mae"])
    return model
