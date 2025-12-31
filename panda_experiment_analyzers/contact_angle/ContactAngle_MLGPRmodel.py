#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
    
from sklearn.preprocessing import StandardScaler
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel, ConstantKernel
from scipy.stats import norm


# -----------------------
# Core GP + BO utilities
# -----------------------

def load_xy(csv_path, x_cols=("concentration", "potential"), y_col="redplusblue"):
    df = pd.read_csv(csv_path)
    cols = list(x_cols) + [y_col]
    d = df[cols].dropna().copy()
    X = d[list(x_cols)].to_numpy(dtype=float)
    y = d[y_col].to_numpy(dtype=float)
    return df, X, y

def fit_gpr(X, y, random_state=42):
    # Scale X only (GPR has normalize_y for y)
    x_scaler = StandardScaler().fit(X)
    Xs = x_scaler.transform(X)

    # Kernel: C * Matern(ν=2.5) + White noise


    kernel = (
        ConstantKernel(1.0, (1e-3, 1e3))
        * RBF(length_scale=np.ones(X.shape[1]),
            length_scale_bounds=(0.5, 50.0))   # <-- RBF instead of Matern
        + WhiteKernel(noise_level=1e-2,
                    noise_level_bounds=(1e-6, 1.0))
    )




    gpr = GaussianProcessRegressor(
        kernel=kernel,
        alpha=0.0,               # handled by WhiteKernel
        normalize_y=True,        # center/scale y internally for stability
        n_restarts_optimizer=8,
        random_state=random_state,
    ).fit(Xs, y)

    return x_scaler, gpr

def ei_minimization(mu, sigma, f_best, xi=0.01):
    # Expected Improvement for *minimization*
    # improvement = f_best - mu - xi
    # EI = improvement * Phi(Z) + sigma * phi(Z), with Z = improvement / sigma
    eps = 1e-12
    sigma = np.maximum(sigma, eps)
    improv = f_best - mu - xi
    Z = improv / sigma
    ei = improv * norm.cdf(Z) + sigma * norm.pdf(Z)
    ei[sigma < eps] = 0.0
    return np.maximum(ei, 0.0)

def propose_candidates(x_scaler, gpr, bounds, y_orig, k=5, xi=0.01, n_random=5000, min_dist_norm=0.2, random_state=42):
    """
    Propose K diverse candidates maximizing EI (minimization).
    - bounds: [(x1_min, x1_max), (x2_min, x2_max)]
    - Diversity via simple exclusion radius in normalized space.
    """
    rng = np.random.default_rng(random_state)
    low = np.array([b[0] for b in bounds], dtype=float)
    high = np.array([b[1] for b in bounds], dtype=float)

    X_rand = rng.uniform(low=low, high=high, size=(n_random, len(bounds)))
    Xs = x_scaler.transform(X_rand)

    mu, sigma = gpr.predict(Xs, return_std=True)    # μ, σ in ORIGINAL y units
    f_best = float(np.min(y_orig))                   # <— ORIGINAL y units (critical)
    ei = ei_minimization(mu, sigma, f_best=f_best, xi=xi)

    # Greedy selection with distance-based diversity in normalized space
    chosen = []
    mask = np.ones(len(X_rand), dtype=bool)
    while len(chosen) < k and np.any(mask):
        idx = np.argmax(ei * mask)
        if ei[idx] <= 0:
            break
        chosen.append(idx)
        # Exclude neighbors within radius in normalized space
        d2 = np.sum((Xs - Xs[idx])**2, axis=1)
        mask = mask & (d2 > (min_dist_norm ** 2))

    X_next = X_rand[chosen]
    mu_next = mu[chosen]
    sigma_next = sigma[chosen]
    ei_next = ei[chosen]

    return X_next, mu_next, sigma_next, ei_next

# -----------------------
# Bounds helpers
# -----------------------

def infer_bounds_from_data(X, pad_frac=0.05, hard_bounds=None):
    """
    Infer rectangular bounds from data with a small padding.
    Optionally clip to hard_bounds=[(min1,max1),(min2,max2)] if provided.
    """
    x_min = X.min(axis=0)
    x_max = X.max(axis=0)
    span = x_max - x_min
    pad = pad_frac * np.where(span > 0, span, 1.0)
    lo = x_min - pad
    hi = x_max + pad
    if hard_bounds is not None:
        lo = np.maximum(lo, [hb[0] for hb in hard_bounds])
        hi = np.minimum(hi, [hb[1] for hb in hard_bounds])
    return list(zip(lo.tolist(), hi.tolist()))

# -----------------------
# Visualization (optional)
# -----------------------

def plot_surrogate_mean(df_all, x_scaler, gpr, bounds,
                        x_cols=("concentration","potential"),
                        y_col_pred="redplusblue",
                        grid_size=200, out_png=None, title=None):
    # Regular grid
    x1 = np.linspace(bounds[0][0], bounds[0][1], grid_size)
    x2 = np.linspace(bounds[1][0], bounds[1][1], grid_size)
    X1g, X2g = np.meshgrid(x1, x2)
    grid = np.c_[X1g.ravel(), X2g.ravel()]

    # GP mean prediction
    mu = gpr.predict(x_scaler.transform(grid), return_std=False).reshape(X1g.shape)

    plt.figure()
    cf = plt.contourf(X1g, X2g, mu, levels=14, cmap="viridis")
    cbar = plt.colorbar(cf, label=y_col_pred)

    # Overlay training points
    if all(c in df_all.columns for c in x_cols):
        x_obs = df_all[x_cols[0]].to_numpy()
        y_obs = df_all[x_cols[1]].to_numpy()
        z_obs = df_all[y_col_pred].to_numpy()

        sc = plt.scatter(
            x_obs, y_obs,
            c=z_obs,
            cmap="viridis",
            edgecolors="white", linewidths=1.2,
            s=50, zorder=3
        )

    plt.xlabel(x_cols[0]); plt.ylabel(x_cols[1])
    plt.title(title or f"GP surrogate mean of {y_col_pred}")
    plt.tight_layout()
    if out_png:
        Path(out_png).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(out_png, dpi=200)
    plt.close()

def plot_ei(df_all, x_scaler, gpr, bounds,
            x_cols=("concentration","potential"),
            y_col_obs="redplusblue",    # the ORIGINAL y column from your CSV
            xi=0.01, grid_size=200,
            out_png=None, title=None):


    # Regular grid over bounds
    x1 = np.linspace(bounds[0][0], bounds[0][1], grid_size)
    x2 = np.linspace(bounds[1][0], bounds[1][1], grid_size)
    X1g, X2g = np.meshgrid(x1, x2)
    grid = np.c_[X1g.ravel(), X2g.ravel()]

    # Predict μ, σ in ORIGINAL units
    mu, sigma = gpr.predict(x_scaler.transform(grid), return_std=True)

    # ✅ Use ORIGINAL y to define f_best
    if y_col_obs in df_all.columns:
        f_best = float(df_all[y_col_obs].min())
    else:
        raise ValueError(f"Column '{y_col_obs}' not found in df_all; needed for EI scale.")

    ei = ei_minimization(mu, sigma, f_best=f_best, xi=xi).reshape(X1g.shape)

    # Plot EI landscape only (no triangulation lines, no point colorbar)
    plt.figure()
    cf = plt.contourf(X1g, X2g, ei, levels=14, cmap="plasma")
    cbar = plt.colorbar(cf, label="Expected Improvement")

    # Optional: overlay training points as white-outlined markers (no colorbar)
    if all(c in df_all.columns for c in x_cols):
        plt.scatter(df_all[x_cols[0]], df_all[x_cols[1]],
                    edgecolors="white", linewidths=1.2, s=40, zorder=3)

    plt.xlabel(x_cols[0]); plt.ylabel(x_cols[1])
    plt.title(title or "Expected Improvement (minimization)")
    plt.tight_layout()
    if out_png:
        Path(out_png).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(out_png, dpi=200)
    plt.close()

# -----------------------
# CLI
# -----------------------

def main():
    parser = argparse.ArgumentParser(description="Bayesian Optimization (GPR) to minimize redplusblue over (concentration, potential).")
    parser.add_argument("--csv", required=True, help="Path to training CSV with columns: concentration, potential, redplusblue")
    parser.add_argument("--x-cols", default="concentration,potential", help="Comma-separated X columns (default: concentration,potential)")
    parser.add_argument("--y-col", default="redplusblue", help="Target column to minimize (default: redplusblue)")
    parser.add_argument("--k", type=int, default=5, help="How many next points to suggest (default: 5)")
    parser.add_argument("--xi", type=float, default=0.15, help="Exploration parameter for EI (default: 0.15)")
    parser.add_argument("--n-random", type=int, default=50000, help="Random candidate pool size for EI (default: 50000)")
    parser.add_argument("--min-dist-norm", type=float, default=0.2, help="Diversity radius in normalized space (default: 0.2)")
    parser.add_argument("--plots-dir", default=None, help="Directory to save plots (optional)")
    parser.add_argument("--out-csv", default=None, help="Where to save suggested points CSV (default: alongside CSV)")
    # Optional hard bounds:
    parser.add_argument("--conc-min", type=float, default=None)
    parser.add_argument("--conc-max", type=float, default=None)
    parser.add_argument("--pot-min", type=float, default=None)
    parser.add_argument("--pot-max", type=float, default=None)
    parser.add_argument("--random-state", type=int, default=42)
    args = parser.parse_args()

    x_cols = tuple([c.strip() for c in args.x_cols.split(",")])
    df_all, X, y = load_xy(args.csv, x_cols=x_cols, y_col=args.y_col)

    # Fit GP
    x_scaler, gpr = fit_gpr(X, y, random_state=args.random_state)

    # Bounds
    hard_bounds = None
    if args.conc_min is not None and args.conc_max is not None and args.pot_min is not None and args.pot_max is not None:
        hard_bounds = [(args.conc_min, args.conc_max), (args.pot_min, args.pot_max)]
    bounds = infer_bounds_from_data(X, pad_frac=0.05, hard_bounds=hard_bounds)

    # Propose next K points
    X_next, mu_next, sigma_next, ei_next = propose_candidates(
        x_scaler, gpr, bounds, y_orig=y,  # y is your original target vector from the CSV
        k=args.k, xi=args.xi, n_random=args.n_random, min_dist_norm=args.min_dist_norm,
        random_state=args.random_state
    )

    # Package suggestions
    suggestions = pd.DataFrame({
        x_cols[0]: X_next[:, 0],
        x_cols[1]: X_next[:, 1],
        "gp_mu_redplusblue": mu_next,
        "gp_sigma": sigma_next,
        "expected_improvement": ei_next,
    }).sort_values("expected_improvement", ascending=False)

    # Save CSV
    out_csv = args.out_csv or str(Path(args.csv).with_name(Path(args.csv).stem + "_bo_suggestions.csv"))
    suggestions.to_csv(out_csv, index=False)
    print(f"Saved suggestions to: {out_csv}")
    print(suggestions)

    # Plots (optional)
    if args.plots_dir:
        plots_dir = Path(args.plots_dir)
    else:
        plots_dir = Path(args.csv).with_name(Path(args.csv).stem + "_bo_plots")
    plots_dir.mkdir(parents=True, exist_ok=True)

    try:
        plot_surrogate_mean(
            df_all=df_all,
            x_scaler=x_scaler,
            gpr=gpr,
            bounds=bounds,
            x_cols=x_cols,
            y_col_pred=args.y_col,
            grid_size=200,
            out_png=str(plots_dir / "gp_surrogate_mean.png"),
            title=f"GP mean of {args.y_col} (lower is better)",
        )
        plot_ei(
            df_all=df_all,
            x_scaler=x_scaler,
            gpr=gpr,
            bounds=bounds,
            x_cols=x_cols,
            xi=args.xi,
            grid_size=200,
            out_png=str(plots_dir / "ei_landscape.png"),
            title="Expected Improvement (minimize redplusblue)",
        )
        print(f"Plots saved to: {plots_dir}")
    except Exception as e:
        print(f"Plotting skipped due to: {e}")

if __name__ == "__main__":
    main()

'''
python ContactAngle_MLGPRmodel.py `
  --csv "D:/1-PhD/4-RawData/2025/pama_trainingdata/analysis/drying-and-trainingdata_BOmodelinput_with_theta.csv" `
  --k 6 `
  --conc-min 10.0 --conc-max 200.0 `
  --pot-min 0.8 --pot-max 2.0 `
  --plots-dir "D:/1-PhD/4-RawData/2025/pama_trainingdata/analysis/bo_plots"
'''