"""
Visualization tools for PEDOT optimization results.

This module creates clear, informative plots to help understand:
1. Where the model thinks the best parameters might be
2. How confident it is about different regions
3. What performance it expects across parameter combinations

The plots use color gradients where:
- Brighter/warmer colors usually indicate better or more interesting regions
- Darker/cooler colors usually indicate less promising regions
"""

from pathlib import Path
from typing import Sequence, Tuple

import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import griddata


class PEDOTVisualizer:
    """
    Creates visualization plots for PEDOT optimization results.

    Generates three types of plots:
    1. Expected Improvement: Where to look for better results
       - Brighter areas suggest more promising parameters to try
       - Considers both predicted performance and uncertainty

    2. Uncertainty: How confident the model is
       - Brighter areas show where the model is less certain
       - Useful for identifying regions needing more experiments

    3. ΔE₀₀ Predictions: Expected performance
       - Brighter areas indicate better predicted performance
       - Shows the model's best guess at each parameter combination
    """

    def __init__(self, figsize: Tuple[int, int] = (18, 5)):
        self.figsize = figsize

    def create_contour_plots(
        self,
        voltage_values: np.ndarray,
        time_values: np.ndarray,
        ei_values: np.ndarray,
        std_dev_values: np.ndarray,
        mean_values: np.ndarray,
        concentration: float,
        resolution: int = 300,
    ) -> plt.Figure:
        """
        Create three contour plots: Expected Improvement, Uncertainty, and ΔE₀₀.

        Args:
            voltage_values: Array of voltage values
            time_values: Array of time values
            ei_values: Expected improvement values
            std_dev_values: Standard deviation values
            mean_values: Mean prediction values
            concentration: EDOT concentration for plot titles
            resolution: Number of points for interpolation grid

        Returns:
            matplotlib Figure object
        """
        fig, axes = plt.subplots(nrows=1, ncols=3, figsize=self.figsize)

        # Create interpolation grid
        voltage_range = np.linspace(
            np.min(voltage_values), np.max(voltage_values), resolution
        )
        time_range = np.linspace(np.min(time_values), np.max(time_values), resolution)
        voltage_grid, time_grid = np.meshgrid(voltage_range, time_range)

        # Generate interpolated grids
        grids = self._interpolate_values(
            voltage_values,
            time_values,
            [ei_values, std_dev_values, mean_values],
            voltage_grid,
            time_grid,
        )

        # Plot each metric
        titles = [
            f"Expected Improvement {concentration} M",
            f"Uncertainty {concentration} M",
            f"ΔE₀₀ {concentration} M",
        ]

        for ax, grid, title in zip(axes, grids, titles):
            contour = ax.contourf(
                voltage_grid, time_grid, grid, levels=50, cmap="viridis"
            )
            plt.colorbar(contour, ax=ax)
            ax.set_title(title)
            ax.set_xlabel("Voltage (scaled)")
            ax.set_ylabel("Time (scaled)")

        plt.tight_layout()
        return fig

    @staticmethod
    def _interpolate_values(
        x: np.ndarray,
        y: np.ndarray,
        values: Sequence[np.ndarray],
        grid_x: np.ndarray,
        grid_y: np.ndarray,
    ) -> Sequence[np.ndarray]:
        """Interpolate multiple value arrays onto a common grid."""
        return [griddata((x, y), v, (grid_x, grid_y), method="cubic") for v in values]

    def save_plots(
        self, fig: plt.Figure, base_path: str, formats: Sequence[str] = ("svg", "png")
    ) -> Tuple[Path, ...]:
        """
        Save plots in multiple formats.

        Returns:
            Tuple of paths where plots were saved
        """
        paths = []
        for fmt in formats:
            path = Path(f"{base_path}.{fmt}")
            fig.savefig(path)
            paths.append(path)
        return tuple(paths)
