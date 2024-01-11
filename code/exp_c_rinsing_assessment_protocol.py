"""
Protocol for testing the rinsing the electrode when performing cyclic voltammetry
on ferrocyanide solution
"""
from typing import Sequence
import json
from codebase.experiment_types import ExperimentBase, ExperimentStatus
from codebase.controller import Toolkit
from codebase.vials import StockVial, WasteVial
from codebase.e_panda import (
    forward_pipette_v2,
    characterization_v2,
    solution_selector,
    waste_selector,
    NoAvailableSolution,
)
