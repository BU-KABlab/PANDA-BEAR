"""
PEDOT Experiment Analyzer
=========================

This module provides analysis tools for PEDOT electrochemical
deposition experiments.

Components:
- experiment_generator: Generate PEDOT experiments
- ml_input: ML model input data handling
- ml_model: Machine learning models for PEDOT optimization
- pedot_classes: Data structures for PEDOT analysis
- sql_ml_functions: Database operations for ML data
"""

from .pedot_classes import PEDOTParams

__all__ = [
    "PEDOTParams",
]

