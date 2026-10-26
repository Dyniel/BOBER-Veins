"""
Physiological Leave-One-Subject-Out (LOSO) Cross-Validation Experiment.
Evaluates Baseline 0, Baseline 1, Baseline 2, Model 3a, and Model 3b.
"""

from typing import Dict, Any, List
import numpy as np
import pandas as pd

from vascushift.data.esa_loader import load_esa_data
from vascushift.data.preprocessing import get_subject_grouped_splits
from vascushift.models.baselines import (
    BaselineMeanPredictor,
    BaselineLinearRegression,
    BaselineRidgeRegression,
)
from vascushift.models.inverse_model import MechanisticParameterEstimator
from vascushift.models.physics_informed import VascuShiftPINN
from vascushift.evaluation.metrics import (
    compute_regression_metrics,
    compute_physical_constraint_violations,
)


def run_physiology_loso_experiment(
    data_dir: str = "data",
    seed: int = 42,
) -> Dict[str, Any]:
    """
    Executes 9-fold Leave-One-Subject-Out (LOSO) cross-validation on verified ESA data.
    """
    df, quality_report, metadata = load_esa_data(data_dir=data_dir)
    splits = get_subject_grouped_splits(df, subject_col="subject_id")

    model_keys = [
        "baseline_mean",
        "baseline_linear",
        "baseline_ridge",
        "mechanistic_physics",
        "unconstrained_nn",
        "vascushift_pinn",
    ]

    all_preds = {k: [] for k in model_keys}
    all_targets = []
    all_gz = []

    for fold_idx, (train_df, test_df, held_out) in enumerate(splits):
        X_train_gz = train_df["gz"].values
        posture_train = np.where(train_df["posture"] == "seated", 0.0, 90.0)
        y_train_area = train_df["IJV_area_mm2"].values
        y_train_press = train_df["IJV_pressure_mmHg"].values

        X_test_gz = test_df["gz"].values
        posture_test = np.where(test_df["posture"] == "seated", 0.0, 90.0)
        y_test_area = test_df["IJV_area_mm2"].values

        all_targets.extend(y_test_area.tolist())
        all_gz.extend(X_test_gz.tolist())

        # 1. Baseline 0 (Mean)
        b0 = BaselineMeanPredictor().fit(X_train_gz, y_train_area)
        all_preds["baseline_mean"].extend(b0.predict(X_test_gz).tolist())

        # 2. Baseline 1a (Linear OLS)
        b1_lin = BaselineLinearRegression().fit(X_train_gz, y_train_area)
        all_preds["baseline_linear"].extend(b1_lin.predict(X_test_gz).tolist())

        # 3. Baseline 1b (Ridge)
        b1_ridge = BaselineRidgeRegression(alpha=2.0).fit(X_train_gz, y_train_area)
        all_preds["baseline_ridge"].extend(b1_ridge.predict(X_test_gz).tolist())

        # 4. Baseline 2 (Mechanistic Physics)
        mech = MechanisticParameterEstimator(max_iter=300).fit(
            gz=X_train_gz,
            area_obs=y_train_area,
            posture_deg=posture_train,
            pressure_obs=y_train_press,
        )
        all_preds["mechanistic_physics"].extend(mech.predict(X_test_gz, posture_test).tolist())

        # 5. Model 3a (Unconstrained Neural Network: lambda_p=0, lambda_c=0)
        nn_unconstrained = VascuShiftPINN(
            lambda_data=1.0,
            lambda_physics=0.0,
            lambda_constraints=0.0,
            epochs=350,
            lr=0.005,
            seed=seed + fold_idx,
        ).fit(
            gz=X_train_gz,
            area_obs=y_train_area,
            posture_deg=posture_train,
            pressure_obs=y_train_press,
        )
        all_preds["unconstrained_nn"].extend(nn_unconstrained.predict(X_test_gz, posture_test).tolist())

        # 6. Model 3b (VascuShift-PINN: lambda_p=1.0, lambda_c=2.0)
        pinn = VascuShiftPINN(
            lambda_data=1.0,
            lambda_physics=1.0,
            lambda_constraints=2.0,
            epochs=350,
            lr=0.005,
            seed=seed + fold_idx,
        ).fit(
            gz=X_train_gz,
            area_obs=y_train_area,
            posture_deg=posture_train,
            pressure_obs=y_train_press,
        )
        all_preds["vascushift_pinn"].extend(pinn.predict(X_test_gz, posture_test).tolist())

    y_true_arr = np.array(all_targets)
    gz_arr = np.array(all_gz)

    results = {}
    for k in model_keys:
        preds = np.array(all_preds[k])
        reg_metrics = compute_regression_metrics(y_true_arr, preds)
        phys_violations = compute_physical_constraint_violations(gz_arr, preds)
        results[k] = {
            **reg_metrics,
            **phys_violations,
            "predictions": preds.tolist(),
        }

    return {
        "dataset_metadata": metadata,
        "n_evaluations": len(y_true_arr),
        "ground_truth_targets": y_true_arr.tolist(),
        "gravity_levels": gz_arr.tolist(),
        "models": results,
    }

