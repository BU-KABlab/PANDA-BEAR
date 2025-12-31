#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
from pathlib import Path
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.tri as mtri


DEFAULT_Y = "theta_pred_deg"

def _find_interval_cols(df: pd.DataFrame, ycol: str):
    """
    Find lower/upper interval columns that correspond to ycol.
    We look for theta_lo_* / theta_hi_* first. If not found, try generic '*_lo'/'*_hi'.
    Returns (lo_col, hi_col, tag). Raises if not found.
    """
    cols = list(df.columns)

    # Prefer standard names that start with 'theta'
    lo_candidates = [c for c in cols if re.match(r"^theta_(pred_)?lo_", c)]
    hi_candidates = [c for c in cols if re.match(r"^theta_(pred_)?hi_", c)]

    # try to pair suffixes like '95_pre'
    for lo in lo_candidates:
        suffix = lo.split("lo_", 1)[-1]
        hi = f"theta_hi_{suffix}"
        if hi in df.columns:
            return lo, hi, suffix

    # fallback: first available pair if present
    if lo_candidates and hi_candidates:
        return lo_candidates[0], hi_candidates[0], "interval"

    # last resort: columns ending with 'lo'/'hi'
    lo_generic = [c for c in cols if c.lower().endswith("lo")]
    hi_generic = [c for c in cols if c.lower().endswith("hi")]
    if lo_generic and hi_generic:
        return lo_generic[0], hi_generic[0], "interval"

    raise ValueError("Could not find interval columns. Expected columns like 'theta_lo_*' and 'theta_hi_*'.")

def _ensure_dir(path: str):
    Path(path).parent.mkdir(parents=True, exist_ok=True)

def _errorbar_plot(df: pd.DataFrame, xcol: str, ycol: str, lo_col: str, hi_col: str, out_png: str, title: str):
    d = df[[xcol, ycol, lo_col, hi_col]].dropna().copy()
    if d.empty:
        print(f"WARNING: No data for {xcol} vs {ycol}. Skipping.")
        return

    # Sort by x so the plot is tidy
    d.sort_values(by=xcol, inplace=True)

    x = d[xcol].values
    y = d[ycol].values
    lo = d[lo_col].values
    hi = d[hi_col].values

    # Asymmetric error bars: lower = y - lo, upper = hi - y
    yerr = np.vstack([y - lo, hi - y])
    # plot a gradient with 
    plt.figure()
    plt.errorbar(x, y, yerr=yerr, fmt='o', capsize=3)
    plt.xlabel(xcol)
    plt.ylabel("Contact angle θ (deg)")
    plt.title(title)
    plt.tight_layout()
    _ensure_dir(out_png)
    plt.savefig(out_png, dpi=200)
    plt.close()
    print(f"Saved: {out_png}")

def _errorbar_plot_colored(
    df: pd.DataFrame,
    xcol: str,           # e.g., "concentration"  or "potential"
    ycol: str,           # e.g., "theta_pred_deg"
    lo_col: str,         # interval lower column
    hi_col: str,         # interval upper column
    color_by: str,       # the other variable to color points by
    out_png: str,
    title: str,
):
    """
    Error bars from [lo, hi] around y, colored by another column (gradient).
    Draws error bars first (fmt='none'), then overlays a scatter colored by 'color_by'.
    """
    needed = [xcol, ycol, lo_col, hi_col, color_by]
    d = df[needed].dropna().copy()
    if d.empty:
        print(f"WARNING: No data for {xcol} vs {ycol}. Skipping.")
        return

    # Sort by x for tidy plotting (keep all columns aligned)
    d.sort_values(by=xcol, inplace=True)

    x  = d[xcol].to_numpy()
    y  = d[ycol].to_numpy()
    lo = d[lo_col].to_numpy()
    hi = d[hi_col].to_numpy()
    c  = d[color_by].to_numpy()

    # Asymmetric error bars: lower = y - lo, upper = hi - y
    yerr = np.vstack([y - lo, hi - y])

    plt.figure(figsize=(7, 3))

    # 1) draw only error bars (no markers), inherit default style
    plt.errorbar(x, y, yerr=yerr, fmt='none', capsize=3)

    # 2) overlay scatter colored by the other variable (gradient)
    sc = plt.scatter(x, y, c=c)  # no explicit cmap -> default colormap

    # add colorbar keyed to the 'color_by' values
    cb = plt.colorbar(sc)
    cb.set_label(color_by)

    plt.xlabel(xcol)
    plt.ylabel("Contact angle θ (deg)")
    plt.title(title)
    plt.tight_layout()
    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_png, dpi=200)
    plt.close()
    print(f"Saved: {out_png}")

def _contour_plot(df: pd.DataFrame, xcol: str, ycol: str, zcol: str, out_png: str, title: str, levels=14):
    d = df[[xcol, ycol, zcol]].dropna().copy()
    if d.empty:
        print(f"WARNING: No data for contour ({xcol},{ycol})→{zcol}. Skipping.")
        return

    x = d[xcol].values
    y = d[ycol].values
    z = d[zcol].values

    # Triangulate scattered points (no SciPy needed)
    tri = mtri.Triangulation(x, y)

    plt.figure()
    cntr = plt.tricontourf(tri, z, levels=levels)
    plt.colorbar(cntr, label="θ (deg)")
    # overlay points
    plt.triplot(tri, lw=0.5, alpha=0.4)
    plt.scatter(x, y)
    plt.xlabel(xcol)
    plt.ylabel(ycol)
    plt.title(title)
    plt.tight_layout()
    _ensure_dir(out_png)
    plt.savefig(out_png, dpi=200)
    plt.close()
    print(f"Saved: {out_png}")

def _ensure_dir(path: str):
    Path(path).parent.mkdir(parents=True, exist_ok=True)

def _contour_heatmap(df, xcol: str, ycol: str, zcol: str,
                     out_png: str, title: str,
                     levels: int = 14, grid_size: int = 200):
    """
    Smooth heatmap/contour of z over (x, y) without showing triangulation or points.
    Uses Matplotlib's TriInterpolator to evaluate on a regular grid.
    """
    d = df[[xcol, ycol, zcol]].dropna().copy()
    if d.empty:
        print(f"WARNING: No data for heatmap ({xcol},{ycol})→{zcol}. Skipping.")
        return

    x = d[xcol].to_numpy()
    y = d[ycol].to_numpy()
    z = d[zcol].to_numpy()

    # Triangulate scattered data
    tri = mtri.Triangulation(x, y)

    # Option A: smooth-ish cubic interpolation (can overshoot slightly)
    try:
        interp = mtri.CubicTriInterpolator(tri, z, kind='geom')
        use_cubic = True
    except Exception:
        # Fallback: piecewise-linear interpolation (monotone, less smooth)
        interp = mtri.LinearTriInterpolator(tri, z)
        use_cubic = False

    # Build a regular grid over the data domain
    xi = np.linspace(x.min(), x.max(), grid_size)
    yi = np.linspace(y.min(), y.max(), grid_size)
    Xi, Yi = np.meshgrid(xi, yi)

    Zi = interp(Xi, Yi)  # returns masked array (outside convex hull masked)

    plt.figure()
    # Filled contour (nice for discrete bands)
    cf = plt.contourf(Xi, Yi, Zi, levels=levels)
    plt.colorbar(cf, label="θ (deg)")

    # Alternative: comment the contourf above and use pcolormesh for continuous heatmap
    # pm = plt.pcolormesh(Xi, Yi, Zi, shading='auto')
    # plt.colorbar(pm, label="θ (deg)")

    plt.xlabel(xcol)
    plt.ylabel(ycol)
    plt.title(title + (" [cubic]" if use_cubic else " [linear]"))
    plt.tight_layout()
    _ensure_dir(out_png)
    plt.savefig(out_png, dpi=200)
    plt.close()
    print(f"Saved: {out_png}")


def main():

    ap = argparse.ArgumentParser(
        description="Error-bar (colored) and smooth heatmap/contour visualizations for contact angle predictions."
    )
    ap.add_argument("--csv", required=True, help="Path to CSV with predictions, intervals, and metadata.")
    ap.add_argument("--plots-dir", default=None,
                   help="Where to save figures (default: alongside CSV in '<csvname>_plots').")
    ap.add_argument("--theta-col", default="theta_pred_deg",
                   help="θ column to visualize (default: theta_pred_deg).")
    ap.add_argument("--concentration-col", default="concentration",
                   help="Column for concentration (default: 'concentration').")
    ap.add_argument("--potential-col", default="potential",
                   help="Column for potential (default: 'potential').")
    ap.add_argument("--levels", type=int, default=14,
                   help="Contour levels for the heatmap (default: 14).")
    ap.add_argument("--grid-size", type=int, default=200,
                   help="Grid size for smooth heatmap interpolation (default: 200).")
    args = ap.parse_args()

    # Load data
    df = pd.read_csv(args.csv)

    # Where to save figures
    csv_path = Path(args.csv)
    plots_dir = Path(args.plots_dir) if args.plots_dir else (csv_path.parent / (csv_path.stem + "_plots"))
    plots_dir.mkdir(parents=True, exist_ok=True)

    # Try to locate interval columns that match your θ column
    try:
        lo_col, hi_col, tag = _find_interval_cols(df, args.theta_col)
    except Exception as e:
        lo_col = hi_col = tag = None
        print(f"NOTE: Interval columns not found; error-bar plots will be skipped. Details: {e}")

    # ---- Error-bar plots (colored markers) ----
    if lo_col and hi_col:
        # concentration vs θ, colored by potential
        if args.concentration_col in df.columns and args.potential_col in df.columns:
            _errorbar_plot_colored(
                df,
                xcol=args.concentration_col,
                ycol=args.theta_col,
                lo_col=lo_col,
                hi_col=hi_col,
                color_by=args.potential_col,
                out_png=str(plots_dir / f"{args.concentration_col}_vs_{args.theta_col}_err_colored_by_{args.potential_col}.png"),
                title=f"{args.concentration_col} vs θ (error bars, colored by {args.potential_col})",
            )
        else:
            if args.concentration_col not in df.columns:
                print(f"WARNING: '{args.concentration_col}' not in CSV; skipping concentration error-bar plot.")
            if args.potential_col not in df.columns:
                print(f"WARNING: '{args.potential_col}' not in CSV; skipping concentration error-bar plot.")
        # potential vs θ, colored by concentration
        if args.potential_col in df.columns and args.concentration_col in df.columns:
            _errorbar_plot_colored(
                df,
                xcol=args.potential_col,
                ycol=args.theta_col,
                lo_col=lo_col,
                hi_col=hi_col,
                color_by=args.concentration_col,
                out_png=str(plots_dir / f"{args.potential_col}_vs_{args.theta_col}_err_colored_by_{args.concentration_col}.png"),
                title=f"{args.potential_col} vs θ (error bars, colored by {args.concentration_col})",
            )
        else:
            if args.potential_col not in df.columns:
                print(f"WARNING: '{args.potential_col}' not in CSV; skipping potential error-bar plot.")
            if args.concentration_col not in df.columns:
                print(f"WARNING: '{args.concentration_col}' not in CSV; skipping potential error-bar plot.")
    else:
        print("NOTE: Skipping both error-bar plots because interval columns were not detected.")

    # ---- Smooth heatmap/contour: θ over (concentration, potential) ----
    if args.concentration_col in df.columns and args.potential_col in df.columns:
        _contour_heatmap(
            df,
            xcol=args.concentration_col,
            ycol=args.potential_col,
            zcol=args.theta_col,
            out_png=str(plots_dir / f"heatmap_{args.concentration_col}_{args.potential_col}_{args.theta_col}.png"),
            title=f"θ heatmap over {args.concentration_col} × {args.potential_col}",
            levels=args.levels,
            grid_size=args.grid_size,
        )
    else:
        print("WARNING: Missing concentration or potential columns; skipping heatmap/contour plot.")

    print(f"All figures (if generated) are in: {plots_dir}")


if __name__ == "__main__":
    main()

# Example usage - see README.md for detailed documentation