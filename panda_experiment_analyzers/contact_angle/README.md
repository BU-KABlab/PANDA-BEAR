# Contact Angle Analysis Scripts

This module provides tools for estimating contact angle from top-down LED reflection images. The workflow uses dual-color LED reflections (red and blue) on a droplet surface to measure distances that correlate with contact angle.

## Overview

The contact angle measurement system works by:
1. Capturing top-down images of a droplet with red and blue LED pairs positioned above
2. Detecting the LED reflections on the droplet surface
3. Measuring the separation distances between LED pairs (`s_red_px`, `s_blue_px`)
4. Using a trained regression model to predict contact angle from these distances

## Module Structure

```
contact_angle/
├── __init__.py                              # Module exports
├── contact_angle_classes.py                 # Data classes and type definitions
├── contact_angle_led_detect.py              # Core LED detection algorithms
├── batch_contact_angle_led.py               # Batch processing for z-stacks
├── contact_angle_train_regression_model.py  # Model training (creates .pkl)
├── contact_angle_predict_ca_regression_model.py  # Contact angle prediction
├── contact_angle_ml_gpr_model.py            # Bayesian optimization with GP
├── contact_angle_plots_regression_model.py  # Visualization utilities
├── experiment_generator.py                  # PANDA experiment generation
├── ml_input.py                              # ML model input data handling
├── sql_ml_functions.py                      # Database operations
└── README.md                                # This file
```

---

## Quick Start

### 1. Process a Single Image

```python
from panda_experiment_analyzers.contact_angle import process_image

# Detect LED positions in an image
result = process_image(
    image_path="path/to/image.jpg",
    debug=True,
    debug_folder="path/to/output/"
)

print(f"Red LED distance: {result['s_red_px']:.2f} px")
print(f"Blue LED distance: {result['s_blue_px']:.2f} px")
```

### 2. Predict Contact Angle

```python
from panda_experiment_analyzers.contact_angle import predict_point

# Predict contact angle from LED distances
predict_point(
    model_path="path/to/contact_angle_poly_model.pkl",
    s_red=85.5,
    s_blue=72.3,
    show_equation=True
)
# Output: Prediction θ ≈ 45.123°  (s_red_px=85.5, s_blue_px=72.3)
```

---

## Detailed Usage

### LED Detection (`contact_angle_led_detect.py`)

This is the core module for detecting LED reflections in images.

#### `process_image()`
Processes a single image to detect LED positions.

```python
from panda_experiment_analyzers.contact_angle.contact_angle_led_detect import process_image

result = process_image(
    image_path="image.jpg",
    output_csv=None,           # Optional: path to save results
    debug=True,                # Generate debug visualizations
    debug_folder="./debug/",   # Where to save debug images
    params=None,               # Optional: dict of detection parameters
    params_path="led_params.json"  # Optional: path to JSON config
)

# Result dictionary contains:
# - s_red_px: Distance between red LED pair (pixels)
# - s_blue_px: Distance between blue LED pair (pixels)
# - droplet_center: {x, y} coordinates of droplet center
# - red_1, red_2: {x, y} coordinates of red LED positions
# - blue_1, blue_2: {x, y} coordinates of blue LED positions
# - hsv_red1, hsv_red2, hsv_blue1, hsv_blue2: HSV values at LED positions
# - diagnostic_image: Annotated image (numpy array)
# - detection methods used (hough/contour, centroid/fallback, etc.)
```

#### `process_z_stack_then_measure()`
For z-stack images, automatically selects the best-focused frame.

```python
from panda_experiment_analyzers.contact_angle.contact_angle_led_detect import (
    process_z_stack_then_measure
)

result = process_z_stack_then_measure(
    image_paths_for_one_stack=["z40.jpg", "z41.jpg", "z42.jpg"],
    debug=True,
    debug_folder="./debug/",
    expect_red_sep=80.0,    # Expected red LED separation (pixels)
    red_sep_tol=30.0,       # Tolerance for red separation
    params_path="led_params.json"
)

# Additional result keys:
# - chosen_best_focus_image: Path to the selected frame
# - focus_ranking: List of all frames with their focus scores
```

---

### Batch Processing (`batch_contact_angle_led.py`)

Process entire folders of images, automatically grouping z-stacks.

#### Command Line Usage

```bash
# Process z-stacks (auto-select best focus)
python -m panda_experiment_analyzers.contact_angle.batch_contact_angle_led \
    /path/to/images \
    --output_folder /path/to/output \
    --params_path led_params.json \
    --debug

# Process all images individually (no z-stack grouping)
python -m panda_experiment_analyzers.contact_angle.batch_contact_angle_led \
    /path/to/images \
    --output_folder /path/to/output \
    --all_images \
    --debug
```

#### Output CSV Columns

| Column | Description |
|--------|-------------|
| `StackKey` | Identifier for the z-stack or image group |
| `ChosenImage` | Filename of the processed/selected image |
| `ChosenZ_mm` | Z-position extracted from filename (if available) |
| `FocusScore` | Focus quality score (higher = sharper) |
| `s_red_px` | Red LED pair separation (pixels) |
| `s_blue_px` | Blue LED pair separation (pixels) |
| `Red1_Y/X/H/S/V` | Position and HSV values for first red LED |
| `Red2_Y/X/H/S/V` | Position and HSV values for second red LED |
| `Blue1_Y/X/H/S/V` | Position and HSV values for first blue LED |
| `Blue2_Y/X/H/S/V` | Position and HSV values for second blue LED |
| `DropletCenter_X/Y` | Detected droplet center coordinates |
| `DropletCenter_to_ImageCenter_px` | Distance from droplet to image center |
| `RedMethod` | Detection method used for red LEDs |
| `BlueMethod` | Detection method used for blue LEDs |
| `DropletMethod` | Detection method used for droplet |

---

### Model Training (`contact_angle_train_regression_model.py`)

Train a polynomial regression model from calibration data (images with known contact angles).

#### Preparing Training Data

You need a CSV file with these columns:
- `s_red_px`: Red LED pair separation (from `batch_contact_angle_led.py` output)
- `s_blue_px`: Blue LED pair separation (from `batch_contact_angle_led.py` output)
- `theta_side_deg`: Ground truth contact angle measured via side-view goniometer

Example training CSV:
```csv
s_red_px,s_blue_px,theta_side_deg
85.2,72.1,45.3
88.7,75.4,52.1
82.1,68.9,38.7
...
```

#### Command Line Usage

```bash
# Basic training
python -m panda_experiment_analyzers.contact_angle.contact_angle_train_regression_model \
    --train-csv calibration_data.csv \
    --out-model contact_angle_poly_model.pkl

# With plots and full diagnostics
python -m panda_experiment_analyzers.contact_angle.contact_angle_train_regression_model \
    --train-csv calibration_data.csv \
    --out-model contact_angle_poly_model.pkl \
    --plots-dir ./training_plots \
    --cv-folds 5 \
    --show-equation
```

#### Command Line Options

| Option | Description |
|--------|-------------|
| `--train-csv` | Path to training CSV (required) |
| `--out-model` | Path to save model .pkl file (required) |
| `--degree` | Polynomial degree (default: 2) |
| `--plots-dir` | Directory for training plots |
| `--cv-folds` | Cross-validation folds, 0 to skip (default: 5) |
| `--show-equation` | Print explicit polynomial equation |

#### Python API

```python
from panda_experiment_analyzers.contact_angle import train_model

# Train and save model
pipeline = train_model(
    train_csv="calibration_data.csv",
    out_model="contact_angle_poly_model.pkl",
    degree=2,
    plots_dir="./training_plots",
    show_equation=True,
    cv_folds=5,
)
```

#### Output

The training script produces:
- **Model file** (`.pkl`): Serialized sklearn Pipeline
- **Parity plot**: Predicted vs actual contact angles
- **Residual plots**: Residuals vs predicted, histogram
- **Surface plot**: 3D visualization of the polynomial surface
- **Training summary**: Text file with metrics and equation

#### Example Output

```
============================================================
TRAINING RESULTS
============================================================
  Samples:      25
  R²:           0.9523
  RMSE:         2.145°
  MAE:          1.876°
  Bias (mean):  0.032°
  Std Dev:      2.148°
  95% LoA:      [-4.18°, 4.24°]

5-Fold Cross-Validation:
  CV RMSE:      2.834° ± 0.521°

------------------------------------------------------------
POLYNOMIAL EQUATION (original units):
------------------------------------------------------------
  θ = 0.001234*s_red_px² + -0.000567*s_red_px*s_blue_px + ...
```

---

### Contact Angle Prediction (`contact_angle_predict_ca_regression_model.py`)

Predict contact angle from LED distances using a trained regression model.

#### Batch Prediction

```bash
python -m panda_experiment_analyzers.contact_angle.contact_angle_predict_ca_regression_model \
    --model path/to/contact_angle_poly_model.pkl \
    batch \
    --in-csv path/to/led_distances.csv \
    --out-csv path/to/with_theta.csv \
    --train-csv-for-intervals path/to/training_data.csv \
    --interval-type prediction \
    --alpha 0.05 \
    --plots-dir path/to/plots \
    --show-equation
```

#### Single Point Prediction

```bash
python -m panda_experiment_analyzers.contact_angle.contact_angle_predict_ca_regression_model \
    --model path/to/contact_angle_poly_model.pkl \
    point \
    --s-red 85.5 \
    --s-blue 72.3 \
    --show-equation
```

#### Python API

```python
from panda_experiment_analyzers.contact_angle.contact_angle_predict_ca_regression_model import (
    predict_batch,
    predict_point,
)

# Batch prediction
predict_batch(
    model_path="model.pkl",
    in_csv="input.csv",
    out_csv="output.csv",
    show_equation=True,
    train_csv_for_intervals="training.csv",  # For confidence/prediction intervals
    alpha=0.05,                              # 95% intervals
    interval_type="prediction",              # or "confidence"
    plots_dir="./plots/",
    id_column="Image"
)

# Single point
predict_point(
    model_path="model.pkl",
    s_red=85.5,
    s_blue=72.3,
    show_equation=True
)
```

#### Required Input CSV Columns
- `s_red_px`: Red LED pair separation
- `s_blue_px`: Blue LED pair separation

#### Output CSV Additions
- `theta_pred_deg`: Predicted contact angle (degrees)
- `theta_lo_95_pre`: Lower bound of 95% prediction interval
- `theta_hi_95_pre`: Upper bound of 95% prediction interval
- `theta_resid_deg`: Residual (if ground truth provided)

---

### Bayesian Optimization (`contact_angle_ml_gpr_model.py`)

Use Gaussian Process Regression for Bayesian optimization to find optimal experimental parameters.

```bash
python -m panda_experiment_analyzers.contact_angle.contact_angle_ml_gpr_model \
    --csv training_data.csv \
    --x-cols concentration,potential \
    --y-col redplusblue \
    --k 5 \
    --conc-min 10.0 --conc-max 200.0 \
    --pot-min 0.8 --pot-max 2.0 \
    --plots-dir ./bo_plots
```

This will:
1. Fit a Gaussian Process to your training data
2. Suggest K new experimental points using Expected Improvement
3. Generate surrogate mean and EI landscape plots

---

### Visualization (`contact_angle_plots_regression_model.py`)

Generate plots of contact angle predictions vs experimental parameters.

```bash
python -m panda_experiment_analyzers.contact_angle.contact_angle_plots_regression_model \
    --csv predictions_with_theta.csv \
    --plots-dir ./plots \
    --theta-col theta_pred_deg \
    --concentration-col concentration \
    --potential-col potential
```

Generates:
- Error bar plots colored by secondary variable
- Smooth heatmap/contour of θ over parameter space

---

## LED Parameters Configuration

Create a `led_params.json` file to customize detection:

```json
{
    "hsv": {
        "red_lower": [150, 0, 200],
        "red_upper": [170, 255, 255],
        "blue_lower": [85, 10, 200],
        "blue_upper": [100, 255, 255]
    },
    "geometry": {
        "expected_red_separation_px": 80.0,
        "red_separation_tolerance_px": 30.0,
        "blue_separation_range_px": [40.0, 100.0]
    },
    "search": {
        "search_radius_px": 100.0
    },
    "detection": {
        "ignore_color": false
    }
}
```

---

## Workflow Summary

### Training Workflow (one-time calibration)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Model Training Workflow                           │
└─────────────────────────────────────────────────────────────────────┘

┌───────────────────┐     ┌───────────────────┐
│ Calibration       │     │ Side-view         │
│ Images            │     │ Goniometer        │
│ (top-down LED)    │     │ Measurements      │
└────────┬──────────┘     └────────┬──────────┘
         │                         │
         ▼                         │
┌────────────────────────┐         │
│ batch_contact_angle_   │         │
│ led.py                 │         │
│ → s_red_px, s_blue_px  │         │
└────────┬───────────────┘         │
         │                         │
         └────────┬────────────────┘
                  ▼
         ┌───────────────────┐
         │ calibration.csv   │
         │ s_red, s_blue,    │
         │ theta_side_deg    │
         └────────┬──────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│ contact_angle_train_regression_     │
│ model.py                            │
│ - Fit polynomial: θ = f(s_red,s_blue)│
│ - Cross-validation                  │
│ - Save model .pkl                   │
└────────┬────────────────────────────┘
         │
         ▼
   ┌─────────────┐
   │ model.pkl   │  (trained polynomial model)
   └─────────────┘
```

### Prediction Workflow (routine use)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Contact Angle Prediction Workflow                 │
└─────────────────────────────────────────────────────────────────────┘

     ┌──────────────┐
     │ Raw Images   │  (z-stack or single frame)
     │ (.jpg/.tif)  │
     └──────┬───────┘
            │
            ▼
┌───────────────────────────────────┐
│  batch_contact_angle_led.py       │
│  - Group images into z-stacks     │
│  - Auto-select best focus frame   │
└───────────────┬───────────────────┘
                │
                ▼
┌───────────────────────────────────┐
│  contact_angle_led_detect.py      │
│  - Detect droplet center          │
│  - Find red & blue LED pairs      │
│  - Measure s_red_px, s_blue_px    │
└───────────────┬───────────────────┘
                │
                ▼
         ┌──────────────┐
         │  output.csv  │  (LED distances)
         │  + debug img │
         └──────┬───────┘
                │
                ▼
┌────────────────────────────────────────────┐
│ contact_angle_predict_ca_regression_model  │
│  - Load trained polynomial model (.pkl)    │
│  - Predict θ from (s_red_px, s_blue_px)    │
│  - Compute confidence/prediction intervals │
└───────────────┬────────────────────────────┘
                │
                ▼
         ┌──────────────┐
         │ with_theta   │  (θ predictions + intervals)
         │    .csv      │
         └──────┬───────┘
                │
       ┌────────┴────────┐
       ▼                 ▼
┌─────────────────┐  ┌─────────────────────────┐
│ Visualization   │  │ Bayesian Optimization   │
│ (plots)         │  │ (suggest next params)   │
└─────────────────┘  └─────────────────────────┘
```

---

---

## Machine Learning Integration (Autonomous Experiments)

This section describes how the contact angle scripts are designed to integrate with a closed-loop machine learning workflow for autonomous experimentation. **Note: This pipeline is not fully implemented yet**, but the components are designed to work together as described below.

### Concept Overview

The goal is to use machine learning to **autonomously optimize experimental parameters** (e.g., polymer concentration, deposition voltage) to achieve a target contact angle. The workflow uses Bayesian Optimization to intelligently suggest the next experiments based on previous results.

```
┌─────────────────────────────────────────────────────────────────────┐
│              Closed-Loop Autonomous Experimentation                 │
└─────────────────────────────────────────────────────────────────────┘

    ┌─────────────┐
    │ Initial     │  (Design of Experiments or random)
    │ Experiments │
    └──────┬──────┘
           │
           ▼
    ┌─────────────────────────────────────────┐
    │           EXPERIMENT LOOP                │
    │  ┌─────────────────────────────────┐    │
    │  │ 1. Run Experiment               │    │
    │  │    (PANDA robot deposits film)  │    │
    │  └──────────────┬──────────────────┘    │
    │                 ▼                        │
    │  ┌─────────────────────────────────┐    │
    │  │ 2. Measure Contact Angle        │    │
    │  │    (LED detection → θ)          │    │
    │  └──────────────┬──────────────────┘    │
    │                 ▼                        │
    │  ┌─────────────────────────────────┐    │
    │  │ 3. Update Training Data         │    │
    │  │    (params, θ) → database       │    │
    │  └──────────────┬──────────────────┘    │
    │                 ▼                        │
    │  ┌─────────────────────────────────┐    │
    │  │ 4. Fit GP Surrogate Model       │    │
    │  │    θ = f(concentration, voltage)│    │
    │  └──────────────┬──────────────────┘    │
    │                 ▼                        │
    │  ┌─────────────────────────────────┐    │
    │  │ 5. Compute Acquisition Function │    │
    │  │    (Expected Improvement)       │    │
    │  └──────────────┬──────────────────┘    │
    │                 ▼                        │
    │  ┌─────────────────────────────────┐    │
    │  │ 6. Suggest Next Experiment      │    │
    │  │    (maximize EI)                │    │
    │  └──────────────┬──────────────────┘    │
    │                 │                        │
    └─────────────────┼────────────────────────┘
                      │
                      ▼
              [Repeat until converged
               or budget exhausted]
```

### How the Scripts Fit Together

| Step | Script | Function |
|------|--------|----------|
| Measure θ | `contact_angle_led_detect.py` | Detect LED positions from images |
| Measure θ | `contact_angle_predict_ca_regression_model.py` | Convert LED distances to θ |
| Update data | `sql_ml_functions.py` | Store results in database |
| Fit model | `contact_angle_ml_gpr_model.py` | Train Gaussian Process on (params → θ) |
| Suggest next | `contact_angle_ml_gpr_model.py` | Compute EI, propose new params |
| Run experiment | `experiment_generator.py` | Schedule PANDA experiment |

### Bayesian Optimization Details

The `contact_angle_ml_gpr_model.py` script implements Bayesian Optimization for **minimizing** a target (e.g., minimizing `|θ - θ_target|` or maximizing/minimizing θ directly).

#### Key Functions

```python
from panda_experiment_analyzers.contact_angle.contact_angle_ml_gpr_model import (
    load_xy,           # Load training data from CSV
    fit_gpr,           # Fit Gaussian Process Regressor
    propose_candidates, # Suggest next experiments via Expected Improvement
    plot_surrogate_mean, # Visualize the GP mean surface
    plot_ei,           # Visualize the acquisition function
)
```

#### Example: Suggest Next Experiments

```python
import pandas as pd
from panda_experiment_analyzers.contact_angle.contact_angle_ml_gpr_model import (
    load_xy, fit_gpr, propose_candidates, infer_bounds_from_data
)

# Load existing experimental data
df, X, y = load_xy(
    "training_data.csv",
    x_cols=("concentration", "potential"),  # Input parameters
    y_col="contact_angle"                    # Target to optimize
)

# Fit the GP surrogate model
x_scaler, gpr = fit_gpr(X, y)

# Define search bounds
bounds = infer_bounds_from_data(X, pad_frac=0.05)
# Or set manually: bounds = [(10.0, 200.0), (0.8, 2.0)]

# Propose next 5 experiments
X_next, mu, sigma, ei = propose_candidates(
    x_scaler, gpr, bounds, y_orig=y,
    k=5,              # Number of suggestions
    xi=0.01,          # Exploration parameter
    n_random=50000,   # Random samples for optimization
    min_dist_norm=0.2 # Diversity radius
)

# X_next contains the suggested (concentration, potential) pairs
for i, (conc, pot) in enumerate(X_next):
    print(f"Suggestion {i+1}: concentration={conc:.2f}, potential={pot:.3f}")
    print(f"  GP prediction: θ = {mu[i]:.2f}° ± {sigma[i]:.2f}°")
    print(f"  Expected Improvement: {ei[i]:.4f}")
```

### Integration with PANDA System

The `contact_angle_analyzer.py` and `experiment_generator.py` files are designed to integrate with the PANDA self-driving lab system. Here's how the intended workflow works:

#### 1. Analyzer Function (after each experiment)

```python
# In contact_angle_analyzer.py
def analyze(experiment_id: int, add_to_training_data: bool = False):
    """
    Called automatically after each experiment completes.
    
    1. Fetch the contact angle image from the database
    2. Detect LED positions using process_image()
    3. Predict contact angle using the polynomial model
    4. Store results in the database
    5. Optionally add to ML training data
    """
    # TODO: Implement the full workflow
    pass
```

#### 2. Generator Function (to schedule next experiment)

```python
# In experiment_generator.py / contact_angle_analyzer.py
def run_ml_model(generate_experiment_id=None):
    """
    Called to generate the next experiment.
    
    1. Load all training data from database
    2. Fit GP model on (concentration, voltage) → θ
    3. Compute Expected Improvement
    4. Select best next point
    5. Schedule new experiment with PANDA
    """
    # Load training data
    training_df = select_ml_training_data()  # From sql_ml_functions.py
    
    # Fit GP and get suggestions
    X = training_df[["concentration", "voltage"]].values
    y = training_df["contact_angle"].values
    x_scaler, gpr = fit_gpr(X, y)
    
    bounds = [(10, 200), (0.8, 2.0)]  # Example bounds
    X_next, mu, sigma, ei = propose_candidates(x_scaler, gpr, bounds, y)
    
    # Take the best suggestion
    best_conc, best_voltage = X_next[0]
    
    # Create experiment parameters
    params = PAMAParams(
        concentration=best_conc,
        dep_v=best_voltage,
    )
    
    # Schedule with PANDA
    experiment_id = generator(params)
    return experiment_id
```

### Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Data Flow                                    │
└─────────────────────────────────────────────────────────────────────┘

  Experiment Parameters              Contact Angle Measurement
  ─────────────────────              ─────────────────────────
  concentration: 50 mM               s_red_px: 85.2 px
  voltage: 1.2 V                     s_blue_px: 72.1 px
  time: 600 s                              │
         │                                 ▼
         │                          ┌─────────────┐
         │                          │ Polynomial  │
         │                          │ Model (.pkl)│
         │                          └──────┬──────┘
         │                                 │
         │                                 ▼
         │                          θ_predicted: 45.3°
         │                                 │
         └────────────┬────────────────────┘
                      ▼
              ┌───────────────┐
              │ Database      │
              │ (training     │
              │  data table)  │
              └───────┬───────┘
                      │
                      ▼
              ┌───────────────┐
              │ GP Model      │
              │ θ = f(c, V)   │
              └───────┬───────┘
                      │
                      ▼
              Next experiment:
              concentration=75, voltage=1.4
```

### Database Schema (sql_ml_functions.py)

The SQL functions manage two main tables:

#### `ml_pama_training_data`
| Column | Type | Description |
|--------|------|-------------|
| experiment_id | int | Unique experiment identifier |
| voltage | float | Deposition voltage (V) |
| concentration | float | Polymer concentration (mM) |
| contact_angle | float | Measured contact angle (°) |

#### `ml_pama_best_test_points`
| Column | Type | Description |
|--------|------|-------------|
| model_id | int | GP model version |
| experiment_id | int | Which experiment this suggestion led to |
| v_dep | float | Suggested voltage |
| concentration | float | Suggested concentration |
| predicted_response | float | GP mean prediction |
| standard_deviation | float | GP uncertainty |

### Implementation Status & TODOs

| Component | Status | Notes |
|-----------|--------|-------|
| LED detection | Complete | `contact_angle_led_detect.py` |
| Batch processing | Complete | `batch_contact_angle_led.py` |
| Polynomial model training | Complete | `contact_angle_train_regression_model.py` |
| Polynomial model prediction | Complete | `contact_angle_predict_ca_regression_model.py` |
| GP fitting & suggestions | Complete | `contact_angle_ml_gpr_model.py` |
| Visualization | Complete | `contact_angle_plots_regression_model.py` |
| SQL data functions | Complete | `sql_ml_functions.py` |
| Analyzer integration | Placeholder | `contact_angle_analyzer.py` needs implementation |
| Experiment generator | Partial | `experiment_generator.py` needs ML loop |
| PANDA scheduling | Depends on panda_lib | External dependency |

### Getting Started with ML Integration

1. **Collect calibration data**: Run experiments with known contact angles (measured via goniometer) to train the polynomial model.

2. **Train the polynomial model**:
   ```bash
   python -m panda_experiment_analyzers.contact_angle.contact_angle_train_regression_model \
       --train-csv calibration.csv --out-model model.pkl
   ```

3. **Run initial experiments**: Perform 5-10 experiments across your parameter space to seed the GP model.

4. **Implement the analysis loop**: Complete the `analyze()` function in `contact_angle_analyzer.py` to:
   - Fetch images from the database
   - Run LED detection
   - Predict contact angle
   - Store results

5. **Implement the generation loop**: Complete `run_ml_model()` to:
   - Fetch training data
   - Fit GP model
   - Generate suggestions
   - Schedule next experiment

6. **Connect to PANDA**: Ensure `panda_lib` scheduler and experiment types are properly configured.

### Example: Manual Bayesian Optimization Loop

If you want to run the ML loop manually (without PANDA automation):

```python
import pandas as pd
from panda_experiment_analyzers.contact_angle import (
    process_image,
    predict_point,
    fit_gpr,
    propose_candidates,
)

# 1. Process your latest image
result = process_image("latest_experiment.jpg", debug=True, debug_folder="./debug")
s_red = result["s_red_px"]
s_blue = result["s_blue_px"]

# 2. Predict contact angle
predict_point("model.pkl", s_red=s_red, s_blue=s_blue)

# 3. Add to your training CSV manually, then...

# 4. Get next suggestions
df = pd.read_csv("training_data.csv")
X = df[["concentration", "voltage"]].values
y = df["contact_angle"].values

x_scaler, gpr = fit_gpr(X, y)
bounds = [(10, 200), (0.8, 2.0)]
X_next, mu, sigma, ei = propose_candidates(x_scaler, gpr, bounds, y, k=3)

print("Next experiments to try:")
for conc, volt in X_next:
    print(f"  concentration={conc:.1f}, voltage={volt:.2f}")
```

---

## Troubleshooting

### Common Issues

**"Could not find valid blue LED pair"**
- Check HSV ranges in params - blue LEDs may be out of expected color range
- Increase `search_radius_px` if droplet is off-center
- Use `--debug` flag to visualize detection attempts

**"Red LED separation outside valid range"**
- Adjust `expected_red_separation_px` and tolerance in params
- Check image focus - out-of-focus images may merge LED spots

**Low focus scores / wrong frame selected**
- Verify z-stack naming convention matches expected patterns
- Check that all images in stack have consistent lighting

### Debug Output

When `--debug` is enabled, the following files are generated:
- `{image}_debug.jpg`: Annotated image showing detected LEDs and droplet
- `{image}_hough_circle.jpg`: Hough circle detection result
- `{image}_contour_fallback.jpg`: Contour detection fallback
- `{image}_red_profile_debug.png`: Intensity profile for red LED fallback
- `{image}_fallback_debug.csv`: Detailed fallback detection log
- `focus_scores.csv`: Focus ranking for all z-stack frames

---

## Data Classes Reference

```python
from panda_experiment_analyzers.contact_angle import (
    RequiredData,    # Input data for analysis
    RawMetrics,      # Raw measurement outputs
    PAMAMetrics,     # Processed metrics
    MLTrainingData,  # Training data structure
    MLInput,         # File paths for ML workflow
    MLOutput,        # ML model outputs
    PAMAParams,      # Experiment parameters
)
```

---

## Authors

- Harley Quinn
- Date Created: 2025-05-01
- Last Modified: 2025-12-31

