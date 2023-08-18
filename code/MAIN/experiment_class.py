""" Experiment data class"""
from typing import List, Optional
from enum import Enum
from datetime import datetime
from pydantic import ConfigDict, FilePath, RootModel
from pydantic.dataclasses import dataclass
from dataclasses import field

class ExperimentStatus(str, Enum):
    NEW = 'new'
    QUEUED = 'queued'
    COMPLETE = 'complete'
    ERROR = 'error'

@dataclass(config=ConfigDict(validate_assignment=True))
class ExperimentResult:
    ocp_file: FilePath
    ocp_pass: bool
    ocp_char_file: FilePath
    ocp_char_pass: bool
    deposition_data_file: FilePath  # FilePaths are validated to actually exist
    deposition_plot_file: FilePath
    deposition_max_value: float
    depsotion_min_value: float
    characterization_data_file: FilePath
    characterization_plot_file: FilePath
    characterization_max_value: float
    characterization_min_value: float


@dataclass(config=ConfigDict(validate_assignment=True))
class Experiment:
    id: int
    replicates: List[int]
    target_well: str
    dmf: float
    peg: float
    acrylate: float
    ferrocene: float
    custom: float
    ocp: int
    ca: int
    cv: int
    dep_duration: int
    dep_pot: float
    char_sol_name: str
    char_vol: int
    flush_sol_name: str
    flush_vol: int
    pumping_rate: float
    # TO restrict this to one of a few values you can use an enum
    status: ExperimentStatus = ExperimentStatus.NEW
    status_date: datetime = field(default_factory=datetime.now)
    time_stamps: List[int] = field(default_factory=list)
    # The optional fields seemed to be that way because they were experiment results, so I grouped them
    results: Optional[ExperimentResult] = None

    def is_replicate(self, other):
        if isinstance(other, Experiment):
            return self.dmf == other.dmf and self.peg == other.peg and self.acrylate == other.acrylate and self.ferrocene == other.ferrocene
        return False

    def is_same_id(self, other):
        # This used to be an "equals". It's dangerous to override equals in this way. This function is used for a lot of built-in methods
        # The generated one for dataclasses will compare and ensure all the fields match, which is not the same behavior. What were you using it for?
        if isinstance(other, Experiment):
            return self.id == other.id
        return False


def make_test_value():
    return Experiment(
        id=1,
        replicates=[],
        target_well="D5",
        dmf=0,
        peg=145,
        acrylate=145,
        ferrocene=0,
        custom=0,
        ocp=1,
        ca=1,
        cv=1,
        dep_duration=300,
        dep_pot=-2.7,
        status=ExperimentStatus.QUEUED,
        status_date=datetime.now(),
        pumping_rate=0.5,
        char_sol_name="Ferrocene",
        char_vol=290,
        flush_sol_name="DMF",
        flush_vol=120,
        results=None)



def test_parse():
    pass

def test_serialize():
   value = make_test_value()
   print(RootModel[Experiment](value).model_dump_json(indent=4))
   #with open('temp_test_file.json', 'w') as f:
   #    f.write(RootModel[Experiment](value).model_dump_json(indent=4))

if __name__ == "__main__":
    test_serialize()
    test_parse()
