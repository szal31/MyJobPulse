"""Forecast accuracy metrics."""
import numpy as np


def mase(y_true, y_pred, y_train, m: int) -> float:
    y_true, y_pred = np.asarray(y_true, float), np.asarray(y_pred, float)
    y_train = np.asarray(y_train, float)
    y_train = y_train[~np.isnan(y_train)]
    scale = np.mean(np.abs(y_train[m:] - y_train[:-m]))
    return float(np.nanmean(np.abs(y_true - y_pred)) / scale)


def mape(y_true, y_pred) -> float:
    y_true, y_pred = np.asarray(y_true, float), np.asarray(y_pred, float)
    return float(np.nanmean(np.abs((y_true - y_pred) / y_true)) * 100)
