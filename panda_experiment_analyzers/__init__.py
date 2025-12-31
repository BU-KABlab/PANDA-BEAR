"""
PANDA Experiment Analyzers
==========================

This package contains analysis modules for processing experimental data
from PANDA-BEAR experiments.

Available Analyzers:
- contact_angle: Contact angle analysis from LED reflection images
- pedot: PEDOT electrochemical characterization analysis

Example Usage:
    from panda_experiment_analyzers.contact_angle import process_image, predict_batch
    from panda_experiment_analyzers.pedot_analyzer import analyze as pedot_analyze
"""

# Note: Submodules are imported on-demand to avoid circular imports
# and heavy dependency loading at package import time.

__all__ = [
    "contact_angle",
    "pedot",
    "contact_angle_analyzer",
    "pedot_analyzer",
    "example_analyzer",
]

