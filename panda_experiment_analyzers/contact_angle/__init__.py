"""
Contact Angle Analysis Module
=============================

This module provides tools for analyzing contact angle measurements from 
top-down LED reflection images.

Core Components:
- contact_angle_led_detect: LED position detection from images
- contact_angle_predict_ca_regression_model: Contact angle prediction using regression
- contact_angle_ml_gpr_model: Gaussian Process Regression model for Bayesian optimization
- contact_angle_plots_regression_model: Visualization tools
- batch_contact_angle_led: Batch processing of z-stack images

Data Classes:
- contact_angle_classes: Data structures for the workflow

Integration:
- experiment_generator: PANDA experiment generation
- ml_input: ML model input data population
- sql_ml_functions: Database functions for ML data
"""

from .contact_angle_classes import (
    RequiredData,
    RawMetrics,
    PAMAMetrics,
    MLTrainingData,
    MLInput,
    MLOutput,
    PAMAParams,
)

from .contact_angle_led_detect import (
    process_image,
    process_z_stack_then_measure,
    extract_z_mm_from_name,
    detect_droplet_center,
)

from .contact_angle_predict_ca_regression_model import (
    predict_batch,
    predict_point,
)

from .contact_angle_train_regression_model import (
    train_model,
    build_pipeline,
    expand_equation_original_units,
)

from .contact_angle_ml_gpr_model import (
    fit_gpr,
    propose_candidates,
    plot_surrogate_mean,
    plot_ei,
)

from .batch_contact_angle_led import (
    extract_stack_key,
    group_images_into_stacks,
)

__all__ = [
    # Data classes
    "RequiredData",
    "RawMetrics",
    "PAMAMetrics",
    "MLTrainingData",
    "MLInput",
    "MLOutput",
    "PAMAParams",
    # LED detection
    "process_image",
    "process_z_stack_then_measure",
    "extract_z_mm_from_name",
    "detect_droplet_center",
    # Model training
    "train_model",
    "build_pipeline",
    "expand_equation_original_units",
    # Prediction
    "predict_batch",
    "predict_point",
    # ML GPR model
    "fit_gpr",
    "propose_candidates",
    "plot_surrogate_mean",
    "plot_ei",
    # Batch processing
    "extract_stack_key",
    "group_images_into_stacks",
]
