""" Experiment data class"""
from typing import List
import datetime


class Experiment:
    def __init__(self, ID: int, Replicates: List[int], Target_Well: str, DMF: float, PEG: float, Acrylate: float, Ferrocene: float, Custom: float, OCP: int, CA: int, CV: int, dep_duration: int, DepPot: float, char_sol_name: str, char_vol: int, flush_sol_name: str, flush_vol: int, status: str = 'new', status_date: str = datetime.datetime.now(), time_stamps: List[str] = [], OCP_file: str = None, OCP_pass: bool = None, deposition_data_file: str = None, deposition_plot_file: str = None, deposition_max_value: float = None, deposition_min_value: float = None, characterization_data_file: str = None, characterization_plot_file: str = None, characterization_max_value: float = None, characterization_min_value: float = None, pumping_rate: float = 0.5):
        self.ID = ID
        self.Replicates = Replicates
        self.Target_Well = Target_Well
        self.DMF = DMF
        self.PEG = PEG
        self.Acrylate = Acrylate
        self.Ferrocene = Ferrocene
        self.Custom = Custom
        self.OCP = OCP
        self.CA = CA
        self.CV = CV
        self.dep_duration = dep_duration
        self.DepPot = DepPot
        self.status = status
        self.status_date = status_date
        self.time_stamps = time_stamps
        self.OCP_file = OCP_file
        self.OCP_pass = OCP_pass
        self.deposition_data_file = deposition_data_file
        self.deposition_plot_file = deposition_plot_file
        self.deposition_max_value = deposition_max_value
        self.deposition_min_value = deposition_min_value
        self.characterization_data_file = characterization_data_file
        self.characterization_plot_file = characterization_plot_file
        self.characterization_max_value = characterization_max_value
        self.characterization_min_value = characterization_min_value
        self.pumping_rate = pumping_rate
        self.char_sol_name = char_sol_name
        self.char_vol = char_vol
        self.flush_sol_name = flush_sol_name
        self.flush_vol = flush_vol

        def is_replicate(self, other):
            if isinstance(other, Experiment):
                return self.DMF == other.DMF and self.PEG == other.PEG and self.Acrylate == other.Acrylate and self.Ferrocene == other.Ferrocene
            return False
        
        def __eq__(self, other):
            if isinstance(other, Experiment):
                return self.ID == other.ID
            return False
        
        def __repr__(self):
            return f"Experiment(ID={self.ID} | Target_Well={self.Target_Well}, DMF={self.DMF}, PEG={self.PEG}, Acrylate={self.Acrylate}, Ferrocene={self.Ferrocene}, Custom = {self.custom} | OCP={self.OCP}, CA={self.CA}, CV={self.CV}, dep_duration={self.dep_duration}, DepPot={self.DepPot}, status={self.status}, status_date={self.status_date}, time_stamps={self.time_stamps}, OCP_file={self.OCP_file}, OCP_pass={self.OCP_pass}, deposition_data_file={self.deposition_data_file}, deposition_plot_file={self.deposition_plot_file}, deposition_max_value={self.deposition_max_value}, deposition_min_value={self.deposition_min_value}, characterization_data_file={self.characterization_data_file}, characterization_plot_file={self.characterization_plot_file}, characterization_max_value={self.characterization_max_value}, characterization_min_value={self.characterization_min_value}, pumping_rate={self.pumping_rate}, char_sol_name={self.char_sol_name}, char_vol={self.char_vol}, flush_sol_name={self.flush_sol_name}, flush_vol={self.flush_vol})"
        