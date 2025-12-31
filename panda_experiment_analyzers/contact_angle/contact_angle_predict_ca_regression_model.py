#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
import os
import matplotlib.pyplot as plt

from sklearn.preprocessing import StandardScaler, PolynomialFeatures
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline

FEATURES = ["s_red_px", "s_blue_px"]
TARGET = "theta_side_deg"  # optional in inputs for parity/residual plots

# ---------- math helpers ----------

def _expand_equation_original_units(pipeline: Pipeline, feature_names=FEATURES):
    scaler: StandardScaler = pipeline.named_steps["scaler"]
    poly: PolynomialFeatures = pipeline.named_steps["poly"]
    reg: LinearRegression = pipeline.named_steps["reg"]

    assert isinstance(scaler, StandardScaler)
    assert isinstance(poly, PolynomialFeatures) and poly.degree == 2 and not poly.include_bias
    assert isinstance(reg, LinearRegression)

    m1, m2 = scaler.mean_
    s1, s2 = scaler.scale_
    c1, c2, c11, c12, c22 = reg.coef_
    b = reg.intercept_

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
        f"y = {A:.6f}*{feature_names[0]}^2"
        f" + {B:.6f}*{feature_names[0]}*{feature_names[1]}"
        f" + {C:.6f}*{feature_names[1]}^2"
        f" + {D:.6f}*{feature_names[0]}"
        f" + {E:.6f}*{feature_names[1]}"
        f" + {F:.6f}"
    )
    return {"A_x1^2": A, "B_x1x2": B, "C_x2^2": C, "D_x1": D, "E_x2": E, "F_const": F}, eq

def _design_matrix(pipeline: Pipeline, X_raw: np.ndarray) -> np.ndarray:
    scaler: StandardScaler = pipeline.named_steps["scaler"]
    poly: PolynomialFeatures = pipeline.named_steps["poly"]
    Z = scaler.transform(X_raw)
    return poly.transform(Z)  # shape (n, 5) for your setup

def _intervals_linear(
    pipeline: Pipeline,
    X_train_raw: np.ndarray,
    y_train: np.ndarray,
    X_new_raw: np.ndarray,
    alpha: float,
    interval_type: str,  # "confidence" or "prediction"
):
    """Closed-form intervals for LinearRegression under the pipeline transforms."""
    from scipy.stats import t

    reg: LinearRegression = pipeline.named_steps["reg"]

    Xd_train = _design_matrix(pipeline, X_train_raw)         # (n, p)
    X_train = np.column_stack([np.ones(len(Xd_train)), Xd_train])  # add bias
    Xd_new = _design_matrix(pipeline, X_new_raw)
    X_new = np.column_stack([np.ones(len(Xd_new)), Xd_new])

    y_hat_train = pipeline.predict(X_train_raw)
    y_hat_new = pipeline.predict(X_new_raw)


    n, p_plus_1 = X_train.shape
    dof = max(n - p_plus_1, 1)

    residuals = y_train - y_hat_train
    RSS = float(np.dot(residuals, residuals))
    s2 = RSS / dof

    XtX_inv = np.linalg.inv(X_train.T @ X_train)
    leverages = np.einsum("ij,jk,ik->i", X_new, XtX_inv, X_new)

    if interval_type == "confidence":
        var_term = leverages                   # Var of mean prediction
    else:
        var_term = 1.0 + leverages            # Prediction interval adds noise

    se = np.sqrt(s2 * var_term)
    tcrit = t.ppf(1 - alpha / 2, dof)

    lower = y_hat_new - tcrit * se
    upper = y_hat_new + tcrit * se
    return y_hat_new, lower, upper

# ---------- plotting ----------

def _ensure_dir(path: str):
    Path(path).parent.mkdir(parents=True, exist_ok=True)

def _plot_pred_with_interval(y_pred, lo, hi, ids, outpath):
    # ids can be strings (e.g., Image); make x positions and label later
    x = np.arange(len(y_pred))
    yerr = np.vstack([y_pred - lo, hi - y_pred])

    plt.figure()
    plt.errorbar(x, y_pred, yerr=yerr, fmt='o', capsize=3)
    plt.xlabel("Sample index")
    plt.ylabel("Predicted θ (deg)")
    plt.title("Predicted Contact Angle with Interval")
    plt.tight_layout()
    _ensure_dir(outpath)
    plt.savefig(outpath, dpi=200)
    plt.close()

    # Also save a CSV pairing index->id for quick lookup
    if ids is not None:
        ixmap = pd.DataFrame({"index": x, "id": ids})
        Path(outpath).with_suffix(".index_map.csv").parent.mkdir(parents=True, exist_ok=True)
        ixmap.to_csv(Path(outpath).with_suffix(".index_map.csv"), index=False)

def _plot_parity_with_interval(y_true, y_pred, lo, hi, outpath):
    plt.figure()
    plt.scatter(y_true, y_pred, s=18)
    # Vertical error bars around prediction
    yerr = np.vstack([y_pred - lo, hi - y_pred])
    plt.errorbar(y_true, y_pred, yerr=yerr, fmt='none', elinewidth=1, capsize=2)
    lims = [min(y_true.min(), y_pred.min()), max(y_true.max(), y_pred.max())]
    plt.plot(lims, lims)
    plt.xlabel("True θ (deg)")
    plt.ylabel("Predicted θ (deg)")
    plt.title("Parity with Interval")
    plt.tight_layout()
    _ensure_dir(outpath)
    plt.savefig(outpath, dpi=200)
    plt.close()

def _plot_residuals(y_true, y_pred, out_scatter, out_hist):
    resid = y_true - y_pred

    plt.figure()
    plt.scatter(y_pred, resid, s=18)
    plt.axhline(0)
    plt.xlabel("Predicted θ (deg)")
    plt.ylabel("Residual (true - pred)")
    plt.title("Residuals vs Predicted")
    plt.tight_layout()
    _ensure_dir(out_scatter)
    plt.savefig(out_scatter, dpi=200)
    plt.close()

    plt.figure()
    plt.hist(resid, bins=30)
    plt.xlabel("Residual (true - pred)")
    plt.ylabel("Count")
    plt.title("Residuals Histogram")
    plt.tight_layout()
    _ensure_dir(out_hist)
    plt.savefig(out_hist, dpi=200)
    plt.close()

# ---------- prediction paths ----------

def predict_batch(model_path: str, in_csv: str, out_csv: str, show_equation: bool = False,
                  train_csv_for_intervals: str = None, alpha: float = 0.05,
                  interval_type: str = "prediction", plots_dir: str = None, id_column: str = "Image"):
    pipeline: Pipeline = joblib.load(model_path)

    df = pd.read_csv(in_csv)
    missing = [f for f in FEATURES if f not in df.columns]
    if missing:
        raise ValueError(f"Input CSV missing required columns: {missing}")

    X = df[FEATURES].values
    y_pred = pipeline.predict(X)

    df_out = df.copy()
    df_out["theta_pred_deg"] = y_pred

    # --- residuals: add when ground-truth is present ---
    if TARGET in df.columns:
        y_true = df[TARGET].to_numpy()
        resid = y_true - y_pred
        df_out["theta_resid_deg"] = resid
        df_out["theta_abs_resid_deg"] = np.abs(resid)

        # quick summary (optional but useful)
        bias = float(resid.mean())
        mae  = float(np.mean(np.abs(resid)))
        rmse = float(np.sqrt(np.mean(resid**2)))
        r2   = 1 - float(np.sum(resid**2) / np.sum((y_true - y_true.mean())**2))
        # N and Bland–Altman (95% limits of agreement)
        N = resid.size
        mu = float(resid.mean())                     # bias (mean residual)
        sigma = float(resid.std(ddof=1))             # sample SD
        loa_low  = mu - 1.96 * sigma
        loa_high = mu + 1.96 * sigma
        slope, intercept = np.polyfit(y_pred, resid, 1)

        print(f"[Trend] resid ~ fitted: slope={slope:.4f} deg/deg, intercept={intercept:.3f} deg")
        print(f"[Residuals] N={N} | bias={mu:.2f}° | MAE={mae:.2f}° | RMSE={rmse:.2f}° | R²={r2:.3f}")
        print(f"[Bland-Altman] mu={mu:.2f}°, sigma={sigma:.2f}° | 95% LoA: {loa_low:.2f}° to {loa_high:.2f}°")
        print(f"[Residuals] bias={bias:.2f}°, MAE={mae:.2f}°, RMSE={rmse:.2f}°, R²={r2:.3f}")

        thesis_line = (
            f"Calibration residuals (θ_true − θ_pred) showed bias = {mu:.1f}°, "
            f"RMSE = {rmse:.1f}°, MAE = {mae:.1f}° over n = {N} samples. "
            f"95% limits of agreement were μ ± 1.96σ = {mu:.1f}° ± 1.96·{sigma:.1f}° = "
            f"{loa_low:.1f}° to {loa_high:.1f}°."
        )
        print(thesis_line)
        
        # ensure folder exists and save a sidecar summary next to --out-csv
        Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
        Path(out_csv).with_suffix(".summary.txt").write_text(thesis_line + "\n", encoding="utf-8")
        print(f"Saved summary to: {Path(out_csv).with_suffix('.summary.txt')}")

    have_intervals = False
    lo = hi = None


    if train_csv_for_intervals:
        train_df = pd.read_csv(train_csv_for_intervals).dropna(subset=FEATURES + [TARGET])
        Xtr = train_df[FEATURES].values
        ytr = train_df[TARGET].values

        # Reuse your private helpers to get design matrices
        Xd_train = _design_matrix(pipeline, Xtr)
        X_train  = np.column_stack([np.ones(len(Xd_train)), Xd_train])  # add bias term
        Xd_new   = _design_matrix(pipeline, X)
        X_new    = np.column_stack([np.ones(len(Xd_new)), Xd_new])

        # Fit-space stats (match _intervals_linear)
        # After you've loaded train_df and built Xtr, ytr, and have pipeline fitted
        y_hat_train = pipeline.predict(Xtr)
        resid_train = ytr - y_hat_train
        N = resid_train.size
        bias = float(resid_train.mean())
        mae  = float(np.mean(np.abs(resid_train)))
        rmse = float(np.sqrt(np.mean(resid_train**2)))
        sigma = float(resid_train.std(ddof=1))
        loa_low, loa_high = bias - 1.96 * sigma, bias + 1.96 * sigma
        print(f"[Calibration residuals] N={N} | bias={bias:.2f}° | MAE={mae:.2f}° | RMSE={rmse:.2f}°")
        print(f"[Calibration LoA] mu={bias:.2f}°, sigma={sigma:.2f}° | 95% LoA: {loa_low:.2f}° to {loa_high:.2f}°")
            # --- Thesis-ready summary line from calibration file ---
        thesis_line_cal = (
            f"Calibration residuals (θ_true − θ_pred) showed bias = {bias:.1f}°, "
            f"RMSE = {rmse:.1f}°, MAE = {mae:.1f}° over n = {N} samples. "
            f"95% limits of agreement were μ ± 1.96σ = {bias:.1f}° ± 1.96·{sigma:.1f}° = "
            f"{loa_low:.1f}° to {loa_high:.1f}°."
        )
        print(thesis_line_cal)
        # ensure folder exists and save a sidecar summary next to --out-csv
        Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
        Path(out_csv).with_suffix(".summary.txt").write_text(thesis_line_cal + "\n", encoding="utf-8")
        print(f"Saved summary to: {Path(out_csv).with_suffix('.summary.txt')}")


        
        n, p_plus_1 = X_train.shape
        dof = max(n - p_plus_1, 1)
        RSS = float(np.dot(resid_train, resid_train))
        s2  = RSS / dof
        XtX_inv = np.linalg.inv(X_train.T @ X_train)

        # Leverage for each new row
        h_new = np.einsum("ij,jk,ik->i", X_new, XtX_inv, X_new)

        # 95% intervals as before
        _, lo, hi = _intervals_linear(
            pipeline, Xtr, ytr, X, alpha=alpha, interval_type=interval_type
        )
        tag = f"{int((1-alpha)*100)}_{interval_type[:3]}"
        have_intervals = True
        df_out[f"theta_lo_{tag}"] = lo
        df_out[f"theta_hi_{tag}"] = hi
        

        # Standardized and PRESS/LOO residuals when ground-truth exists
        if TARGET in df.columns:
            s = np.sqrt(s2)
            # guard against numeric issues if any h is ~1
            denom = np.sqrt(np.maximum(1e-12, 1 - h_new))
            std_resid  = resid / (s * denom)
            loo_resid  = resid / np.maximum(1e-12, (1 - h_new))
            df_out["theta_std_resid"] = std_resid
            df_out["theta_loo_resid"] = loo_resid


    Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
    df_out.to_csv(out_csv, index=False)
    print(f"Saved predictions to: {out_csv}")

    if show_equation:
        coefs, eq = _expand_equation_original_units(pipeline, FEATURES)
        print("\nExplicit quadratic in ORIGINAL units:")
        print("  " + eq)
        print("Coefficients:", {k: float(v) for k, v in coefs.items()})

    # ---- plots ----
    if plots_dir:
        os.makedirs(plots_dir, exist_ok=True)
        ids = df[id_column].astype(str) if id_column in df.columns else None

        if have_intervals:
            _plot_pred_with_interval(y_pred, lo, hi, ids, os.path.join(plots_dir, "pred_with_interval.png"))

        # If ground-truth exists in the input, add parity/residual plots
        if TARGET in df.columns:
            y_true = df[TARGET].values
            if have_intervals:
                _plot_parity_with_interval(y_true, y_pred, lo, hi, os.path.join(plots_dir, "parity_with_interval.png"))
            _plot_residuals(y_true, y_pred,
                            os.path.join(plots_dir, "residuals_vs_pred.png"),
                            os.path.join(plots_dir, "residuals_hist.png"))

def predict_point(model_path: str, s_red: float, s_blue: float, show_equation: bool = False,
                  train_csv_for_intervals: str = None, alpha: float = 0.05, interval_type: str = "prediction"):
    pipeline: Pipeline = joblib.load(model_path)
    X = np.array([[s_red, s_blue]], dtype=float)
    y_hat = pipeline.predict(X)[0]

    msg = f"Prediction θ ≈ {y_hat:.3f}°  (s_red_px={s_red}, s_blue_px={s_blue})"
    if train_csv_for_intervals:
        train_df = pd.read_csv(train_csv_for_intervals).dropna(subset=FEATURES + [TARGET])
        Xtr = train_df[FEATURES].values
        ytr = train_df[TARGET].values
        _, lo, hi = _intervals_linear(
            pipeline, Xtr, ytr, X, alpha=alpha, interval_type=interval_type
        )
        tag = f"{int((1-alpha)*100)}% {interval_type}"
        msg += f"  |  {tag}: [{lo[0]:.3f}, {hi[0]:.3f}]"

    print(msg)

    if show_equation:
        coefs, eq = _expand_equation_original_units(pipeline, FEATURES)
        print("\nExplicit quadratic in ORIGINAL units:")
        print("  " + eq)
        print("Coefficients:", {k: float(v) for k, v in coefs.items()})

# ---------- CLI ----------

def main():
    p = argparse.ArgumentParser(
        description="Predict contact angle (deg) from s_red_px and s_blue_px using a saved polynomial pipeline."
    )
    p.add_argument("--model", required=True, help="Path to saved joblib model (.pkl)")
    sub = p.add_subparsers(dest="mode", required=True)

    # Batch mode
    b = sub.add_parser("batch", help="Batch predict from CSV")
    b.add_argument("--in-csv", required=True, help="Input CSV with columns: s_red_px, s_blue_px (and optional Image)")
    b.add_argument("--out-csv", required=True, help="Output CSV path")
    b.add_argument("--show-equation", action="store_true", help="Print explicit quadratic in original units")
    b.add_argument("--train-csv-for-intervals", default=None,
                   help="Training CSV used to compute intervals (required for CI/PI)")
    b.add_argument("--alpha", type=float, default=0.05, help="Alpha (0.05 => 95% interval)")
    b.add_argument("--interval-type", choices=["confidence", "prediction"], default="prediction",
                   help="Interval type (default: prediction)")
    b.add_argument("--plots-dir", default=None, help="Directory to save plots")
    b.add_argument("--id-column", default="Image",
                   help="Column name to use as ID labels in index map (default: Image)")

    # Single-point mode
    s = sub.add_parser("point", help="Predict for a single point")
    s.add_argument("--s-red", type=float, required=True, help="s_red_px")
    s.add_argument("--s-blue", type=float, required=True, help="s_blue_px")
    s.add_argument("--show-equation", action="store_true", help="Print explicit quadratic in original units")
    s.add_argument("--train-csv-for-intervals", default=None,
                   help="Training CSV used to compute intervals (required for CI/PI)")
    s.add_argument("--alpha", type=float, default=0.05, help="Alpha (0.05 => 95% interval)")
    s.add_argument("--interval-type", choices=["confidence", "prediction"], default="prediction",
                   help="Interval type (default: prediction)")

    args = p.parse_args()

    try:
        if args.mode == "batch":
            predict_batch(
                model_path=args.model,
                in_csv=args.in_csv,
                out_csv=args.out_csv,
                show_equation=args.show_equation,
                train_csv_for_intervals=args.train_csv_for_intervals,
                alpha=args.alpha,
                interval_type=args.interval_type,
                plots_dir=args.plots_dir,
                id_column=args.id_column,
            )
        else:
            predict_point(
                model_path=args.model,
                s_red=args.s_red,
                s_blue=args.s_blue,
                show_equation=args.show_equation,
                train_csv_for_intervals=args.train_csv_for_intervals,
                alpha=args.alpha,
                interval_type=args.interval_type,
            )
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

# Example usage - see README.md for detailed documentation