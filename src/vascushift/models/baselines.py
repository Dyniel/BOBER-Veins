"""
Conventional statistical and constant baseline models for physiological state prediction.
All models follow a standard fit / predict API.
"""

from typing import Optional, Dict, Any, Union
import numpy as np
import pandas as pd


class BaselineMeanPredictor:
    """
    Baseline 0 — Trivial constant predictor.
    Predicts the mean (or median) of the training set target.
    """

    def __init__(self, strategy: str = "mean"):
        self.strategy = strategy
        self.constant_val_: Optional[float] = None

    def fit(self, X: np.ndarray, y: np.ndarray) -> "BaselineMeanPredictor":
        if self.strategy == "median":
            self.constant_val_ = float(np.median(y))
        else:
            self.constant_val_ = float(np.mean(y))
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if self.constant_val_ is None:
            raise ValueError("Model is not fitted.")
        return np.full(shape=(len(X),), fill_value=self.constant_val_, dtype=float)


class BaselineLinearRegression:
    """
    Baseline 1a — Ordinary Least Squares (OLS) Linear Regression.
    Fitted via closed-form pseudo-inverse: beta = (X^T X)^{-1} X^T y.
    """

    def __init__(self, fit_intercept: bool = True):
        self.fit_intercept = fit_intercept
        self.coef_: Optional[np.ndarray] = None
        self.intercept_: float = 0.0

    def fit(self, X: np.ndarray, y: np.ndarray) -> "BaselineLinearRegression":
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)
        if X.ndim == 1:
            X = X[:, np.newaxis]

        if self.fit_intercept:
            X_design = np.column_stack([np.ones(len(X)), X])
            beta, _, _, _ = np.linalg.lstsq(X_design, y, rcond=None)
            self.intercept_ = float(beta[0])
            self.coef_ = beta[1:]
        else:
            beta, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
            self.intercept_ = 0.0
            self.coef_ = beta
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=float)
        if X.ndim == 1:
            X = X[:, np.newaxis]
        return np.dot(X, self.coef_) + self.intercept_


class BaselineRidgeRegression:
    """
    Baseline 1b — Ridge Regression with L2 Regularization.
    Closed-form solution: beta = (X^T X + alpha * I)^{-1} X^T y.
    """

    def __init__(self, alpha: float = 1.0, fit_intercept: bool = True):
        self.alpha = float(alpha)
        self.fit_intercept = fit_intercept
        self.coef_: Optional[np.ndarray] = None
        self.intercept_: float = 0.0

    def fit(self, X: np.ndarray, y: np.ndarray) -> "BaselineRidgeRegression":
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)
        if X.ndim == 1:
            X = X[:, np.newaxis]

        if self.fit_intercept:
            X_mean = np.mean(X, axis=0)
            y_mean = np.mean(y)
            X_centered = X - X_mean
            y_centered = y - y_mean
            p = X.shape[1]
            A = np.dot(X_centered.T, X_centered) + self.alpha * np.eye(p)
            b = np.dot(X_centered.T, y_centered)
            self.coef_ = np.linalg.solve(A, b)
            self.intercept_ = float(y_mean - np.dot(X_mean, self.coef_))
        else:
            p = X.shape[1]
            A = np.dot(X.T, X) + self.alpha * np.eye(p)
            b = np.dot(X.T, y)
            self.coef_ = np.linalg.solve(A, b)
            self.intercept_ = 0.0
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=float)
        if X.ndim == 1:
            X = X[:, np.newaxis]
        return np.dot(X, self.coef_) + self.intercept_

