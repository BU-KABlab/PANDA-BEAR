"""
Contact Angle LED Detection Script
-----------------------------------
Author: Harley Quinn
Date Created: 2025-05-01
Date last modified: 2025-07-11

Summary:
This script analyzes images to detect the positions of red and blue LEDs
used for top-down contact angle measurements. It combines color-based detection
with grayscale intensity analysis to ensure robust identification.

Workflow Summary:

1. Image Loading and Preprocessing:
   - Load image from file.
   - Convert to HSV for color masks and to grayscale for intensity analysis.

2. Droplet Center Detection:
   - Attempt to detect the droplet using Hough Circle Transform.
   - If Hough fails, fallback to threshold-based contour detection.

3. Color Mask Creation:
   - Create red and blue masks using HSV thresholds.
   - Extract centroids of masked regions using contour analysis.
   - Merge close centroids to reduce duplicates.

4. Blue LED Detection:
   - Attempt primary detection using centroid alignment and distance checks.
   - If primary fails, use fallback: extract horizontal intensity profile
     across the droplet and locate two brightest peaks (blue LEDs).
   - Calculate Euclidean distance and midpoint of detected blue LEDs.

5. Red LED Detection:
   - Attempt primary detection using vertical alignment of red centroids.
   - If primary fails, use fallback:
     - Extract vertical intensity profile at the X-position of the blue midpoint.
     - Detect peaks and evaluate candidate pairs based on:
         * Y separation (vertical distance)
         * Intensity similarity
         * Euclidean distance
     - Select the best scoring pair.
     - If only one red peak is found, mirror it across the blue midpoint to synthesize the missing LED.

6. Final Calculations and Annotations:
   - Compute distances and midpoints for both red and blue pairs.
   - Extract HSV values at LED positions.
   - Draw:
       * Droplet center
       * All detected centroids
       * Confirmed red and blue LED pairs
   - Save annotated debug images.

7. Debugging and Reporting:
   - Save fallback intensity profiles and detailed CSV logs explaining:
       * Detected peaks
       * Candidate pair evaluations
       * Rejection reasons

8. Error Handling:
   - Raises descriptive errors when either red or blue LED pairs cannot be confidently detected,
     even after fallback methods.

"""

import cv2
import numpy as np
import csv
import os
from itertools import combinations
import scipy.signal
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for matplotlib
import matplotlib.pyplot as plt
import math
import re
import json
from typing import Optional, List, Tuple, Dict, Any

# Placeholder stubs for missing functions (implement or import as needed)
def clahe_on_v(hsv_img):
    # Apply CLAHE to V channel and return HSV image
    hsv = hsv_img.copy()
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    hsv[:,:,2] = clahe.apply(hsv[:,:,2])
    return hsv

def dog_response(v, sigma_small=1.5, sigma_big=3.5):
    g1 = cv2.GaussianBlur(v, (0,0), sigma_small)
    g2 = cv2.GaussianBlur(v, (0,0), sigma_big)
    return cv2.subtract(g1, g2)

def color_likelihood_h(hsv_img, target_h, tol=18, sat_min=10):
    h = hsv_img[:,:,0]
    s = hsv_img[:,:,1]
    mask = ((np.abs(h.astype(int)-target_h) <= tol) & (s >= sat_min)).astype(np.uint8)*255
    return mask

def build_droplet_ring_mask(shape, center, r_in, r_out):
    H, W = shape[:2]
    Y, X = np.ogrid[:H, :W]
    dist = np.sqrt((X-center[0])**2 + (Y-center[1])**2)
    mask = ((dist >= r_in) & (dist <= r_out)).astype(np.uint8)*255
    return mask

def conn_comp_candidates(bw, min_area=4, max_area=400):
    cnts, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cands = []
    for c in cnts:
        a = cv2.contourArea(c)
        if not (min_area <= a <= max_area):
            continue
        M = cv2.moments(c)
        if M["m00"] == 0: continue
        cx = int(M["m10"]/M["m00"])
        cy = int(M["m01"]/M["m00"])
        per = cv2.arcLength(c, True)
        compact = 0.0
        if a > 0 and per > 0:
            circ = (per*per)/(4.0*np.pi*a)
            compact = 1.0/max(circ, 1e-6)
        cands.append({"cx":cx, "cy":cy, "compact":compact})
    return cands

# Fix type hints for compatibility
def load_led_params(params_path: Optional[str]):
    if not params_path or not os.path.exists(params_path):
        return None
    with open(params_path,"r") as f:
        return json.load(f)

_Z_PATTERNS = [
    re.compile(r"z-?([0-9]+)-([0-9]+)mm", re.IGNORECASE),   # z-40-00mm
    re.compile(r"z-?([0-9]+(?:\.[0-9]+)?)", re.IGNORECASE), # z-39.5
]

def extract_z_mm_from_name(name: str) -> Optional[float]:
    base = os.path.basename(name)
    for pat in _Z_PATTERNS:
        m = pat.search(base)
        if not m: 
            continue
        if len(m.groups()) == 2:
            whole, frac = m.groups()
            return float(f"{whole}.{frac}")
        else:
            return float(m.group(1))
    return None

def _variance_of_laplacian(img_roi: np.ndarray) -> float:
    lap = cv2.Laplacian(img_roi, cv2.CV_64F, ksize=3)
    return float(lap.var())

def _local_contrast(gray_img: np.ndarray, cx: int, cy: int, r_inner: int=4, r_outer: int=9) -> float:
    h, w = gray_img.shape[:2]
    y0, y1 = max(0, cy-r_outer), min(h, cy+r_outer+1)
    x0, x1 = max(0, cx-r_outer), min(w, cx+r_outer+1)
    patch = gray_img[y0:y1, x0:x1]
    if patch.size == 0:
        return 0.0

    yy, xx = np.ogrid[y0:y1, x0:x1]
    rr = np.sqrt((xx-cx)**2 + (yy-cy)**2)

    spot_region = patch[rr <= r_inner]
    bg_annulus = patch[(rr > r_inner) & (rr <= r_outer)]

    if spot_region.size < 5 or bg_annulus.size < 20:
        return 0.0

    peak = np.percentile(spot_region, 95)
    bg = np.median(bg_annulus)
    return float(max(0.0, peak - bg))

def _compactness(contour: np.ndarray) -> float:
    # Higher = rounder/tighter blob
    area = cv2.contourArea(contour)
    per = cv2.arcLength(contour, True)
    if area <= 0 or per <= 0:
        return 0.0
    # Ideal circle has per^2 / (4π area) ≈ 1; we invert to map to [0,1-ish]
    circ_ratio = (per*per) / (4.0*np.pi*area)
    return float(1.0 / max(circ_ratio, 1e-6))

def score_led_focus_for_frame(
    image: np.ndarray,
    droplet_center: tuple[int,int],
    red_mask: np.ndarray,
    blue_mask: np.ndarray,
    search_radius: int = 100,
    expect_red_sep: float = 80.0,
    red_sep_tol: float = 30.0,
) -> dict:
    """
    Returns a dict with:
      score (float): higher = better focus for LED reflections
      details (dict): per-spot metrics and geometry info for logging
      picks (dict): chosen red/blue pairs [(x,y), (x,y)] if available
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    cx0, cy0 = droplet_center

    def _components(mask):
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        # limit to search_radius around droplet center
        kept = []
        for c in cnts:
            M = cv2.moments(c)
            if M["m00"] == 0: 
                continue
            cx = int(M["m10"]/M["m00"]); cy = int(M["m01"]/M["m00"])
            if np.hypot(cx-cx0, cy-cy0) <= search_radius:
                kept.append((c, (cx,cy)))
        return kept

    def _rank_two_spots(components):
        # Rank by composite spot score (sharpness + contrast + compactness)
        scored = []
        for c, (cx,cy) in components:
            # small ROI for Laplacian variance
            y0, y1 = max(0, cy-6), min(gray.shape[0], cy+7)
            x0, x1 = max(0, cx-6), min(gray.shape[1], cx+7)
            roi = gray[y0:y1, x0:x1]
            sharp = _variance_of_laplacian(roi)
            contrast = _local_contrast(gray, cx, cy, r_inner=4, r_outer=9)
            compact = _compactness(c)

            scored.append({
                "cx": cx, "cy": cy,
                "sharp": sharp,
                "contrast": contrast,
                "compact": compact,
                "raw": (c, (cx,cy))
            })
        if not scored:
            return [], []

        # Normalize metrics (robust) so one stack doesn’t dominate
        eps = 1e-9
        for key in ("sharp","contrast","compact"):
            vals = np.array([s[key] for s in scored], dtype=float)
            med, iqr = np.median(vals), (np.percentile(vals,75)-np.percentile(vals,25))
            denom = max(iqr, vals.std(ddof=1), 1.0)  # keep scales sane
            for s in scored:
                s[f"nz_{key}"] = (s[key]-med)/denom

        # Composite per spot
        for s in scored:
            s["spot_score"] = 0.6*s["nz_sharp"] + 0.3*s["nz_contrast"] + 0.1*s["nz_compact"]

        # Top two by spot_score
        scored_sorted = sorted(scored, key=lambda d: d["spot_score"], reverse=True)
        top2 = scored_sorted[:2]
        return top2, scored_sorted

    # Build component lists
    red_comps = _components(red_mask)
    blue_comps = _components(blue_mask)

    red_top2, red_all = _rank_two_spots(red_comps)
    blue_top2, blue_all = _rank_two_spots(blue_comps)

    def _pair_and_geom(top2):
        if len(top2) < 2:
            return None, {}
        p1 = (top2[0]["cx"], top2[0]["cy"])
        p2 = (top2[1]["cx"], top2[1]["cy"])
        mid = ((p1[0]+p2[0])//2, (p1[1]+p2[1])//2)
        sep = float(np.hypot(p1[0]-p2[0], p1[1]-p2[1]))
        return (p1,p2), {"mid": mid, "sep": sep}

    red_pair, red_geom = _pair_and_geom(red_top2)
    blue_pair, blue_geom = _pair_and_geom(blue_top2)

    # Base score = sum of spot scores for the chosen four spots (if present)
    base = 0.0
    if red_top2: base += sum(s["spot_score"] for s in red_top2)
    if blue_top2: base += sum(s["spot_score"] for s in blue_top2)

    # Geometry bonuses/penalties
    geom_bonus = 0.0
    if red_pair:
        # Reward red separation close to expected
        sep_err = abs((red_geom["sep"] if "sep" in red_geom else 0.0) - expect_red_sep)
        geom_bonus += max(0.0, 2.0 - (sep_err / max(red_sep_tol, 1.0)))  # clipped ~[0..2]
        # Reward verticality (red should be mostly vertical)
        (x1,y1),(x2,y2)= red_pair
        dx, dy = abs(x1-x2), abs(y1-y2)
        geom_bonus += max(0.0, (dy - dx) / max(dy+dx,1.0))  # ∈ [0..1] if dy>>dx

    if red_pair and blue_pair:
        # Reward blue midpoint near red midpoint
        rx,ry = red_geom["mid"]; bx,by = blue_geom["mid"]
        mid_d = np.hypot(rx-bx, ry-by)
        geom_bonus += max(0.0, 2.0 - (mid_d/25.0))  # within ~25px gets +2 → +0

    # Slight penalty if chosen spots are too far from droplet center
    def _center_penalty(pair):
        if not pair: return 0.0
        (x1,y1),(x2,y2) = pair
        d1 = np.hypot(x1-cx0, y1-cy0); d2 = np.hypot(x2-cx0, y2-cy0)
        # beyond ~search_radius/2 start penalizing
        th = max(1.0, search_radius/2.0)
        return max(0.0, (d1-th)/th) + max(0.0, (d2-th)/th)

    penalty = 0.5*_center_penalty(red_pair) + 0.5*_center_penalty(blue_pair)

    score = base + geom_bonus - penalty

    return {
        "score": float(score),
        "details": {
            "red_spots": red_all,
            "blue_spots": blue_all,
            "red_sep": red_geom.get("sep", None) if red_geom else None,
            "blue_sep": blue_geom.get("sep", None) if blue_geom else None,
        },
        "picks": {
            "red_pair": red_pair,
            "blue_pair": blue_pair
        }
    }

def select_best_focus_frame(
    image_paths: list[str],
    debug_folder: str | None = None,
    expect_red_sep: float = 80.0,
    red_sep_tol: float = 30.0
) -> tuple[str, dict]:
    """
    Returns (best_image_path, log_dict)
    """
    scored = []
    os.makedirs(debug_folder, exist_ok=True) if debug_folder else None

    for p in image_paths:
        img = cv2.imread(p)
        if img is None:
            continue
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        base = os.path.splitext(os.path.basename(p))[0]

        try:
            droplet_center, _, _ = detect_droplet_center(gray, debug_folder=debug_folder, img_basename=base)
        except Exception:
            # no droplet = unscored
            continue

        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        red_lower = np.array([150, 0, 200]); red_upper = np.array([170, 255, 255])
        blue_lower = np.array([85, 10, 200]); blue_upper = np.array([100, 255, 255])
        red_mask = cv2.inRange(hsv, red_lower, red_upper)
        blue_mask = cv2.inRange(hsv, blue_lower, blue_upper)

        s = score_led_focus_for_frame(
            img, droplet_center, red_mask, blue_mask,
            search_radius=100,
            expect_red_sep=expect_red_sep, red_sep_tol=red_sep_tol
        )
        z = extract_z_mm_from_name(p)
        scored.append({
            "path": p,
            "z_mm": z,
            "score": s["score"],
            "red_sep": s["details"]["red_sep"],
            "blue_sep": s["details"]["blue_sep"],
        })

    if not scored:
        raise RuntimeError("No frames could be scored for focus.")

    scored.sort(key=lambda d: d["score"], reverse=True)
    best = scored[0]

    # Optional: write a per-stack CSV log
    if debug_folder:
        out_csv = os.path.join(debug_folder, "focus_scores.csv")
        header = not os.path.exists(out_csv)
        with open(out_csv, "a", newline="") as f:
            w = csv.writer(f)
            if header:
                w.writerow(["image_name","z_mm","score","red_sep","blue_sep"])
            for row in scored:
                w.writerow([
                    os.path.basename(row["path"]), 
                    f"{row['z_mm']}" if row["z_mm"] is not None else "",
                    f"{row['score']:.3f}",
                    f"{row['red_sep']:.1f}" if row["red_sep"] else "",
                    f"{row['blue_sep']:.1f}" if row["blue_sep"] else "",
                ])

    return best["path"], {"ranked": scored}

def detect_led_pairs_specular_no_color(
    image_bgr,
    gray,
    droplet_center,
    search_radius_px=120,
    inner_ring_frac=0.25,
    outer_ring_frac=0.70,
    blue_sep_range=(35.0, 120.0),
    red_expected_sep=80.0,
    red_sep_tol=35.0,
    debug_folder=None,
    base_name=""
):
    """
    Color-agnostic LED finder:
      - CLAHE on V-like intensity
      - DoG (small - big Gaussian) for shiny dots
      - White top-hat (local bright peaks)
      - 'Whiteness' (low chroma) helps prefer specular cores over colored halos
      - Ring mask (donut) around droplet to avoid rim/center
      - Pair by geometry: horizontal ≈ blue, vertical ≈ red
    """
    H, W = gray.shape[:2]
    cx, cy = droplet_center

    # intensity (V-like) with CLAHE
    v = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)[:,:,2]
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    v2 = clahe.apply(v)

    # DoG & top-hat
    g1 = cv2.GaussianBlur(v2, (0,0), 1.8)
    g2 = cv2.GaussianBlur(v2, (0,0), 4.2)
    dog = cv2.subtract(g1, g2)
    se = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9,9))
    tophat = cv2.morphologyEx(v2, cv2.MORPH_TOPHAT, se)

    # "whiteness" (achromaticity): bright & R≈G≈B
    bgr = image_bgr.astype(np.float32)
    mean_rgb = bgr.mean(axis=2) + 1e-6
    std_rgb = bgr.std(axis=2)
    achroma = (1.0 - (std_rgb / mean_rgb))  # high when achromatic
    achroma = np.clip(achroma, 0, 1) * (v2.astype(np.float32)/255.0)  # favor bright achromatic
    achroma = (achroma*255).astype(np.uint8)

    # normalize helper
    def n255(x):
        a, b = float(x.min()), float(x.max())
        if b - a < 1e-6: return np.zeros_like(x, np.uint8)
        return ((x - a) * (255.0/(b-a))).astype(np.uint8)

    dog_n = n255(dog)
    top_n = n255(tophat)
    ach_n = n255(achroma)

    # ring (donut) ROI around the droplet
    R = int(max(30, 0.9*search_radius_px))
    r_in  = max(5, int(inner_ring_frac * R))
    r_out = min(int(outer_ring_frac * R), int(search_radius_px))
    Y, X = np.ogrid[:H, :W]
    dist = np.sqrt((X-cx)**2 + (Y-cy)**2)
    ring = ((dist >= r_in) & (dist <= r_out)).astype(np.uint8)*255

    # combined score map (no color)
    score = cv2.min(255, (0.5*dog_n + 0.3*top_n + 0.2*ach_n)).astype(np.uint8)
    score = cv2.bitwise_and(score, score, mask=ring)

    # threshold at high percentile within ring
    ring_vals = score[ring>0]
    t = int(np.percentile(ring_vals, 96)) if ring_vals.size else 220
    _, bw = cv2.threshold(score, t, 255, cv2.THRESH_BINARY)
    bw = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(3,3)), 1)

    # connected components to candidates
    cnts, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cands = []
    for c in cnts:
        a = cv2.contourArea(c)
        if a < 4 or a > 400:  # adjust if your dots are bigger/smaller
            continue
        M = cv2.moments(c)
        if M["m00"] == 0: 
            continue
        px, py = int(M["m10"]/M["m00"]), int(M["m01"]/M["m00"])
        per = cv2.arcLength(c, True)
        compact = 0.0
        if a > 0 and per > 0:
            circ = (per*per)/(4.0*np.pi*a)
            compact = 1.0/max(circ, 1e-6)

        # local contrast
        y0,y1 = max(0,py-8), min(H,py+9)
        x0,x1 = max(0,px-8), min(W,px+9)
        patch = v2[y0:y1, x0:x1]
        lc = 0.0
        if patch.size:
            lc = float(np.percentile(patch,95) - np.median(patch))

        s = float(0.45*dog_n[py,px] + 0.25*top_n[py,px] + 0.20*lc + 0.10*(255.0*compact))
        cands.append({"pt":(px,py), "score":s})

    # keep strongest few
    cands = sorted(cands, key=lambda d: d["score"], reverse=True)[:12]
    if len(cands) < 2:
        return None, None, {"why":"<2 candidates", "r_in":r_in, "r_out":r_out}

    # pair scoring
    def euclid(p,q): return float(np.hypot(p[0]-q[0], p[1]-q[1]))

    # choose horizontal pair (≈blue): large dx, sep in range, midpoint near droplet center
    best_blue=None; best_bs=-1e9
    for i in range(len(cands)):
        for j in range(i+1, len(cands)):
            p1, p2 = cands[i]["pt"], cands[j]["pt"]
            dx, dy = abs(p1[0]-p2[0]), abs(p1[1]-p2[1])
            sep = euclid(p1,p2)
            if not (blue_sep_range[0] <= sep <= blue_sep_range[1]): continue
            mid = ((p1[0]+p2[0])//2, (p1[1]+p2[1])//2)
            mid_d = euclid(mid, (cx,cy))
            horiz = max(0.0, dx - dy)
            s = cands[i]["score"] + cands[j]["score"] + 0.7*horiz - 0.05*mid_d
            if s > best_bs:
                best_bs = s; best_blue = (p1,p2)

    # choose vertical pair (≈red): large dy, sep ~ expected
    best_red=None; best_rs=-1e9
    for i in range(len(cands)):
        for j in range(i+1, len(cands)):
            p1, p2 = cands[i]["pt"], cands[j]["pt"]
            dx, dy = abs(p1[0]-p2[0]), abs(p1[1]-p2[1])
            sep = euclid(p1,p2)
            if abs(sep - red_expected_sep) > red_sep_tol: continue
            vert = max(0.0, dy - dx)
            s = cands[i]["score"] + cands[j]["score"] + 0.8*vert - 0.25*abs(sep - red_expected_sep)
            if s > best_rs:
                best_rs = s; best_red = (p1,p2)

    return best_red, best_blue, {"r_in":r_in, "r_out":r_out, "N":len(cands)}


def detect_led_pairs_robust(
    image_bgr,
    hsv_img,
    gray,
    droplet_center,
    droplet_radius_estimate=None,
    hsv_red=(np.array([150,0,200],np.uint8), np.array([170,255,255],np.uint8)),
    hsv_blue=(np.array([85,10,200],np.uint8), np.array([100,255,255],np.uint8)),
    search_radius_px=120,
    inner_ring_frac=0.25,
    outer_ring_frac=0.70,
    blue_sep_range=(35.0, 120.0),
    red_expected_sep=80.0,
    red_sep_tol=35.0,
    debug_folder=None,
    base_name="",
):
    """
    Specular-highlight driven detector:
    - CLAHE(V), DoG, ring mask
    - Color likelihood for red/blue
    - Candidate scoring: DoG + local contrast + compactness + color
    - Pair scoring: geometry + symmetry
    """
    cx, cy = droplet_center
    H, W = gray.shape[:2]

    # 1) normalize brightness
    hsv_norm = clahe_on_v(hsv_img)
    v = hsv_norm[:,:,2]

    # 2) estimate droplet radius from search_radius if none
    R = droplet_radius_estimate
    if R is None:
        # crude: radius ~ search radius*0.9 (just to size the ring)
        R = max(30, int(0.9*search_radius_px))

    # 3) ring ROI to avoid rim & center
    r_in  = max(5, int(inner_ring_frac * R))
    r_out = min(int(outer_ring_frac * R), int(search_radius_px))
    ring_mask = build_droplet_ring_mask(gray.shape, droplet_center, r_in, r_out)

    # 4) feature maps
    dog = dog_response(v, sigma_small=1.5, sigma_big=3.5)
    # local contrast via morphological white top-hat (spots over background)
    se = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9,9))
    tophat = cv2.morphologyEx(v, cv2.MORPH_TOPHAT, se)

    # color likelihoods (OpenCV hue 0..179)
    red_like  = color_likelihood_h(hsv_norm, target_h=160, tol=18, sat_min=10)
    blue_like = color_likelihood_h(hsv_norm, target_h=92,  tol=18, sat_min=10)

    # 5) build red/blue candidate maps, constrain to ring
    def norm255(img):
        a,b = float(img.min()), float(img.max())
        if b-a < 1e-6: return np.zeros_like(img, np.uint8)
        return ((img - a)*(255.0/(b-a))).astype(np.uint8)

    dog_n   = norm255(dog)
    top_n   = norm255(tophat)

    red_score_map  = cv2.min(255, (0.6*dog_n + 0.4*top_n)).astype(np.uint8)
    blue_score_map = cv2.min(255, (0.6*dog_n + 0.4*top_n)).astype(np.uint8)

    # weight by color likelihood
    red_score_map  = cv2.multiply(red_score_map,  red_like,  scale=1/255.0)
    blue_score_map = cv2.multiply(blue_score_map, blue_like, scale=1/255.0)

    # apply ring mask
    red_score_map  = cv2.bitwise_and(red_score_map,  red_score_map,  mask=ring_mask)
    blue_score_map = cv2.bitwise_and(blue_score_map, blue_score_map, mask=ring_mask)

    # 6) threshold adaptively to get components
    def thresh_and_candidates(score_map):
        # threshold at high percentile to keep only strong spots
        t = np.percentile(score_map[ring_mask>0], 96) if np.any(ring_mask>0) else 200
        _, bw = cv2.threshold(score_map, int(t), 255, cv2.THRESH_BINARY)
        # small dilate then erode to merge tiny bits a touch
        kern = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3,3))
        bw = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, kern, iterations=1)
        return conn_comp_candidates(bw, min_area=4, max_area=400)

    red_cands  = thresh_and_candidates(red_score_map)
    blue_cands = thresh_and_candidates(blue_score_map)

    # 7) score candidates
    def local_contrast(gray_img, x, y, r_in=3, r_out=8):
        h, w = gray_img.shape[:2]
        y0, y1 = max(0,y-r_out), min(h,y+r_out+1)
        x0, x1 = max(0,x-r_out), min(w,x+r_out+1)
        patch = gray_img[y0:y1, x0:x1]
        if patch.size==0: return 0.0
        yy, xx = np.ogrid[y0:y1, x0:x1]
        rr = np.sqrt((xx-x)**2 + (yy-y)**2)
        spot = patch[rr <= r_in]
        ann  = patch[(rr > r_in) & (rr <= r_out)]
        if spot.size < 3 or ann.size < 10: return 0.0
        return float(max(0.0, np.percentile(spot,95) - np.median(ann)))

    def score_cands(cands, color_like_map):
        # derive per-candidate features
        scores=[]
        for d in cands:
            cx, cy = d["cx"], d["cy"]
            # pull maps at centroid
            dogv = float(dog_n[cy, cx])
            topv = float(top_n[cy, cx])
            colv = float(color_like_map[cy, cx])
            lc   = local_contrast(v, cx, cy, r_in=3, r_out=8)
            comp = float(d["compact"])
            # robust z-ish normalization is implicit via weights; keep simple
            s = 0.35*dogv + 0.20*topv + 0.20*lc + 0.15*colv + 0.10*(255.0*comp)
            scores.append({**d, "score": s})
        return sorted(scores, key=lambda x: x["score"], reverse=True)[:8]  # keep top N

    red_top  = score_cands(red_cands,  red_like)
    blue_top = score_cands(blue_cands, blue_like)

    if len(red_top) < 1 and len(blue_top) < 2:
        return None, None, {"why": "no strong candidates"}

    # 8) pair selection with geometry constraints
    def euclid(p,q): return float(np.hypot(p[0]-q[0], p[1]-q[1]))

    # try blue first (should be roughly horizontal wrt red midpoint later)
    best_blue=None; best_blue_s=-1e9
    for i in range(len(blue_top)):
        for j in range(i+1, len(blue_top)):
            p1=(blue_top[i]["cx"], blue_top[i]["cy"])
            p2=(blue_top[j]["cx"], blue_top[j]["cy"])
            dx, dy = abs(p1[0]-p2[0]), abs(p1[1]-p2[1])
            sep = euclid(p1,p2)
            if not (blue_sep_range[0] <= sep <= blue_sep_range[1]):
                continue
            # midpoint should be near droplet center
            mid=((p1[0]+p2[0])//2, (p1[1]+p2[1])//2)
            mid_d = euclid(mid, (cx,cy))
            horiz = max(0.0, dx - dy)
            pair_score = (blue_top[i]["score"] + blue_top[j]["score"]) + 0.5*horiz - 0.05*mid_d
            if pair_score > best_blue_s:
                best_blue_s = pair_score; best_blue = (p1,p2)

    # red: mostly vertical; use expected separation
    best_red=None; best_red_s=-1e9
    for i in range(len(red_top)):
        for j in range(i+1, len(red_top)):
            p1=(red_top[i]["cx"], red_top[i]["cy"])
            p2=(red_top[j]["cx"], red_top[j]["cy"])
            dx, dy = abs(p1[0]-p2[0]), abs(p1[1]-p2[1])
            sep = euclid(p1,p2)
            if abs(sep - red_expected_sep) > red_sep_tol:
                continue
            vert = max(0.0, dy - dx)
            pair_score = (red_top[i]["score"] + red_top[j]["score"]) + 0.7*vert - 0.2*abs(sep - red_expected_sep)
            if pair_score > best_red_s:
                best_red_s = pair_score; best_red = (p1,p2)

    # If one color missing, try to infer using the other
    if best_red is None and best_blue is not None:
        # fall back to vertical profile at blue midpoint (like your original)
        midx = (best_blue[0][0] + best_blue[1][0])//2
        # search only inside ring window columns
        # (use your existing fallback_red_detection if you prefer)
    if best_blue is None and best_red is not None:
        # infer blue along horizontal near red midpoint (can reuse your fallback_blue_detection)
        pass

    return best_red, best_blue, {
        "r_in": r_in, "r_out": r_out, "N_red": len(red_top), "N_blue": len(blue_top)
    }

def detect_droplet_center(gray_img, debug_folder=None, img_basename=""):
    # Step 1: Preprocessing
    blurred = cv2.GaussianBlur(gray_img, (9, 9), 0)

    # Step 2: Hough Circle Detection
    circles = cv2.HoughCircles(blurred, cv2.HOUGH_GRADIENT, dp=1.2, minDist=100,
                               param1=50, param2=30, minRadius=200, maxRadius=300)
    
    if circles is not None:
        circles = np.round(circles[0, :]).astype("int")
        cx, cy, r = circles[0] 
        if debug_folder:
            debug_img = cv2.cvtColor(gray_img, cv2.COLOR_GRAY2BGR)
            cv2.circle(debug_img, (cx, cy), r, (0, 255, 0), 2)
            cv2.circle(debug_img, (cx, cy), 5, (0, 255, 0), -1)
            debug_path = os.path.join(debug_folder, f"{img_basename}_hough_circle.jpg")
            cv2.imwrite(debug_path, debug_img)
            print(f"[DEBUG] Saved Hough circle detection: {os.path.basename(debug_path)}")
        return (cx, cy), None, 'hough' 

    # Step 3: Fallback: Threshold + Contour
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        raise ValueError("No contours found for droplet")

    # Filter contours by area or approximate diameter
    target_area_min = np.pi * (200)**2 * 0.5  # Rough min area for ~400px diameter
    target_area_max = np.pi * (300)**2 * 1.5  # Rough max area for ~600px diameter

    valid_contours = [cnt for cnt in contours if target_area_min < cv2.contourArea(cnt) < target_area_max]

    if not valid_contours:
        raise ValueError("No valid droplet contour found")

    largest = max(valid_contours, key=cv2.contourArea)
    M = cv2.moments(largest)
    if M["m00"] == 0:
        raise ValueError("Droplet center computation failed")

    cx = int(M["m10"] / M["m00"])
    cy = int(M["m01"] / M["m00"])

    if debug_folder:
        debug_img = cv2.cvtColor(gray_img, cv2.COLOR_GRAY2BGR)
        cv2.drawContours(debug_img, [largest], -1, (255, 255, 255), 2)
        cv2.circle(debug_img, (cx, cy), 5, (255, 255, 255), -1)
        debug_path = os.path.join(debug_folder, f"{img_basename}_contour_fallback.jpg")
        cv2.imwrite(debug_path, debug_img)
        print(f"[DEBUG] Saved contour fallback detection: {os.path.basename(debug_path)}")

    return (cx, cy), largest, 'contour'

def merge_close_centroids(centroids, distance_threshold=10):
    """
    Merge centroids that are close to each other. 
    This is necessary when LED reflections are larger than expected and accidentally detected as multiple centroids.
    """
    if not centroids:
        return []

    merged = []
    used = set()

    for i, c1 in enumerate(centroids):
        if i in used:
            continue
        cluster = [c1]
        for j, c2 in enumerate(centroids):
            if j <= i or j in used:
                continue
            if np.linalg.norm(np.array(c1) - np.array(c2)) < distance_threshold:
                cluster.append(c2)
                used.add(j)
        used.add(i)
        avg_x = int(np.mean([pt[0] for pt in cluster]))
        avg_y = int(np.mean([pt[1] for pt in cluster]))
        merged.append((avg_x, avg_y))

    return merged

def process_image(
    image_path,
    output_csv="auto_output.csv",
    debug=False,
    debug_folder=None,
    params: Optional[dict] = None,
    params_path: Optional[str] = None
):
    # ----------------------------
    # 0) Load params (if provided)
    # ----------------------------
    if params is None:
        params = load_led_params(params_path)

    base_name = os.path.splitext(os.path.basename(image_path))[0]

    # Defaults (will be overridden by params if present)
    red_min_area = 5
    blue_min_area = 5
    blue_max_area = 100  # cap spurious large blobs
    red_expected_direction = "vertical"
    midpoint_tolerance = 50

    red_lower = np.array([150, 0, 200], dtype=np.uint8)
    red_upper = np.array([170, 255, 255], dtype=np.uint8)
    blue_lower = np.array([85, 10, 200], dtype=np.uint8)
    blue_upper = np.array([100, 255, 255], dtype=np.uint8)

    search_radius = 100.0
    red_expected_sep = 80.0
    red_sep_tol = 30.0
    blue_sep_min, blue_sep_max = 40.0, 100.0

    if params:
        try:
            hv = params.get("hsv", {})
            if "red_lower" in hv:  red_lower = np.array(hv["red_lower"], dtype=np.uint8)
            if "red_upper" in hv:  red_upper = np.array(hv["red_upper"], dtype=np.uint8)
            if "blue_lower" in hv: blue_lower = np.array(hv["blue_lower"], dtype=np.uint8)
            if "blue_upper" in hv: blue_upper = np.array(hv["blue_upper"], dtype=np.uint8)
        except Exception:
            pass
        try:
            g = params.get("geometry", {})
            if "expected_red_separation_px" in g:
                red_expected_sep = float(g["expected_red_separation_px"])
            if "red_separation_tolerance_px" in g:
                red_sep_tol = float(g["red_separation_tolerance_px"])
            if "blue_separation_range_px" in g:
                blue_sep_min, blue_sep_max = [float(x) for x in g["blue_separation_range_px"]]
        except Exception:
            pass
        try:
            s = params.get("search", {})
            if "search_radius_px" in s:
                search_radius = float(s["search_radius_px"])
        except Exception:
            pass

    # ----------------------------
    # 1) Clean debug leftovers
    # ----------------------------
    if debug_folder and os.path.exists(debug_folder):
        debug_patterns = [
            f"{base_name}_debug.jpg",
            f"{base_name}_hough_circle.jpg",
            f"{base_name}_contour_fallback.jpg",
            f"{base_name}_red_profile_debug.png",
            f"{base_name}_fallback_debug.csv",
        ]
        cleaned_count = 0
        for pattern in debug_patterns:
            p = os.path.join(debug_folder, pattern)
            if os.path.exists(p):
                try:
                    os.remove(p); cleaned_count += 1
                except OSError as e:
                    print(f"[WARNING] Could not remove {pattern}: {e}")
        if cleaned_count > 0:
            print(f"[DEBUG] Cleaned {cleaned_count} old debug files for {base_name}")

    # ----------------------------
    # 2) Load + basic conversions
    # ----------------------------
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Could not read image at {image_path}")

    try:
        hsv_img = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    except Exception as e:
        raise ValueError(f"Failed to convert image to HSV: {e}")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    vis_image = image.copy()

        # If a YOLO weights path is given in params, try it first
    yolo_weights = None
    if params and "model" in params:
        yolo_weights = params["model"].get("yolo_pose_weights")

    if yolo_weights and os.path.exists(yolo_weights):
        try:
            from detect_leds_yolo import YOLOLedDetector, draw_points
            det = YOLOLedDetector(yolo_weights, device=None, conf=0.10)  # low conf to be forgiving
            red_pair, blue_pair, confs = det.detect(image)
            if red_pair and blue_pair:
                # compute distances and finish exactly like before
                red_dist  = float(np.hypot(red_pair[0][0]-red_pair[1][0], red_pair[0][1]-red_pair[1][1]))
                blue_dist = float(np.hypot(blue_pair[0][0]-blue_pair[1][0], blue_pair[0][1]-blue_pair[1][1]))
                # (optional sanity checks using your learned ranges)
                # draw & pack results
                vis_image = draw_points(image, red_pair, blue_pair)
                # fill your 'results' dict and return early
                hsv_img = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
                def hsv_at(p):
                    h,s,v = hsv_img[p[1], p[0]]; return {"x":p[0], "y":p[1], "h":int(h), "s":int(s), "v":int(v)}
                debug_img_path = os.path.join(debug_folder, f"{os.path.splitext(os.path.basename(image_path))[0]}_debug.jpg") if debug_folder else None
                if debug_img_path:
                    cv2.imwrite(debug_img_path, vis_image)
                return {
                    's_red_px': red_dist, 's_blue_px': blue_dist,
                    'droplet_center': {'x': int(image.shape[1]/2), 'y': int(image.shape[0]/2)},  # or your droplet center if you need it
                    'red_1': {'x': red_pair[0][0], 'y': red_pair[0][1]},
                    'red_2': {'x': red_pair[1][0], 'y': red_pair[1][1]},
                    'blue_1': {'x': blue_pair[0][0], 'y': blue_pair[0][1]},
                    'blue_2': {'x': blue_pair[1][0], 'y': blue_pair[1][1]},
                    'hsv_red1': hsv_at(red_pair[0]), 'hsv_red2': hsv_at(red_pair[1]),
                    'hsv_blue1': hsv_at(blue_pair[0]), 'hsv_blue2': hsv_at(blue_pair[1]),
                    'diagnostic_image_path': debug_img_path,
                    'diagnostic_image': vis_image,
                    'pixel_plot_path': None,
                    'image_path': image_path,
                    'image_name': os.path.splitext(os.path.basename(image_path))[0],
                    'droplet_detection_method': 'n/a',
                    'red_detection_method': 'yolo_pose',
                    'blue_detection_method': 'yolo_pose',
                    'confs': confs
                }
        except Exception as e:
            print(f"[WARN] YOLO pose inference failed, falling back to classical: {e}")


    # ----------------------------
    # 3) Droplet center
    # ----------------------------
    droplet_center, _, droplet_detection_method = detect_droplet_center(
        gray, debug_folder=debug_folder, img_basename=base_name
    )

    #----------------------------
    # 3.5) Optional colorless/specular detection first
    #----------------------------
    red_detection_method = 'centroid'
    blue_detection_method = 'centroid'

    ignore_color = False
    if params and "detection" in params:
        ignore_color = bool(params["detection"].get("ignore_color", False))

    used_specular = False
    red_pair = None
    blue_pair = None
    red_dist = None
    blue_dist = None
    pixel_plot_path = None  # set later if red fallback is used

    if ignore_color:
        red_pair2, blue_pair2, _spec_info = detect_led_pairs_specular_no_color(
            image_bgr=image,
            gray=gray,
            droplet_center=droplet_center,
            search_radius_px=search_radius,
            inner_ring_frac=0.25,   # adjust if needed
            outer_ring_frac=0.70,   # adjust if needed
            blue_sep_range=(blue_sep_min, blue_sep_max),
            red_expected_sep=red_expected_sep,
            red_sep_tol=red_sep_tol,
            debug_folder=debug_folder,
            base_name=base_name
        )
        if red_pair2 is not None and blue_pair2 is not None:
            red_pair = red_pair2
            blue_pair = blue_pair2
            red_detection_method = "specular_nocolor"
            blue_detection_method = "specular_nocolor"
            used_specular = True
            # distances + validation for specular path
            blue_dist = float(np.hypot(blue_pair[0][0]-blue_pair[1][0], blue_pair[0][1]-blue_pair[1][1]))
            red_dist  = float(np.hypot(red_pair[0][0]-red_pair[1][0],   red_pair[0][1]-red_pair[1][1]))
            if not (blue_sep_min <= blue_dist <= blue_sep_max):
                raise ValueError(f"Blue LED separation ({blue_dist:.1f}) outside valid range [{blue_sep_min:.0f}-{blue_sep_max:.0f}] px")
            red_min_ok = max(50.0, red_expected_sep - red_sep_tol)
            if not (red_min_ok <= red_dist <= red_expected_sep + red_sep_tol):
                raise ValueError(f"Red LED separation ({red_dist:.1f}) outside valid range [{red_min_ok:.0f}-{red_expected_sep + red_sep_tol:.0f}] px")

    # ----------------------------
    # 4) Masks (use learned HSV) – still useful for debug/overlay
    # ----------------------------
    red_mask  = cv2.inRange(hsv_img, red_lower,  red_upper)
    blue_mask = cv2.inRange(hsv_img, blue_lower, blue_upper)

    # ----------------------------
    # 5) Helpers
    # ----------------------------
    def get_centroids(mask, min_area, max_area=np.inf, center=None, radius=None):
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        centroids = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if not (min_area <= area <= max_area):
                continue
            M = cv2.moments(cnt)
            if M["m00"] == 0:
                continue
            cx, cy = int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"])
            if center is not None and radius is not None:
                if np.hypot(cx - center[0], cy - center[1]) > radius:
                    continue
            centroids.append((cx, cy))
        return centroids

    def best_aligned_pair(centroids, direction="vertical"):
        best_pair, best_score = None, -np.inf
        for p1, p2 in combinations(centroids, 2):
            dx, dy = abs(p1[0] - p2[0]), abs(p1[1] - p2[1])
            score = dy - dx if direction == "vertical" else dx - dy
            if score > best_score:
                best_score, best_pair = score, (p1, p2)
        return best_pair

    def midpoint(p1, p2):
        return ((p1[0] + p2[0]) // 2, (p1[1] + p2[1]) // 2)

    def best_blue_pair_aligned_with_red(centroids, red_mid, tol):
        best_pair, best_score = None, -np.inf
        for p1, p2 in combinations(centroids, 2):
            dx, dy = abs(p1[0] - p2[0]), abs(p1[1] - p2[1])
            mid_x, mid_y = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
            dist_to_red = np.hypot(mid_x - red_mid[0], mid_y - red_mid[1])
            if dist_to_red > tol:
                continue
            score = dx - dy - dist_to_red
            if score > best_score:
                best_score, best_pair = score, (p1, p2)
        return best_pair

    def euclidean(p1, p2):
        return float(np.hypot(p1[0] - p2[0], p1[1] - p2[1]))

    def hsv_at(p):
        h, s, v = hsv_img[p[1], p[0]]
        return {"x": p[0], "y": p[1], "h": int(h), "s": int(s), "v": int(v)}

    # ----------------------------
    # 6) Centroids (respect search_radius) – used for overlay/refine
    # ----------------------------
    red_centroids  = merge_close_centroids(
        get_centroids(red_mask,  red_min_area, center=droplet_center, radius=search_radius),
        distance_threshold=15
    )
    blue_centroids = merge_close_centroids(
        get_centroids(blue_mask, blue_min_area, blue_max_area, center=droplet_center, radius=search_radius),
        distance_threshold=15
    )

    # ----------------------------
    # 7) Fallbacks (profile-based helpers)
    # ----------------------------
    def save_debug_csv(debug_folder, img_basename, rows):
        if debug_folder:
            csv_path = os.path.join(debug_folder, f"{img_basename}_fallback_debug.csv")
            with open(csv_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Image", "Check", "Reason", "Y1", "Int1", "Y2", "Int2",
                                 "Separation Y", "Euclidean Dist", "Mean Intensity"])
                writer.writerows(rows)

    def fallback_red_detection(gray_img, droplet_center, blue_pair=None,
                               width=40, min_distance=10,
                               expected_separation=80, separation_tolerance=20,
                               debug_folder=None, img_basename=""):
        if blue_pair is not None:
            x_center = (blue_pair[0][0] + blue_pair[1][0]) // 2
        else:
            x_center = droplet_center[0]
        y_center = droplet_center[1]

        sr = int(max(1, round(search_radius)))
        half_width = width // 2
        x_start = max(0, x_center - half_width)
        x_end   = min(gray_img.shape[1], x_center + half_width)
        y_start = max(0, y_center - sr)
        y_end   = min(gray_img.shape[0], y_center + sr)

        strip = gray_img[y_start:y_end, x_start:x_end]
        profile = np.mean(strip, axis=1)
        profile_smooth = cv2.GaussianBlur(profile[:, np.newaxis], (1, 11), 0).flatten()

        peaks, properties = scipy.signal.find_peaks(profile_smooth, distance=min_distance, prominence=2)
        debug_rows = []

        if debug_folder:
            plt.figure(figsize=(6, 4))
            plt.plot(profile_smooth, label='Smoothed Intensity')
            if peaks.size:
                plt.plot(peaks, profile_smooth[peaks], 'rx', label='Detected Peaks')
            plt.axhline(y=float(np.mean(profile_smooth)), color='gray', linestyle='--', label='Mean Level')
            plt.title('Vertical Intensity Profile (Red Fallback)')
            plt.legend(); plt.tight_layout()
            plot_path = os.path.join(debug_folder, f"{img_basename}_red_profile_debug.png")
            plt.savefig(plot_path); plt.close()
            print(f"[DEBUG] Saved red intensity profile: {os.path.basename(plot_path)}")

        if len(peaks) < 2:
            debug_rows.append([img_basename, "Not enough peaks found for pairing.", "", "", "", "", "", "", "", ""])
            save_debug_csv(debug_folder, img_basename, debug_rows)
            return None

        best_pair = None
        best_score = np.inf
        for i in range(len(peaks)):
            for j in range(i + 1, len(peaks)):
                y1_rel, y2_rel = peaks[i], peaks[j]
                y1, y2 = y1_rel + y_start, y2_rel + y_start
                separation_y = abs(y2 - y1)
                x1 = x_center; x2 = x_center
                intensity1 = float(profile_smooth[y1_rel])
                intensity2 = float(profile_smooth[y2_rel])
                intensity_diff = abs(intensity1 - intensity2)
                euclid_v = float(abs(y2 - y1))  # vertical line
                mean_int = (intensity1 + intensity2) / 2.0
                separation_error = abs(separation_y - expected_separation)
                reason = ("Accepted" if (expected_separation - separation_tolerance
                                         <= separation_y
                                         <= expected_separation + separation_tolerance)
                          else "Rejected: separation outside expected range")
                debug_rows.append([
                    img_basename, f"Pair ({y1}, {y2})", reason,
                    f"{y1}", f"{intensity1:.2f}",
                    f"{y2}", f"{intensity2:.2f}",
                    f"{separation_y}", f"{euclid_v:.2f}", f"{mean_int:.2f}"
                ])
                score = intensity_diff + separation_error
                if score < best_score:
                    best_score = score
                    best_pair = ((x1, y1), (x2, y2))

        if best_pair:
            save_debug_csv(debug_folder, img_basename, debug_rows)
            print(f"[DEBUG] Saved red fallback CSV: {img_basename}_fallback_debug.csv")
            return best_pair

        if len(peaks) == 1 and blue_pair is not None:
            found_y = int(peaks[0] + y_start)
            blue_mid_y = (blue_pair[0][1] + blue_pair[1][1]) // 2
            mirror_y = int(np.clip(2 * blue_mid_y - found_y, 0, gray_img.shape[0] - 1))
            debug_rows.append([img_basename, f"Only one peak: {found_y}", f"Mirrored to {mirror_y}",
                               f"{found_y}", f"{profile_smooth[peaks[0]]:.2f}",
                               "", "", "", "", ""])
            save_debug_csv(debug_folder, img_basename, debug_rows)
            return (x_center, found_y), (x_center, mirror_y)

        debug_rows.append([img_basename, "No valid red pair found after all checks.", "", "", "", "", "", "", "", ""])
        save_debug_csv(debug_folder, img_basename, debug_rows)
        return None

    def fallback_blue_detection(gray_img, droplet_center, height=20, min_distance=30, search_radius=100):
        y_center = droplet_center[1]
        x_center = droplet_center[0]
        half_height = height // 2
        y_start = max(0, y_center - half_height)
        y_end   = min(gray_img.shape[0], y_center + half_height)
        sr = int(max(1, round(search_radius)))
        x_start = max(0, x_center - sr)
        x_end   = min(gray_img.shape[1], x_center + sr)
        strip = gray_img[y_start:y_end, x_start:x_end]
        profile = np.mean(strip, axis=0)
        profile_smooth = cv2.GaussianBlur(profile[:, np.newaxis], (11, 1), 0).flatten()
        peaks, _ = scipy.signal.find_peaks(profile_smooth, distance=min_distance)
        if len(peaks) >= 2:
            intens = profile_smooth[peaks]
            order = np.argsort(-intens)[:2]
            p1_x_rel, p2_x_rel = peaks[order[0]], peaks[order[1]]
            p1 = (int(p1_x_rel + x_start), int(y_center))
            p2 = (int(p2_x_rel + x_start), int(y_center))
            return p1, p2
        return None

    # ----------------------------
    # 8) Blue then red (HSV/centroid path) – ONLY if not used_specular
    # ----------------------------
    if not used_specular:
        # Initial blue using droplet center
        blue_pair = best_blue_pair_aligned_with_red(blue_centroids, droplet_center, tol=midpoint_tolerance)
        if not blue_pair:
            blue_pair = fallback_blue_detection(gray, droplet_center, height=20, min_distance=30, search_radius=search_radius)
            blue_detection_method = 'fallback'
            if not blue_pair:
                raise ValueError("Could not find valid blue LED pair")

        blue_dist = euclidean(*blue_pair)
        if not (blue_sep_min <= blue_dist <= blue_sep_max):
            raise ValueError(f"Blue LED separation ({blue_dist:.1f}) outside valid range [{blue_sep_min:.0f}-{blue_sep_max:.0f}] px")
        if blue_dist > 1.5 * search_radius:  # sanity vs search radius
            raise ValueError(f"Blue LED separation ({blue_dist:.1f}) exceeds search radius constraint")

        # Red using centroids; then fallback with learned expectations
        red_pair = best_aligned_pair(red_centroids, direction=red_expected_direction)
        if not red_pair:
            red_detection_method = 'fallback'
            red_pair = fallback_red_detection(
                gray,
                droplet_center,
                blue_pair=blue_pair,
                expected_separation=red_expected_sep,
                separation_tolerance=red_sep_tol,
                debug_folder=debug_folder,
                img_basename=base_name
            )
            if debug_folder:
                pixel_plot_path = os.path.join(debug_folder, f"{base_name}_red_profile_debug.png")
            if red_pair is None:
                if debug_folder:
                    cv2.putText(vis_image, "No red pair found", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    cv2.imwrite(os.path.join(debug_folder, f"{base_name}_debug.jpg"), vis_image)
                raise ValueError("Could not find valid red LED pair")

        red_dist = euclidean(*red_pair)
        red_min_ok = max(50.0, red_expected_sep - red_sep_tol)
        if not (red_min_ok <= red_dist <= red_expected_sep + red_sep_tol):
            raise ValueError(f"Red LED separation ({red_dist:.1f}) outside valid range [{red_min_ok:.0f}-{red_expected_sep + red_sep_tol:.0f}] px")

    # ----------------------------
    # 9) Optional refine blue using red midpoint (both paths)
    # ----------------------------
    red_mid = midpoint(*red_pair)
    refined_blue = best_blue_pair_aligned_with_red(blue_centroids, red_mid, tol=midpoint_tolerance)
    if refined_blue:
        ref_dist = euclidean(*refined_blue)
        if (blue_sep_min <= ref_dist <= blue_sep_max) and (ref_dist <= 1.5 * search_radius):
            blue_pair = refined_blue
            blue_dist = ref_dist

    # ----------------------------
    # 10) HSV at LED pixels + draw
    # ----------------------------
    hsv_red1  = hsv_at(red_pair[0]);  hsv_red2  = hsv_at(red_pair[1])
    hsv_blue1 = hsv_at(blue_pair[0]); hsv_blue2 = hsv_at(blue_pair[1])

    cv2.circle(vis_image, droplet_center, 5, (255, 255, 255), -1)
    for c in red_centroids:
        cv2.circle(vis_image, c, 3, (0, 0, 255), -1)
    for c in blue_centroids:
        cv2.circle(vis_image, c, 3, (255, 0, 0), -1)

    cv2.circle(vis_image, red_pair[0],  3, (0, 0, 255), -1)
    cv2.circle(vis_image, red_pair[1],  3, (0, 0, 255), -1)
    cv2.circle(vis_image, blue_pair[0], 3, (255, 0, 0), -1)
    cv2.circle(vis_image, blue_pair[1], 3, (255, 0, 0), -1)

    debug_img_path = None
    if debug_folder:
        debug_img_path = os.path.join(debug_folder, f"{base_name}_debug.jpg")
        cv2.imwrite(debug_img_path, vis_image)
        print(f"[DEBUG] Saved final debug image: {os.path.basename(debug_img_path)}")

    # ----------------------------
    # 11) Results
    # ----------------------------
    results = {
        's_red_px': red_dist,
        's_blue_px': blue_dist,
        'droplet_center': {'x': droplet_center[0], 'y': droplet_center[1]},
        'red_1': {'x': red_pair[0][0], 'y': red_pair[0][1]},
        'red_2': {'x': red_pair[1][0], 'y': red_pair[1][1]},
        'blue_1': {'x': blue_pair[0][0], 'y': blue_pair[0][1]},
        'blue_2': {'x': blue_pair[1][0], 'y': blue_pair[1][1]},
        'hsv_red1': hsv_red1, 'hsv_red2': hsv_red2,
        'hsv_blue1': hsv_blue1, 'hsv_blue2': hsv_blue2,
        'diagnostic_image_path': debug_img_path,
        'diagnostic_image': vis_image,
        'pixel_plot_path': pixel_plot_path,
        'image_path': image_path,
        'image_name': base_name,
        'droplet_detection_method': droplet_detection_method,
        'red_detection_method': red_detection_method,
        'blue_detection_method': blue_detection_method
    }
    return results


def process_z_stack_then_measure(
    image_paths_for_one_stack: List[str],
    output_csv="auto_output.csv",
    debug=False,
    debug_folder=None,
    expect_red_sep=80.0,
    red_sep_tol=30.0,
    params_path=None,
    params=None
):
    best_path, log = select_best_focus_frame(
        image_paths_for_one_stack,
        debug_folder=debug_folder,
        expect_red_sep=expect_red_sep,
        red_sep_tol=red_sep_tol,
    )
    # Now run your existing detector on the chosen image
    results = process_image(best_path, output_csv=output_csv, debug=debug, debug_folder=debug_folder,
                             params=params, params_path=params_path)
    results["chosen_best_focus_image"] = best_path
    results["focus_ranking"] = log["ranked"]
    return results

# Example usage:
'''
python -m ContactAngleScriptsForPANDAV2.Batch_ContactangleLED `
    "D:\1-PhD\4-RawData\2025\2025-07-02" `
    --output_folder "D:\1-PhD\4-RawData\2025\2025-07-02\analysis_part3" `
    --params_path "D:\1-PhD\3-Research\Publications\PANDA-V2\pama_peo_training\led_params.json" `
    --debug


#no Z-stack
python -m ContactAngleScriptsForPANDAV2.Batch_ContactangleLED `
"D:\1-PhD\4-RawData\2025\2025-07-02" `
--output_folder "D:\1-PhD\4-RawData\2025\2025-07-02\analysis_part3" --all_images --debug

#z-stack
python -m ContactAngleScriptsForPANDAV2.Batch_ContactangleLED `
    "D:\1-PhD\4-RawData\2025\2025-07-02" `
    --output_folder "D:\1-PhD\4-RawData\2025\2025-07-02\analysis_part3" `
    --params_path "D:\1-PhD\3-Research\Publications\PANDA-V2\pama_peo_training\led_params.json" `
    --debug

'''
# python -m ContactAngleScriptsForPANDAV2.Batch_ContactangleLED D:\1-PhD\3-Research\Publications\PANDA-V2\pama_peo_training\CA_images --output D:\1-PhD\3-Research\Publications\PANDA-V2\pama_peo_training\analysis --debug
# python -m ContactAngleScriptsForPANDAV2.Batch_ContactangleLED.py D:\1-PhD\4-RawData\2025\2025-07-08\contact_angle_experiment_2025-07-08_152937\ --output D:\1-PhD\4-RawData\2025\2025-07-08\analysis_part2\ --debug
# D:\1-PhD\4-RawData\2025\pama_trainingdata
# D:\1-PhD\4-RawData\2025\2025-07-08\contact_angle_experiment_2025-07-08_152937
# D:\1-PhD\3-Research\Publications\PANDA-V2\PAMA_drying
# D:\1-PhD\3-Research\Publications\PANDA-V2\pama_peo_training