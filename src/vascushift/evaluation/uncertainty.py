"""
Statistical uncertainty and confidence interval estimation.
"""

from typing import Tuple
import numpy as np


def bootstrap_confidence_interval(
    values: np.ndarray,
    n_bootstraps: int = 1000,
    alpha: float = 0.05,
    seed: int = 42,
) -> Tuple[float, float, float]:
    """
    Computes empirical bootstrap (1 - alpha) confidence interval.

    Returns:
        (mean, ci_lower, ci_upper)
    """
    v = np.asarray(values, dtype=float)
    v = v[~np.isnan(v)]
    if len(v) == 0:
        return np.nan, np.nan, np.nan
    if len(v) == 1:
        return float(v[0]), float(v[0]), float(v[0])

    rng = np.random.RandomState(seed)
    boot_means = []
    n = len(v)
    for _ in range(n_bootstraps):
        sample = rng.choice(v, size=n, replace=True)
        boot_means.append(np.mean(sample))

    ci_low = float(np.percentile(boot_means, 100.0 * (alpha / 2.0)))
    ci_high = float(np.percentile(boot_means, 100.0 * (1.0 - alpha / 2.0)))
    return float(np.mean(v)), ci_low, ci_high

