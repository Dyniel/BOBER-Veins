# Scientific Evaluation Protocol: VascuShift-GPINN

## 1. Grouped Data Partitioning & Leakage Prevention
In small-sample physiological research ($N = 9$ human participants), random sample-level cross-validation creates severe data leakage: within-subject correlation causes models to memorize individual baseline vessel sizes rather than learning gravitational hemodynamics.

To guarantee zero participant leakage:
1. **Leave-One-Subject-Out (LOSO) Validation**:
   - $K = 9$ folds.
   - For fold $i \in \{1, \dots, 9\}$, all measurements from participant $i$ are held out as the test set ($N_{test} = 5$ gravity conditions).
   - Training is performed exclusively on the remaining 8 subjects ($N_{train} = 40$ samples).
2. **Strictly Matched Partitions**:
   - All models (Baseline 0, Baseline 1a, Baseline 1b, Baseline 2, Model 3a, Model 3b) are evaluated on the exact same 9 folds.
   - No test set observations are ever used to normalize or scale inputs.

---

## 2. Quantitative Performance Metrics
1. **Mean Absolute Error (MAE)**:
   $$\text{MAE} = \frac{1}{N} \sum_{i=1}^N |\hat{y}_i - y_i|$$
2. **Root Mean Squared Error (RMSE)**:
   $$\text{RMSE} = \sqrt{\frac{1}{N} \sum_{i=1}^N (\hat{y}_i - y_i)^2}$$
3. **Coefficient of Determination ($R^2$)**:
   $$R^2 = 1 - \frac{\sum (\hat{y}_i - y_i)^2}{\sum (y_i - \bar{y})^2}$$
4. **Physical Constraint Violations**:
   - Bounds: $\hat{A}_j \notin [2.0, 250.0]\text{ mm}^2$ or $\hat{P}_j < 0$.
   - Monotonicity: for upright posture, $\hat{A}_j(g_{z, high}) > \hat{A}_j(g_{z, low})$.
5. **Relative Improvement over Baseline 0**:
   $$\Delta \text{Err} = \frac{\text{MAE}_{baseline0} - \text{MAE}_{model}}{\text{MAE}_{baseline0}} \times 100\%$$

---

## 3. Optical rPPG Benchmark Protocol
Evaluated across an independent benchmark cohort ($N = 12$ sessions):
- **Metrics**:
  - Heart Rate MAE in BPM
  - Heart Rate RMSE in BPM
  - Pearson correlation coefficient $r$
  - Spectral Signal-to-Noise Ratio (SNR) in dB
  - Valid window coverage ($\%$) using clinical threshold $\text{SNR} \ge -3.0\text{ dB}$.

