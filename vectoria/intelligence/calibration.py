"""
Confidence Calibration Module (Refinement 2).

Computes Expected Calibration Error (ECE) and confidence intervals comparing predicted confidence vs actual accuracy.
"""

from typing import List, Tuple
import numpy as np


class ConfidenceCalibrator:
    """Calculates ECE metric over confidence predictions and correctness binary labels."""

    def compute_ece(self, confidences: List[float], accuracies: List[bool], num_bins: int = 10) -> float:
        if not confidences or len(confidences) != len(accuracies):
            return 0.0

        confs = np.array(confidences)
        accs = np.array(accuracies, dtype=float)

        bin_boundaries = np.linspace(0, 1, num_bins + 1)
        ece = 0.0

        for i in range(num_bins):
            bin_lower = bin_boundaries[i]
            bin_upper = bin_boundaries[i + 1]

            in_bin = (confs > bin_lower) & (confs <= bin_upper)
            bin_size = np.sum(in_bin)

            if bin_size > 0:
                avg_confidence_in_bin = np.mean(confs[in_bin])
                avg_accuracy_in_bin = np.mean(accs[in_bin])
                ece += (bin_size / len(confs)) * np.abs(avg_confidence_in_bin - avg_accuracy_in_bin)

        return float(ece)
