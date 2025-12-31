import math
import cv2
import numpy as np
import csv
import os
import re
import argparse
from typing import Dict, List, Tuple, Optional

from .ContactAngle_LEDdetect import process_z_stack_then_measure, extract_z_mm_from_name, process_image

# Helpers to group images into stacks (by well and position)
WELL_RE = re.compile(r"\b([A-Ha-h][1-9]\d?)\b")
SLIDE_RE = re.compile(r"\bslide[_-]?(\d+)\b", re.IGNORECASE)
POS_RE   = re.compile(r"\bpos[_-]?([A-Ha-h])\b", re.IGNORECASE)

def _safe_lower(s: str) -> str:
    return s.lower() if isinstance(s, str) else ""

def extract_stack_key(fname: str) -> str:
    """
    Build a stack key (group ID) from typical filename parts.
    Priority:
      1) WELL like 'B5' if present
      2) slideN + posX combo if present
      3) fallback to filename with 'z...' removed (stable across z-slices)
    """
    base = os.path.basename(fname)
    low  = _safe_lower(base)

    # 1) Try direct well like B5 / A1
    m_well = WELL_RE.search(base)
    if m_well:
        well = m_well.group(1).upper()
        # include slide/pos if available for uniqueness across slides
        m_slide = SLIDE_RE.search(low)
        m_pos   = POS_RE.search(low)
        slide = f"slide{m_slide.group(1)}" if m_slide else ""
        pos   = f"pos{m_pos.group(1).upper()}" if m_pos else ""
        parts = [p for p in [slide, pos, f"well{well}"] if p]
        return "_".join(parts)

    # 2) Try slide + pos (e.g., slide1_posA)
    m_slide = SLIDE_RE.search(low)
    m_pos   = POS_RE.search(low)
    if m_slide or m_pos:
        slide = f"slide{m_slide.group(1)}" if m_slide else ""
        pos   = f"pos{m_pos.group(1).upper()}" if m_pos else ""
        parts = [p for p in [slide, pos] if p]
        if parts:
            return "_".join(parts)

    # 3) Fallback: strip a 'z-...' segment so all z-slices collapse to same key
    # Matches both z-40-00mm and z-39.5 forms
    no_z = re.sub(r"z-?\d+(?:-\d+)?mm", "z", low)          # remove z-40-00mm → 'z'
    no_z = re.sub(r"z-?\d+(?:\.\d+)?", "z", no_z)          # remove z-39.5     → 'z'
    # also drop trailing image index parts like '_image_0'
    no_idx = re.sub(r"_image_\d+\b", "", no_z)
    # Key = filename without extension after the removals
    key = os.path.splitext(no_idx)[0]
    return key

def group_images_into_stacks(image_paths: List[str]) -> Dict[str, List[str]]:
    """
    Returns dict: { stack_key: [paths...] }
    """
    stacks: Dict[str, List[str]] = {}
    for p in image_paths:
        key = extract_stack_key(p)
        stacks.setdefault(key, []).append(p)
    return stacks

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch process Z-stacks: auto-pick in-focus frame, then measure LED distances.")
    parser.add_argument("input_folder", help="Path to folder containing images")
    parser.add_argument("--output_folder", required=True, help="Path to save CSV and debug images")
    parser.add_argument("--debug", action="store_true", help="Enable debug visualization")
    # Optional tunables for focus selection (match your LED geometry expectations)
    parser.add_argument("--expect_red_sep", type=float, default=80.0, help="Expected pixel separation for red LED pair")
    parser.add_argument("--red_sep_tol", type=float, default=30.0, help="Tolerance (±px) for red LED separation")
    parser.add_argument("--params_path", type=str, help="Path to led_params.json")
    parser.add_argument("--all_images", action="store_true", help="Process each image individually (skip z-stack focus selection). Ignores --params_path."
)

    args = parser.parse_args()

    input_folder = args.input_folder
    output_folder = args.output_folder
    debug = args.debug
    expect_red_sep = args.expect_red_sep
    red_sep_tol = args.red_sep_tol

    os.makedirs(output_folder, exist_ok=True)
    
    # Find images
    
    exts = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp")
    images = [os.path.join(input_folder, f)
              for f in os.listdir(input_folder)
              if f.lower().endswith(exts)]

    if not images:
        raise SystemExit(f"No images found in {input_folder}")

    output_csv = os.path.join(output_folder, "output.csv")

    # Common header for both modes (FocusScore/ChosenZ_mm will be blank in --all_images mode)
    HEADER = [
        "StackKey",
        "ChosenImage",
        "ChosenZ_mm",
        "FocusScore",
        "s_red_px",
        "s_blue_px",
        "Red1_Y", "Red1_X", "Red1_H", "Red1_S", "Red1_V",
        "Red2_Y", "Red2_X", "Red2_H", "Red2_S", "Red2_V",
        "Blue1_Y", "Blue1_X", "Blue1_H", "Blue1_S", "Blue1_V",
        "Blue2_Y", "Blue2_X", "Blue2_H", "Blue2_S", "Blue2_V",
        "DropletCenter_X", "DropletCenter_Y",
        "DropletCenter_to_ImageCenter_px",
        "RedMethod", "BlueMethod", "DropletMethod"
    ]

    with open(output_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(HEADER)

        if args.all_images:
            # --- Simple pass: every image individually, no z-stack, ignore params ---
            images_sorted = sorted(images)
            print(f"Processing {len(images_sorted)} images individually (no z-stack).")

            for p in images_sorted:
                try:
                    res = process_image(
                        p,
                        output_csv=None,
                        debug=debug,
                        debug_folder=output_folder,
                        params=None,         # <-- ignore params
                        params_path=None,    # <-- ignore params file
                    )

                    img_name = os.path.basename(p)
                    chosen_z = extract_z_mm_from_name(img_name)
                    red_dist = res["s_red_px"]
                    blue_dist = res["s_blue_px"]
                    hsv_red1 = res["hsv_red1"]; hsv_red2 = res["hsv_red2"]
                    hsv_blue1 = res["hsv_blue1"]; hsv_blue2 = res["hsv_blue2"]
                    droplet_center = res.get("droplet_center", {})
                    red_m  = res.get("red_detection_method", "")
                    blue_m = res.get("blue_detection_method", "")
                    drop_m = res.get("droplet_detection_method", "")
                                        
                    img = cv2.imread(p)
                    H, W = img.shape[:2] if img is not None else (None, None)

                    # Compute distance (pixels) from droplet center to image center
                    if H is not None and W is not None and "x" in droplet_center and "y" in droplet_center:
                        icx, icy = W / 2.0, H / 2.0
                        dx = float(droplet_center["x"]) - icx
                        dy = float(droplet_center["y"]) - icy
                        center_dist = f"{math.hypot(dx, dy):.3f}"
                    else:
                        center_dist = ""

                    row = [
                        # StackKey: use base filename as a simple key in this mode
                        os.path.splitext(img_name)[0],
                        img_name,
                        f"{chosen_z}" if chosen_z is not None else "",
                        "",  # FocusScore blank in all-images mode
                        f"{red_dist:.3f}",
                        f"{blue_dist:.3f}",
                        hsv_red1["y"], hsv_red1["x"], hsv_red1["h"], hsv_red1["s"], hsv_red1["v"],
                        hsv_red2["y"], hsv_red2["x"], hsv_red2["h"], hsv_red2["s"], hsv_red2["v"],
                        hsv_blue1["y"], hsv_blue1["x"], hsv_blue1["h"], hsv_blue1["s"], hsv_blue1["v"],
                        hsv_blue2["y"], hsv_blue2["x"], hsv_blue2["h"], hsv_blue2["s"], hsv_blue2["v"],
                        droplet_center.get("x", ""), droplet_center.get("y", ""),
                        center_dist,
                        red_m, blue_m, drop_m,
                    ]
                    writer.writerow(row)
                    print(f"[OK] {img_name}: Red={red_dist:.2f}  Blue={blue_dist:.2f}")

                except Exception as e:
                    print(f"[ERROR] Failed on image '{p}': {e}")

        else:
            # --- Original z-stack mode ---
            stacks = group_images_into_stacks(images)
            print(f"Found {len(stacks)} stacks.")

            for stack_key, paths in stacks.items():
                # sort by parsed Z so logs read nicely
                decorated = []
                for p in paths:
                    z = extract_z_mm_from_name(p)
                    z_sort = z if z is not None else float("inf")
                    decorated.append((z_sort, p))
                decorated.sort(key=lambda t: t[0])
                sorted_paths = [p for _, p in decorated]

                try:
                    results = process_z_stack_then_measure(
                        sorted_paths,
                        output_csv=None,              # CSV handled here
                        debug=debug,
                        debug_folder=output_folder,
                        expect_red_sep=expect_red_sep,
                        red_sep_tol=red_sep_tol,
                        params_path=args.params_path
                    )

                    chosen_path = results.get("chosen_best_focus_image", results["image_path"])
                    chosen_name = os.path.basename(chosen_path)
                    chosen_z = extract_z_mm_from_name(chosen_name)

                    # focus score for the chosen image
                    score = ""
                    fr = results.get("focus_ranking", [])
                    for item in fr:
                        # os.path.samefile may fail across drives; fallback to basename match if needed:
                        try:
                            same = os.path.samefile(item["path"], chosen_path)
                        except Exception:
                            same = (os.path.basename(item["path"]) == os.path.basename(chosen_path))
                        if same:
                            score = f'{item["score"]:.3f}'
                            break

                    red_dist = results["s_red_px"]
                    blue_dist = results["s_blue_px"]
                    hsv_red1 = results["hsv_red1"]; hsv_red2 = results["hsv_red2"]
                    hsv_blue1 = results["hsv_blue1"]; hsv_blue2 = results["hsv_blue2"]
                    droplet_center = results.get("droplet_center", {})
                    red_m  = results.get("red_detection_method", "")
                    blue_m = results.get("blue_detection_method", "")
                    drop_m = results.get("droplet_detection_method", "")
                    img = cv2.imread(chosen_path)
                    H, W = img.shape[:2] if img is not None else (None, None)

                    if H is not None and W is not None and "x" in droplet_center and "y" in droplet_center:
                        icx, icy = W / 2.0, H / 2.0
                        dx = float(droplet_center["x"]) - icx
                        dy = float(droplet_center["y"]) - icy
                        center_dist = f"{math.hypot(dx, dy):.3f}"
                    else:
                        center_dist = ""

                    row = [
                        stack_key,
                        chosen_name,
                        f"{chosen_z}" if chosen_z is not None else "",
                        score,
                        f"{red_dist:.3f}",
                        f"{blue_dist:.3f}",
                        hsv_red1["y"], hsv_red1["x"], hsv_red1["h"], hsv_red1["s"], hsv_red1["v"],
                        hsv_red2["y"], hsv_red2["x"], hsv_red2["h"], hsv_red2["s"], hsv_red2["v"],
                        hsv_blue1["y"], hsv_blue1["x"], hsv_blue1["h"], hsv_blue1["s"], hsv_blue1["v"],
                        hsv_blue2["y"], hsv_blue2["x"], hsv_blue2["h"], hsv_blue2["s"], hsv_blue2["v"],
                        droplet_center.get("x", ""), droplet_center.get("y", ""),
                        center_dist,
                        red_m, blue_m, drop_m,
                    ]
                    writer.writerow(row)
                    print(f"[OK] {stack_key}: picked {chosen_name} (z={chosen_z}, score={score})  Red={red_dist:.2f}  Blue={blue_dist:.2f}")

                except Exception as e:
                    print(f"[ERROR] Failed on stack '{stack_key}' with {len(paths)} images: {e}")
