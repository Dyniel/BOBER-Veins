"""
Results reporting and markdown table exporter.
"""

from pathlib import Path
from typing import Dict, Any, List
import json
import pandas as pd


def export_master_results_markdown(
    results_dict: Dict[str, Any],
    output_path: str = "reports/results/master_results.md",
) -> str:
    """Formats and exports benchmark results to a formatted Markdown report."""
    lines = [
        "# VascuShift-GPINN Master Scientific Results Table",
        "Generated for ISSSP 2026 Evaluation.",
        "",
        "## 1. Physiological Model Comparison (Leave-One-Subject-Out Cross-Validation)",
        "Target variable: Internal Jugular Vein (IJV) Cross-Sectional Area ($mm^2$)",
        "",
        "| Model Class | Model Description | LOSO MAE ($mm^2$) | LOSO RMSE ($mm^2$) | $R^2$ | Monotonicity Violations | Total Violations | Improvement vs Baseline 0 (%) |",
        "| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]

    physio = results_dict.get("physiology_models", {})
    b0_mae = physio.get("baseline_mean", {}).get("mae", 1.0)

    order = [
        ("baseline_mean", "Baseline 0: Constant Mean"),
        ("baseline_linear", "Baseline 1a: Linear Regression"),
        ("baseline_ridge", "Baseline 1b: Ridge Regression"),
        ("mechanistic_physics", "Baseline 2: Mechanistic 2-Compartment"),
        ("unconstrained_nn", "Model 3a: Unconstrained Neural Network"),
        ("vascushift_pinn", "Model 3b: VascuShift-PINN (Physics-Informed)"),
    ]

    for key, name in order:
        if key in physio:
            m = physio[key]
            mae = m.get("mae", "N/A")
            rmse = m.get("rmse", "N/A")
            r2 = m.get("r2", "N/A")
            mon = m.get("monotonicity_violations", 0)
            tot = m.get("total_violations", 0)
            if isinstance(mae, (int, float)) and b0_mae > 0:
                imp = round((b0_mae - mae) / b0_mae * 100.0, 1)
                imp_str = f"+{imp}%" if imp > 0 else f"{imp}%"
            else:
                imp_str = "-"
            lines.append(
                f"| **{key}** | {name} | {mae} | {rmse} | {r2} | {mon} | {tot} | {imp_str} |"
            )

    lines.extend([
        "",
        "## 2. Optical rPPG Benchmark (Subject-Independent Evaluation)",
        "Heart Rate Estimation Performance against Synchronized Reference PPG",
        "",
        "| Algorithm | Method Family | HR MAE (BPM) | HR RMSE (BPM) | Pearson $r$ | Mean SNR (dB) | Valid Window Coverage (%) |",
        "| :--- | :--- | :---: | :---: | :---: | :---: | :---: |",
    ])

    rppg_res = results_dict.get("rppg_benchmark", {})
    for algo, vals in rppg_res.items():
        family = "Color Difference" if algo == "chrom" else ("Subspace Projection" if algo == "pos" else "Spectral Absorption")
        lines.append(
            f"| **{algo.upper()}** | {family} | {vals.get('mae', 'N/A')} | {vals.get('rmse', 'N/A')} | "
            f"{vals.get('pearson_r', 'N/A')} | {vals.get('mean_snr_db', 'N/A')} | {vals.get('coverage_pct', 'N/A')}% |"
        )

    lines.extend([
        "",
        "## 3. Identifiability & Parameter Recovery (Synthetic Ground-Truth Evaluation)",
        "",
        "| Noise Level $\\sigma$ | $A_0$ Relative Error (%) | $k$ Relative Error (%) | $P_0$ Error (mmHg) | CVP Error (mmHg) |",
        "| :---: | :---: | :---: | :---: | :---: |",
    ])

    ident = results_dict.get("identifiability", {})
    for nl, vals in ident.items():
        lines.append(
            f"| {nl} | {vals.get('A0_rel_err_pct', 'N/A')}% | {vals.get('k_rel_err_pct', 'N/A')}% | "
            f"{vals.get('P0_abs_err', 'N/A')} | {vals.get('CVP_abs_err', 'N/A')} |"
        )

    md_content = "\n".join(lines)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(md_content)

    return md_content


def save_master_results_json(
    results_dict: Dict[str, Any],
    output_path: str = "reports/results/master_results.json",
) -> None:
    """Exports master results to JSON."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results_dict, f, indent=2)

