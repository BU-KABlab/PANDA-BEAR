# For writing a protocol, use the available actions from the panda_lib.actions module.
from dataclasses import dataclass
from logging import Logger

from panda_lib import Toolkit
from panda_lib.actions import (
    clear_well,
    flush_pipette,
    image_well,
    perform_cyclic_voltammetry,
    rinse_well,
    transfer,
)

# If you are using custom actions, import them from the appropriate module.
from panda_lib.experiments import EchemExperimentBase, ExperimentStatus

# To have specific types for the wells, import them from the labware module.
from panda_lib.labware.wellplates import Well


@dataclass
class Solution:
    name: str
    volume: int
    concentration: float
    repeated: int


def run(experiment: EchemExperimentBase, toolkit: Toolkit):
    """Run the experiment."""

    toolkit.global_logger.info("Running experiment: " + experiment.experiment_name)
    PolyethyleneDeposition(experiment, toolkit)
    toolkit.global_logger.info("Experiment complete")

def PolyethyleneDeposition(exp:EchemExperimentBase,toolkit: Toolkit):
    """Transfer polyethylene solution to the well"""

    reag = Solution(
        "polystyrene",
        exp.solutions["polystyrene"]["volume"],
        exp.solutions["polystyrene"]["concentration"],
        1,
    )

    transfer(
        reag.volume,
        reag.name,
        exp.well_id,
        toolkit=toolkit,
    )

    image_well(
        toolkit=toolkit,
        instructions=exp,
        step_description="after_transfer",
    )