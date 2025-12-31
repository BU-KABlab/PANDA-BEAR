#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Contact Angle Polynomial Regression Model Training
---------------------------------------------------
Author: Harley Quinn
Date Created: 2025-07-11

This script trains a polynomial regression model to predict contact angle (θ)
from LED reflection distances (s_red_px, s_blue_px).

The model uses:
- StandardScaler: Normalizes input features
- PolynomialFeatures: Creates quadratic terms (degree=2)
- LinearRegression: Fits the polynomial surface

Usage:
    python contact_angle_train_regression_model.py \\
        --train-csv training_data.csv \\
        --out-model contact_angle_poly_model.pkl \\
        --plots-dir ./training_plots

Required CSV columns:
    - s_red_px: Red LED pair separation (pixels)
    - s_blue_px: Blue LED pair separation (pixels)
    - theta_side_deg: Ground truth contact angle (degrees)
"""

import argparse
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
import matplotlib.pyplot as plt

from sklearn.preprocessing import StandardScaler, PolynomialFeatures
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import cross_val_score, LeaveOneOut

FEATURES = ["s_red_px", "s_blue_px"]
TARGET = "theta_side_deg"


def load_training_data(csv_path: str) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    """Load and validate training data from CSV."""
    df = pd.read_csv(csv_path)
    
    # Check required columns
    missing = [c for c in FEATURES + [TARGET] if c not in df.columns]
    if missing:
        raise ValueError(f"Training CSV missing required columns: {missing}")
    
    # Drop rows with NaN in required columns
    df_clean = df.dropna(subset=FEATURES + [TARGET]).copy()
    n_dropped = len(df) - len(df_clean)
    if n_dropped > 0:
        print(f"[INFO] Dropped {n_dropped} rows with missing values")
    
    X = df_clean[FEATURES].values
    y = df_clean[TARGET].values
    
    print(f"[INFO] Loaded {len(X)} training samples")
    print(f"       s_red_px range: [{X[:, 0].min():.1f}, {X[:, 0].max():.1f}]")
    print(f"       s_blue_px range: [{X[:, 1].min():.1f}, {X[:, 1].max():.1f}]")
    print(f"       theta range: [{y.min():.1f}°, {y.max():.1f}°]")
    
    return df_clean, X, y


def build_pipeline(degree: int = 2) -> Pipeline:
    """Build the polynomial regression pipeline."""
    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("poly", PolynomialFeatures(degree=degree, include_bias=False)),
        ("reg", LinearRegression()),
    ])
    return pipeline


def expand_equation_original_units(pipeline: Pipeline, feature_names=FEATURES) -> tuple[dict, str]:
    """
    Expand the fitted polynomial to an equation in original (unscaled) units.
    
    For degree=2 with 2 features, the polynomial terms are:
    [x1, x2, x1^2, x1*x2, x2^2]
    """
    scaler: StandardScaler = pipeline.named_steps["scaler"]
    poly: PolynomialFeatures = pipeline.named_steps["poly"]
    reg: LinearRegression = pipeline.named_steps["reg"]

    m1, m2 = scaler.mean_
    s1, s2 = scaler.scale_
    
    # Coefficients for [x1, x2, x1^2, x1*x2, x2^2]
    c1, c2, c11, c12, c22 = reg.coef_
    b = reg.intercept_

    # Transform to original units
    A = c11 / (s1**2)
    B = c12 / (s1 * s2)
    C = c22 / (s2**2)
    D = (c1 / s1) - (2 * c11 * m1 / (s1**2)) - (c12 * m2 / (s1 * s2))
    E = (c2 / s2) - (2 * c22 * m2 / (s2**2)) - (c12 * m1 / (s1 * s2))
    F = (
        b
        - c1 * m1 / s1
        - c2 * m2 / s2
        + c11 * (m1**2) / (s1**2)
        + c12 * (m1 * m2) / (s1 * s2)
        + c22 * (m2**2) / (s2**2)
    )
    
    eq = (
        f"θ = {A:.6f}*{feature_names[0]}² "
        f"+ {B:.6f}*{feature_names[0]}*{feature_names[1]} "
        f"+ {C:.6f}*{feature_names[1]}² "
        f"+ {D:.6f}*{feature_names[0]} "
        f"+ {E:.6f}*{feature_names[1]} "
        f"+ {F:.6f}"
    )
    
    coefficients = {
        "A_x1^2": A, 
        "B_x1x2": B, 
        "C_x2^2": C, 
        "D_x1": D, 
        "E_x2": E, 
        "F_const": F
    }
    
    return coefficients, eq


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """Compute regression metrics."""
    residuals = y_true - y_pred
    n = len(y_true)
    
    bias = float(residuals.mean())
    mae = float(np.mean(np.abs(residuals)))
    rmse = float(np.sqrt(np.mean(residuals**2)))
    ss_res = float(np.sum(residuals**2))
    ss_tot = float(np.sum((y_true - y_true.mean())**2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    
    # Bland-Altman limits of agreement
    sigma = float(residuals.std(ddof=1))
    loa_low = bias - 1.96 * sigma
    loa_high = bias + 1.96 * sigma
    
    return {
        "n": n,
        "bias": bias,
        "mae": mae,
        "rmse": rmse,
        "r2": r2,
        "sigma": sigma,
        "loa_low": loa_low,
        "loa_high": loa_high,
    }


def plot_parity(y_true, y_pred, out_path: str, title: str = "Parity Plot"):
    """Create parity plot (predicted vs actual)."""
    plt.figure(figsize=(6, 6))
    plt.scatter(y_true, y_pred, s=40, alpha=0.7, edgecolors='white', linewidths=0.5)
    
    # Perfect prediction line
    lims = [min(y_true.min(), y_pred.min()) - 5, max(y_true.max(), y_pred.max()) + 5]
    plt.plot(lims, lims, 'k--', lw=1, label='Perfect prediction')
    
    # Metrics annotation
    metrics = compute_metrics(y_true, y_pred)
    text = f"R² = {metrics['r2']:.3f}\nRMSE = {metrics['rmse']:.2f}°\nMAE = {metrics['mae']:.2f}°"
    plt.annotate(text, xy=(0.05, 0.95), xycoords='axes fraction', 
                 fontsize=10, verticalalignment='top',
                 bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    plt.xlabel("True Contact Angle θ (deg)")
    plt.ylabel("Predicted Contact Angle θ (deg)")
    plt.title(title)
    plt.xlim(lims)
    plt.ylim(lims)
    plt.tight_layout()
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=200)
    plt.close()
    print(f"[PLOT] Saved parity plot: {out_path}")


def plot_residuals(y_true, y_pred, out_path: str):
    """Create residual plots."""
    residuals = y_true - y_pred
    
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    
    # Residuals vs predicted
    axes[0].scatter(y_pred, residuals, s=40, alpha=0.7, edgecolors='white', linewidths=0.5)
    axes[0].axhline(0, color='k', linestyle='--', lw=1)
    axes[0].set_xlabel("Predicted θ (deg)")
    axes[0].set_ylabel("Residual (True - Predicted)")
    axes[0].set_title("Residuals vs Predicted")
    
    # Histogram of residuals
    axes[1].hist(residuals, bins=15, edgecolor='white', alpha=0.7)
    axes[1].axvline(0, color='k', linestyle='--', lw=1)
    axes[1].set_xlabel("Residual (deg)")
    axes[1].set_ylabel("Count")
    axes[1].set_title("Residual Distribution")
    
    # Add statistics
    metrics = compute_metrics(y_true, y_pred)
    text = f"μ = {metrics['bias']:.2f}°\nσ = {metrics['sigma']:.2f}°"
    axes[1].annotate(text, xy=(0.95, 0.95), xycoords='axes fraction',
                     fontsize=10, verticalalignment='top', horizontalalignment='right',
                     bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    plt.tight_layout()
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=200)
    plt.close()
    print(f"[PLOT] Saved residual plots: {out_path}")


def plot_surface(pipeline, X, y, out_path: str, grid_size: int = 100):
    """Create 3D surface plot of the polynomial model."""
    try:
        from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
    except ImportError:
        print("[WARN] 3D plotting not available, skipping surface plot")
        return
    
    # Create grid
    x1_range = np.linspace(X[:, 0].min() - 5, X[:, 0].max() + 5, grid_size)
    x2_range = np.linspace(X[:, 1].min() - 5, X[:, 1].max() + 5, grid_size)
    X1, X2 = np.meshgrid(x1_range, x2_range)
    
    # Predict on grid
    grid_points = np.c_[X1.ravel(), X2.ravel()]
    Z = pipeline.predict(grid_points).reshape(X1.shape)
    
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    
    # Surface
    surf = ax.plot_surface(X1, X2, Z, alpha=0.6, cmap='viridis', edgecolor='none')
    
    # Training points
    ax.scatter(X[:, 0], X[:, 1], y, c='red', s=50, edgecolors='white', linewidths=0.5, label='Training data')
    
    ax.set_xlabel('s_red_px')
    ax.set_ylabel('s_blue_px')
    ax.set_zlabel('θ (deg)')
    ax.set_title('Polynomial Regression Surface')
    
    fig.colorbar(surf, ax=ax, shrink=0.5, aspect=10, label='θ (deg)')
    
    plt.tight_layout()
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=200)
    plt.close()
    print(f"[PLOT] Saved surface plot: {out_path}")


def train_model(
    train_csv: str,
    out_model: str,
    degree: int = 2,
    plots_dir: str = None,
    show_equation: bool = True,
    cv_folds: int = 5,
) -> Pipeline:
    """
    Train the polynomial regression model.
    
    Args:
        train_csv: Path to training CSV
        out_model: Path to save the trained model (.pkl)
        degree: Polynomial degree (default: 2)
        plots_dir: Directory for training plots (optional)
        show_equation: Print the explicit polynomial equation
        cv_folds: Number of cross-validation folds (0 to skip CV)
    
    Returns:
        Trained Pipeline object
    """
    # Load data
    df, X, y = load_training_data(train_csv)
    
    # Build and fit pipeline
    pipeline = build_pipeline(degree=degree)
    pipeline.fit(X, y)
    
    # Training predictions
    y_pred = pipeline.predict(X)
    metrics = compute_metrics(y, y_pred)
    
    print("\n" + "=" * 60)
    print("TRAINING RESULTS")
    print("=" * 60)
    print(f"  Samples:      {metrics['n']}")
    print(f"  R²:           {metrics['r2']:.4f}")
    print(f"  RMSE:         {metrics['rmse']:.3f}°")
    print(f"  MAE:          {metrics['mae']:.3f}°")
    print(f"  Bias (mean):  {metrics['bias']:.3f}°")
    print(f"  Std Dev:      {metrics['sigma']:.3f}°")
    print(f"  95% LoA:      [{metrics['loa_low']:.2f}°, {metrics['loa_high']:.2f}°]")
    
    # Cross-validation
    if cv_folds > 0 and len(X) >= cv_folds:
        print(f"\n{cv_folds}-Fold Cross-Validation:")
        cv_pipeline = build_pipeline(degree=degree)
        cv_scores = cross_val_score(cv_pipeline, X, y, cv=cv_folds, scoring='neg_root_mean_squared_error')
        cv_rmse = -cv_scores
        print(f"  CV RMSE:      {cv_rmse.mean():.3f}° ± {cv_rmse.std():.3f}°")
        print(f"  CV folds:     {cv_rmse}")
    
    # Leave-one-out cross-validation for small datasets
    if len(X) <= 30:
        print("\nLeave-One-Out Cross-Validation:")
        loo = LeaveOneOut()
        loo_pipeline = build_pipeline(degree=degree)
        loo_scores = cross_val_score(loo_pipeline, X, y, cv=loo, scoring='neg_root_mean_squared_error')
        loo_rmse = -loo_scores
        print(f"  LOO RMSE:     {loo_rmse.mean():.3f}° ± {loo_rmse.std():.3f}°")
    
    # Show equation
    if show_equation:
        coeffs, eq = expand_equation_original_units(pipeline, FEATURES)
        print("\n" + "-" * 60)
        print("POLYNOMIAL EQUATION (original units):")
        print("-" * 60)
        print(f"  {eq}")
        print("\nCoefficients:")
        for k, v in coeffs.items():
            print(f"  {k}: {v:.8f}")
    
    # Save model
    Path(out_model).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, out_model)
    print(f"\n[SAVED] Model saved to: {out_model}")
    
    # Generate plots
    if plots_dir:
        plots_dir = Path(plots_dir)
        plots_dir.mkdir(parents=True, exist_ok=True)
        
        plot_parity(y, y_pred, str(plots_dir / "parity_plot.png"), "Training Parity Plot")
        plot_residuals(y, y_pred, str(plots_dir / "residual_plots.png"))
        plot_surface(pipeline, X, y, str(plots_dir / "surface_plot.png"))
        
        # Save training summary
        summary_path = plots_dir / "training_summary.txt"
        with open(summary_path, "w") as f:
            f.write("Contact Angle Polynomial Regression Model\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Training data: {train_csv}\n")
            f.write(f"Samples: {metrics['n']}\n")
            f.write(f"Polynomial degree: {degree}\n\n")
            f.write("Metrics:\n")
            f.write(f"  R²:    {metrics['r2']:.4f}\n")
            f.write(f"  RMSE:  {metrics['rmse']:.3f}°\n")
            f.write(f"  MAE:   {metrics['mae']:.3f}°\n")
            f.write(f"  Bias:  {metrics['bias']:.3f}°\n")
            f.write(f"  95% LoA: [{metrics['loa_low']:.2f}°, {metrics['loa_high']:.2f}°]\n\n")
            if show_equation:
                _, eq = expand_equation_original_units(pipeline, FEATURES)
                f.write(f"Equation:\n  {eq}\n")
        print(f"[SAVED] Training summary: {summary_path}")
    
    print("\n" + "=" * 60)
    
    return pipeline


def main():
    parser = argparse.ArgumentParser(
        description="Train a polynomial regression model for contact angle prediction.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Basic training
    python contact_angle_train_regression_model.py \\
        --train-csv calibration_data.csv \\
        --out-model contact_angle_poly_model.pkl

    # With plots and cross-validation
    python contact_angle_train_regression_model.py \\
        --train-csv calibration_data.csv \\
        --out-model contact_angle_poly_model.pkl \\
        --plots-dir ./training_plots \\
        --cv-folds 5 \\
        --show-equation

Required CSV columns:
    s_red_px      - Red LED pair separation (pixels)
    s_blue_px     - Blue LED pair separation (pixels)  
    theta_side_deg - Ground truth contact angle (degrees)
        """
    )
    
    parser.add_argument("--train-csv", required=True, 
                        help="Path to training CSV with s_red_px, s_blue_px, theta_side_deg")
    parser.add_argument("--out-model", required=True,
                        help="Path to save trained model (.pkl)")
    parser.add_argument("--degree", type=int, default=2,
                        help="Polynomial degree (default: 2)")
    parser.add_argument("--plots-dir", default=None,
                        help="Directory to save training plots")
    parser.add_argument("--show-equation", action="store_true",
                        help="Print explicit polynomial equation in original units")
    parser.add_argument("--cv-folds", type=int, default=5,
                        help="Number of cross-validation folds (0 to skip, default: 5)")
    
    args = parser.parse_args()
    
    try:
        train_model(
            train_csv=args.train_csv,
            out_model=args.out_model,
            degree=args.degree,
            plots_dir=args.plots_dir,
            show_equation=args.show_equation,
            cv_folds=args.cv_folds,
        )
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

