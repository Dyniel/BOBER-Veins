"""
Command-Line Interface (CLI) for BOBER Veins / VascuShift-GPINN.
Targeted for ISSSP 2026 reproducibility and experiments.
"""

import sys
import argparse
import yaml
from pathlib import Path
from typing import Dict, Any

from vascushift.data.esa_loader import load_esa_data, query_hreda_tap
from vascushift.physics.simulator import VenousHemodynamicSimulator
from vascushift.experiments.physiology import run_physiology_loso_experiment
from vascushift.experiments.ablations import run_physics_ablation_experiment
from vascushift.experiments.recovery import run_synthetic_identifiability_experiment
from vascushift.experiments.rppg import run_rppg_benchmark_experiment
from vascushift.evaluation.reporting import export_master_results_markdown, save_master_results_json
from vascushift.visualization.figures import (
    generate_figure_1_architecture,
    generate_figure_2_gravity_physiology,
    generate_figure_3_baseline_comparison,
    generate_figure_4_synthetic_recovery,
    generate_figure_5_rppg_validation,
    generate_figure_6_ablation_results,
    generate_figure_7_demonstrator,
)
from vascushift.visualization.dashboard import launch_local_demonstrator


def load_yaml_config(path: str) -> Dict[str, Any]:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def cmd_data_audit(args: argparse.Namespace) -> None:
    print("=== [CLI] ESA HEADWARD FLUID SHIFT DATA AUDIT ===")
    df, report, meta = load_esa_data(data_dir="data")
    print(f"Investigation: {meta['investigation_acronym']} (DOI: {meta['doi']})")
    print(f"Data source:    {meta['source']}")
    print(f"Participants:   {meta['n_subjects']} subjects (Cohort size N={meta['n_samples']})")
    print(f"Gravity levels: {meta['gravity_levels']}")
    print("\n--- Validation Report ---")
    print(report.summary())
    print("\n--- Real-Time ESA HREDA Query ---")
    print(meta["hreda_status"])


def cmd_simulate(args: argparse.Namespace) -> None:
    print("=== [CLI] FORWARD VENOUS HEMODYNAMIC SIMULATION ===")
    sim = VenousHemodynamicSimulator()
    df_sweep = sim.simulate_gravity_sweep(gravity_levels=[0.0, 0.16, 0.25, 0.38, 0.50, 0.75, 1.00])
    print(df_sweep.to_string(index=False))


def cmd_train_physics(args: argparse.Namespace) -> None:
    print("=== [CLI] PHYSICS-INFORMED MODEL TRAINING & LOSO EVALUATION ===")
    res = run_physiology_loso_experiment(data_dir="data")
    print(f"Evaluated on {res['n_evaluations']} samples across 9 Leave-One-Subject-Out folds.")
    for k, v in res["models"].items():
        print(f"  [{k:22s}] MAE: {v['mae']:5.2f} mm² | RMSE: {v['rmse']:5.2f} mm² | R²: {v['r2']:6.3f} | Violations: {v['total_violations']}")


def cmd_evaluate(args: argparse.Namespace) -> None:
    print("=== [CLI] FULL EXPERIMENT EVALUATION SUITE ===")
    print("1. Running Physiology LOSO Benchmark...")
    physio_res = run_physiology_loso_experiment(data_dir="data")

    print("2. Running Physics Loss Ablation...")
    ablation_res = run_physics_ablation_experiment(data_dir="data")

    print("3. Running Parameter Identifiability Analysis...")
    ident_res = run_synthetic_identifiability_experiment()

    print("4. Running Optical rPPG Benchmarks...")
    rppg_res = run_rppg_benchmark_experiment(data_dir="data")

    master_results = {
        "physiology_models": physio_res["models"],
        "ablations": ablation_res,
        "identifiability": ident_res,
        "rppg_benchmark": rppg_res,
    }

    out_json = "reports/results/master_results.json"
    out_md = "reports/results/master_results.md"
    save_master_results_json(master_results, out_json)
    export_master_results_markdown(master_results, out_md)
    print(f"\nSaved Master Results to:\n  - {out_json}\n  - {out_md}")


def cmd_run_rppg(args: argparse.Namespace) -> None:
    print("=== [CLI] OPTICAL rPPG BENCHMARKING ===")
    res = run_rppg_benchmark_experiment(data_dir="data")
    for algo, vals in res.items():
        print(f"  [{algo.upper():6s}] HR MAE: {vals['mae']:5.2f} BPM | RMSE: {vals['rmse']:5.2f} BPM | Pearson r: {vals['pearson_r']:6.3f} | SNR: {vals['mean_snr_db']:5.1f} dB | Coverage: {vals['coverage_pct']}%")


def cmd_figures(args: argparse.Namespace) -> None:
    print("=== [CLI] GENERATING PUBLICATION-QUALITY FIGURES ===")
    import json
    df_real, _, _ = load_esa_data(data_dir="data")

    # Run physiology LOSO (needed for targets & predictions)
    physio_res = run_physiology_loso_experiment(data_dir="data")

    # Use master results if already cached to avoid redundant recomputations
    master_path = Path("reports/results/master_results.json")
    if master_path.exists():
        with open(master_path, "r") as f:
            cached = json.load(f)
        ablation_res = cached.get("ablations")
        ident_res = cached.get("identifiability")
        rppg_res = cached.get("rppg_benchmark")
    else:
        ablation_res = None
        ident_res = None
        rppg_res = None

    if ablation_res is None:
        ablation_res = run_physics_ablation_experiment(data_dir="data")
    if ident_res is None:
        ident_res = run_synthetic_identifiability_experiment()
    if rppg_res is None:
        rppg_res = run_rppg_benchmark_experiment(data_dir="data")

    sim = VenousHemodynamicSimulator()
    sweep = sim.simulate_gravity_sweep()

    generate_figure_1_architecture("reports/figures/fig1_architecture.png")
    print("  - Figure 1: System Architecture saved.")
    generate_figure_2_gravity_physiology(df_real, "reports/figures/fig2_gravity_physiology.png")
    print("  - Figure 2: Gravity Physiology saved.")
    generate_figure_3_baseline_comparison(physio_res, "reports/figures/fig3_baseline_comparison.png")
    print("  - Figure 3: Baseline Comparison saved.")
    generate_figure_4_synthetic_recovery(ident_res, "reports/figures/fig4_synthetic_recovery.png")
    print("  - Figure 4: Synthetic Parameter Recovery saved.")
    generate_figure_5_rppg_validation(rppg_res, "reports/figures/fig5_rppg_validation.png")
    print("  - Figure 5: rPPG Signal Validation saved.")
    generate_figure_6_ablation_results(ablation_res, "reports/figures/fig6_ablation_results.png")
    print("  - Figure 6: Physics Ablation Results saved.")
    generate_figure_7_demonstrator(sweep, rppg_res, "reports/figures/fig7_demonstrator.png")
    print("  - Figure 7: Scientific Demonstrator saved.")


def cmd_demo(args: argparse.Namespace) -> None:
    launch_local_demonstrator(port=args.port, open_browser=args.open_browser)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="BOBER Veins / VascuShift-GPINN: Physics-Informed Venous Hemodynamics & Optical rPPG"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    p_audit = subparsers.add_parser("data-audit", help="Audit ESA HREDA and local dataset")
    p_audit.add_argument("--config", default="configs/data.yaml")

    p_sim = subparsers.add_parser("simulate", help="Forward physiological simulation")
    p_sim.add_argument("--config", default="configs/physics_model.yaml")

    p_train = subparsers.add_parser("train-physics", help="Train and evaluate PINN on real ESA data")
    p_train.add_argument("--config", default="configs/physiology.yaml")

    p_eval = subparsers.add_parser("evaluate", help="Execute full benchmark evaluation")
    p_eval.add_argument("--config", default="configs/experiments.yaml")

    p_rppg = subparsers.add_parser("run-rppg", help="Run rPPG benchmark on optical cohort")
    p_rppg.add_argument("--config", default="configs/rppg.yaml")

    p_fig = subparsers.add_parser("figures", help="Generate publication-ready figures")
    p_fig.add_argument("--config", default="configs/experiments.yaml")

    p_demo = subparsers.add_parser("demo", help="Launch interactive local demonstrator")
    p_demo.add_argument("--port", type=int, default=8501)
    p_demo.add_argument("--open-browser", action="store_true")

    args = parser.parse_args()
    if args.command == "data-audit":
        cmd_data_audit(args)
    elif args.command == "simulate":
        cmd_simulate(args)
    elif args.command == "train-physics":
        cmd_train_physics(args)
    elif args.command == "evaluate":
        cmd_evaluate(args)
    elif args.command == "run-rppg":
        cmd_run_rppg(args)
    elif args.command == "figures":
        cmd_figures(args)
    elif args.command == "demo":
        cmd_demo(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
