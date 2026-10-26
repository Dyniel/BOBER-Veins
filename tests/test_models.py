"""
Unit tests for baseline models, mechanistic estimator, and physics-informed neural network.
"""

import numpy as np
import pytest

from vascushift.models.baselines import (
    BaselineMeanPredictor,
    BaselineLinearRegression,
    BaselineRidgeRegression,
)
from vascushift.models.inverse_model import MechanisticParameterEstimator
from vascushift.models.physics_informed import VascuShiftPINN


def test_baseline_mean_predictor():
    X = np.array([0.0, 0.5, 1.0])
    y = np.array([100.0, 50.0, 10.0])
    model = BaselineMeanPredictor().fit(X, y)
    preds = model.predict(np.array([0.25, 0.75]))
    assert np.allclose(preds, 53.333, atol=1e-2)


def test_baseline_linear_regression():
    X = np.array([0.0, 1.0])
    y = np.array([100.0, 10.0])
    model = BaselineLinearRegression().fit(X, y)
    preds = model.predict(np.array([0.5]))
    assert np.isclose(preds[0], 55.0, atol=1e-3)


def test_mechanistic_parameter_estimator():
    gz = np.array([0.0, 0.25, 0.5, 0.75, 1.0])
    area_obs = np.array([108.0, 68.0, 34.0, 24.0, 12.0])
    estimator = MechanisticParameterEstimator(max_iter=100)
    estimator.fit(gz=gz, area_obs=area_obs)
    preds = estimator.predict(gz)
    assert len(preds) == len(gz)
    assert preds[0] > preds[-1]  # Monotonic reduction with gravity
    assert estimator.params.A0 > 50.0


def test_vascushift_pinn_training_step():
    gz = np.array([0.0, 0.25, 0.5, 0.75, 1.0])
    area_obs = np.array([108.0, 68.0, 34.0, 24.0, 12.0])
    pinn = VascuShiftPINN(
        lambda_data=1.0,
        lambda_physics=1.0,
        lambda_constraints=2.0,
        epochs=30,
        lr=0.01,
        seed=42,
    )
    pinn.fit(gz=gz, area_obs=area_obs)
    preds = pinn.predict(gz)
    assert len(preds) == len(gz)
    assert np.all(preds > 0.0)

