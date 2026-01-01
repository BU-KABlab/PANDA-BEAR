# Model Files Management

## Overview

PyTorch model files (`.pth`) are **not stored in this Git repository**. These files are typically large binary files that would bloat the repository and are better managed separately.

## Current Model Files Location

Model files are located in:
- `panda_experiment_analyzers/pedot/ml_model/*.pth`

These files are used by the PEDOT analyzer for machine learning-based experiment optimization.

## Git Configuration

The `.gitignore` file is configured to exclude:
- `*.pth` - PyTorch model files
- `*.pth.tar` - PyTorch model archives
- `*.h5` - HDF5 model files
- `*.ckpt` - Checkpoint files

## For Users

### If You Need the Model Files

1. **Contact the maintainers** to obtain the model files
2. **Place them in the correct location**:
   ```
   panda_experiment_analyzers/pedot/ml_model/
   ```
3. **Ensure the file naming matches** what the code expects:
   - Base path: `pedot_gp_model_v8`
   - Files: `pedot_gp_model_v8_0.pth`, `pedot_gp_model_v8_1.pth`, etc.
   - Counter file: `model_counter.txt`

### Model File Requirements

The analyzer expects:
- Model files named with a counter suffix (e.g., `pedot_gp_model_v8_0.pth`)
- A `model_counter.txt` file indicating which model iteration to use
- Models must be compatible with the GPyTorch framework used in the code

## For Developers

### Adding New Models

If you need to add model files to the repository:

1. **Consider alternatives first**:
   - Use Git LFS for large files (if repository supports it)
   - Host models externally (cloud storage, model registry)
   - Document download instructions

2. **If models must be in repo**:
   - Use Git LFS: `git lfs track "*.pth"`
   - Document the model version and requirements
   - Update this file with model information

### Model Loading Code

Models are loaded in:
- `panda_experiment_analyzers/pedot/ml_model/pedot_ml_analyzer_v8.py`
- `panda_experiment_analyzers/pedot/ml_model/pedot_ml_analyzer_v9.py`

The loading logic:
1. Reads `model_counter.txt` to determine which model iteration to load
2. Constructs filename: `{base_path}_{counter}.pth`
3. Loads the model state dict using `torch.load()`

## Troubleshooting

### "No model found" Error

If you get a `FileNotFoundError` about missing model files:

1. Check that model files exist in `panda_experiment_analyzers/pedot/ml_model/`
2. Verify the `model_counter.txt` file exists and contains a valid number
3. Ensure file naming matches the expected pattern
4. Check file permissions (must be readable)

### Model Version Mismatch

If models were trained with a different version of the code:

1. Check the model file format matches current code expectations
2. Verify GPyTorch version compatibility
3. Consider retraining models if significant code changes occurred

## Future Improvements

Consider implementing:
- Model versioning system
- Automatic model download from external source
- Model validation on load
- Fallback to default parameters if models unavailable
