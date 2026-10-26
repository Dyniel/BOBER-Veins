"""
Ablation study on physics constraints and regularizers.
Evaluates model behavior across lambda_physics in [0.0, 0.1, 0.5, 1.0, 2.0, 5.0].
"""

from typing import Dict, Any, List, Optional
import numpy as np

from vascushift.data.esa_loader import load_esa_data
from vascushift.data.preprocessing import get_subject_grouped_splits
from vascushift.models.physics_informed import VascuShiftPINN
from vascushift.evaluation.metrics import (
    compute_regression_metrics,
    compute_physical_constraint_violations,
)


def run_physics_ablation_experiment(
    data_dir: str = "data",
    lambda_grid: Optional[List[float]] = None,
    seed: int = 42,
) -> Dict[str, Any]:
    """
    Evaluates effect of physics loss weight lambda_p on test error and physical consistency.
    """
    if lambda_grid is None:
        lambda_grid = [0.0, 0.1, 0.5, 1.0, 2.0, 5.0]

    df, _, _ = load_esa_data(data_dir=data_dir)
    splits = get_subject_grouped_splits(df, subject_col="subject_id")

    ablation_results = {}

    for lam in lambda_grid:
        all_preds = []
        all_targets = []
        all_gz = []

        for fold_idx, (train_df, test_df, _) in enumerate(splits):
            X_train_gz = train_df["gz"].values
            posture_train = np.where(train_df["posture"] == "seated", 0.0, 90.0)
            y_train_area = train_df["IJV_area_mm2"].values
            y_train_press = train_df["IJV_pressure_mmHg"].values

            X_test_gz = test_df["gz"].values
            posture_test = np.where(test_df["posture"] == "seated", 0.0, 90.0)
            y_test_area = test_df["IJV_area_mm2"].values

            all_targets.extend(y_test_area.tolist())
            all_gz.extend(X_test_gz.tolist())

            model = VascuShiftPINN(
                lambda_data=1.0,
                lambda_physics=lam,
                lambda_constraints=2.0 if lam > 0 else 0.0,
                epochs=300,
                lr=0.005,
                seed=seed + fold_idx,
            ).fit(
                gz=X_train_gz,
                area_obs=y_train_area,
                posture_deg=posture_train,
                pressure_obs=y_train_press,
            )
            preds = model.predict(X_test_gz, posture_test)
            all_preds.extend(preds.tolist())

        y_true_arr = np.array(all_targets)
        y_pred_arr = np.array(all_preds)
        gz_arr = np.array(all_gz)

        reg_metrics = compute_regression_metrics(y_true_arr, y_pred_arr)
        violations = compute_physical_constraint_violations(gz_arr, y_pred_arr)

        ablation_results[f"lambda_{lam:.1f}"] = {
            "lambda_physics": lam,
            "mae": reg_metrics["mae"],
            "rmse": reg_metrics["rmse"],
            "r2": reg_metrics["r2"],
            "total_violations": violations["total_violations"],
            "monotonicity_violations": violations["monotonicity_violations"],
            "is_physically_consistent": violations["is_physically_consistent"],
        }

    return ablation_results
