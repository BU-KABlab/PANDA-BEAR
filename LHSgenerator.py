#!/usr/bin/env python3
"""
make_lhs_polymer_design.py

Generates Latin Hypercube samples for:
- pama_conc (0 or 10–50 mg/mL, log-spaced if nonzero)
- peo_conc  (0 or 10–50 mg/mL, log-spaced if nonzero)
- dep_v     (0.8–2.0 V, linear)

Computes stock volumes for a 300 µL final solution:
- PAMA stock: 200 mg/mL
- PEO  stock: 70 mg/mL
- Solvent fills remaining volume

Writes CSV: lhs_pama_peo_dep.csv
"""

import numpy as np
import math
import csv

# --- Config ---
N = 6  # number of samples
SEED = 42  # RNG seed
FINAL_VOL_UL = 300.0  # final volume (µL)
OUTFILE = "lhs_pama_peo_dep2.csv"

# Ranges
PAMA_MIN, PAMA_MAX = 10.0, 50.0
PEO_MIN, PEO_MAX = 10.0, 50.0
DEP_V_MIN, DEP_V_MAX = 0.8, 2.0

# Stock concentrations (mg/mL)
STOCK_PAMA = 200.0
STOCK_PEO = 70.0

# Allow zero?
ALLOW_ZERO_PAMA = True
ALLOW_ZERO_PEO = True


# --- Helpers ---
def latin_hypercube_01(n, d, rng):
    H = np.zeros((n, d), dtype=float)
    for j in range(d):
        strata = (np.arange(n) + rng.random(n)) / n
        rng.shuffle(strata)
        H[:, j] = strata
    return H


def u_to_logrange(u, lo, hi):
    lo_log, hi_log = math.log10(lo), math.log10(hi)
    return 10.0 ** (lo_log + u * (hi_log - lo_log))


def transform_with_zero(u, lo, hi, allow_zero):
    if allow_zero:
        # Split probability mass: 20% of zero, 80% chance log-spaced
        return np.where(u < 0.2, 0.0, u_to_logrange((u - 0.2) * 2.0, lo, hi))
    else:
        return u_to_logrange(u, lo, hi)


# --- Main ---
def main():
    rng = np.random.default_rng(SEED)
    U = latin_hypercube_01(N, 3, rng)

    pama_conc = transform_with_zero(U[:, 0], PAMA_MIN, PAMA_MAX, ALLOW_ZERO_PAMA)
    peo_conc = transform_with_zero(U[:, 1], PEO_MIN, PEO_MAX, ALLOW_ZERO_PEO)
    dep_v = DEP_V_MIN + U[:, 2] * (DEP_V_MAX - DEP_V_MIN)

    vol_pama_uL = (pama_conc * FINAL_VOL_UL) / STOCK_PAMA
    vol_peo_uL = (peo_conc * FINAL_VOL_UL) / STOCK_PEO
    vol_solvent_uL = FINAL_VOL_UL - (vol_pama_uL + vol_peo_uL)
    vol_solvent_uL = np.maximum(vol_solvent_uL, 0.0)

    fieldnames = [
        "sample_id",
        "pama_conc_mg_per_mL",
        "peo_conc_mg_per_mL",
        "dep_v",
        "vol_pama_uL",
        "vol_peo_uL",
        "vol_solvent_uL",
        "final_vol_uL",
    ]

    with open(OUTFILE, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for i in range(N):
            w.writerow(
                {
                    "sample_id": i + 1,
                    "pama_conc_mg_per_mL": f"{pama_conc[i]:.6f}",
                    "peo_conc_mg_per_mL": f"{peo_conc[i]:.6f}",
                    "dep_v": f"{dep_v[i]:.6f}",
                    "vol_pama_uL": f"{vol_pama_uL[i]:.3f}",
                    "vol_peo_uL": f"{vol_peo_uL[i]:.3f}",
                    "vol_solvent_uL": f"{vol_solvent_uL[i]:.3f}",
                    "final_vol_uL": f"{FINAL_VOL_UL:.3f}",
                }
            )

    print(f"Wrote {N} samples to {OUTFILE}")


if __name__ == "__main__":
    main()
