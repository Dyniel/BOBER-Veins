#!/usr/bin/env python3
"""Run physics loss weight ablation study."""
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "src"))

from vascushift.experiments.ablations import run_physics_ablation_experiment
import json

if __name__ == "__main__":
    print("=== RUNNING PHYSICS CONSTRAINT ABLATION ===")
    res = run_physics_ablation_experiment(data_dir=str(repo_root / "data"))
    for k, v in res.items():
        print(f"  [{k}] MAE: {v['mae']:5.2f} mm² | RMSE: {v['rmse']:5.2f} mm² | Violations: {v['total_violations']}")

