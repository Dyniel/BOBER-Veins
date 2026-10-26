# VascuShift-GPINN Master Scientific Results Table
Generated for ISSSP 2026 Evaluation.

## 1. Physiological Model Comparison (Leave-One-Subject-Out Cross-Validation)
Target variable: Internal Jugular Vein (IJV) Cross-Sectional Area ($mm^2$)

| Model Class | Model Description | LOSO MAE ($mm^2$) | LOSO RMSE ($mm^2$) | $R^2$ | Monotonicity Violations | Total Violations | Improvement vs Baseline 0 (%) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **baseline_mean** | Baseline 0: Constant Mean | 35.416 | 41.694 | -0.0142 | 20 | 20 | 0.0% |
| **baseline_linear** | Baseline 1a: Linear Regression | 14.779 | 18.754 | 0.7948 | 22 | 22 | +58.3% |
| **baseline_ridge** | Baseline 1b: Ridge Regression | 16.217 | 21.486 | 0.7307 | 21 | 21 | +54.2% |
| **mechanistic_physics** | Baseline 2: Mechanistic 2-Compartment | 12.586 | 16.447 | 0.8422 | 21 | 21 | +64.5% |
| **unconstrained_nn** | Model 3a: Unconstrained Neural Network | 33.288 | 48.422 | -0.3679 | 25 | 25 | +6.0% |
| **vascushift_pinn** | Model 3b: VascuShift-PINN (Physics-Informed) | 40.562 | 55.545 | -0.8 | 19 | 19 | -14.5% |

## 2. Optical rPPG Benchmark (Subject-Independent Evaluation)
Heart Rate Estimation Performance against Synchronized Reference PPG

| Algorithm | Method Family | HR MAE (BPM) | HR RMSE (BPM) | Pearson $r$ | Mean SNR (dB) | Valid Window Coverage (%) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **GREEN** | Spectral Absorption | 0.395 | 0.552 | 0.9988 | -2.36 | 66.7% |
| **CHROM** | Color Difference | 0.062 | 0.068 | 1.0 | 6.59 | 100.0% |
| **POS** | Subspace Projection | 0.028 | 0.033 | 1.0 | 10.52 | 100.0% |

## 3. Identifiability & Parameter Recovery (Synthetic Ground-Truth Evaluation)

| Noise Level $\sigma$ | $A_0$ Relative Error (%) | $k$ Relative Error (%) | $P_0$ Error (mmHg) | CVP Error (mmHg) |
| :---: | :---: | :---: | :---: | :---: |
| noise_0.00 | 6.38% | 68.29% | 8.5 | 3.72 |
| noise_0.02 | 8.91% | 65.02% | 8.17 | 4.18 |
| noise_0.05 | 6.64% | 69.26% | 8.36 | 3.79 |
| noise_0.10 | 15.73% | 65.1% | 6.57 | 4.05 |
| noise_0.15 | 15.0% | 62.17% | 7.52 | 4.16 |
| noise_0.20 | 12.84% | 59.72% | 6.73 | 4.26 |