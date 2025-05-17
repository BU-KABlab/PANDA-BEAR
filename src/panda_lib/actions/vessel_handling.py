import logging
from logging import Logger
from typing import List, Optional, Tuple, Union

from sqlalchemy.orm import Session

from panda_shared.config.config_tools import (
    read_config,
    read_testing_config,
)
from panda_shared.db_setup import SessionLocal
from panda_shared.log_tools import timing_wrapper

from ..errors import (
    NoAvailableSolution,
)
from ..labware import StockVial, Vial, WasteVial, Well, read_vials
from ..utilities import solve_vials_ilp

TESTING = read_testing_config()

config = read_config()

# Set up logging
logger = logging.getLogger("panda")
testing_logging = logging.getLogger("panda")


def _handle_source_vessels(
    volume: float,
    src_vessel: Union[str, Well, StockVial],
    pjct_logger: Logger = logger,
    source_concentration: Optional[float] = None,
    db_session: Session = SessionLocal,
) -> Tuple[List[Union[Vial, Well]], List[Tuple[Union[Vial, Well], float]]]:
    """Handle selection and processing of source vessels for liquid transfer.

    Parameters
    ----------
    volume : float
        The volume to be transferred in microliters.
    src_vessel : Union[str, Well, StockVial]
        The source vessel identifier or object.
    pjct_logger : Logger, optional
        Logger instance for recording events, by default logger
    source_concentration : float, optional
        Target concentration in mM, by default None
    db_session : Session, optional
        Database session for querying vials, by default SessionLocal

    Returns
    -------
    Tuple[List[Union[Vial, Well]], List[Tuple[Union[Vial, Well], float]]]
        A tuple containing:
        - List of selected source vessels
        - List of tuples containing (vessel, volume) pairs

    Raises
    ------
    ValueError
        If no suitable vials are available or if source concentration cannot be determined
    """
    selected_source_vessels: List[Union[Vial, Well]] = []
    source_vessel_volumes: List[Tuple[Union[Vial, Well], float]] = []

    if isinstance(src_vessel, (str, Vial)):
        if isinstance(src_vessel, Vial):
            src_vessel = src_vessel.name.lower()
        else:
            src_vessel = src_vessel.lower()
        stock_vials, _ = read_vials(db_session())
        selected_source_vessels = [
            vial
            for vial in stock_vials
            if vial.name.lower() == src_vessel and vial.volume > 0.0
        ]

        if not selected_source_vessels:
            pjct_logger.error("No %s vials available", src_vessel)
            raise ValueError(f"No {src_vessel} vials available")

        if source_concentration is None:
            pjct_logger.warning(
                "Source concentration not provided, using database value"
            )
            if selected_source_vessels[0].category == 0:
                try:
                    source_concentration = float(
                        selected_source_vessels[0].concentration
                    )
                except ValueError:
                    pjct_logger.error(
                        "Source concentration not provided and not available in the database"
                    )
                    raise ValueError(
                        "Source concentration not provided and not available in the database"
                    )

        source_vessel_volumes, deviation, volumes_by_position = solve_vials_ilp(
            vial_concentration_map={
                vial.position: vial.concentration for vial in selected_source_vessels
            },
            v_total=volume,
            c_target=source_concentration,
        )

        if source_vessel_volumes is None:
            raise ValueError(
                f"No solution combinations found for {src_vessel} {source_concentration} mM"
            )

        pjct_logger.info("Deviation from target concentration: %s mM", deviation)

        source_vessel_volumes = [
            (vial, volumes_by_position[vial.position])
            for vial in selected_source_vessels
        ]

    elif isinstance(src_vessel, (Well, Vial)):
        source_vessel_volumes = [(src_vessel, volume)]
        pjct_logger.info(
            "Pipetting %f uL from %s", volume, src_vessel.name or src_vessel
        )

    return selected_source_vessels, source_vessel_volumes


@timing_wrapper
def solution_selector(
    solution_name: str,
    volume: float,
    db_session: Session = SessionLocal,
) -> StockVial:
    """
    Select the solution from which to withdraw from, from the list of solution objects
    Args:
        solutions (list): The list of solution objects
        solution_name (str): The name of the solution to select
        volume (float): The volume to be pipetted
    Returns:
        solution (object): The solution object
    """
    # Fetch updated solutions from the db
    stock_vials, _ = read_vials("stock", db_session)

    for solution in stock_vials:
        # if the solution names match and the requested volume is less than the available volume (volume - 10% of capacity)
        if solution.name.lower() == solution_name.lower() and round(
            float(solution.volume) - float(0.10) * float(solution.capacity), 6
        ) > (volume):
            logger.debug(
                "Selected stock vial: %s in position %s",
                solution.name,
                solution.position,
            )
            return solution
    raise NoAvailableSolution(solution_name)


@timing_wrapper
def waste_selector(
    solution_name: str,
    volume: float,
    db_session: Session = SessionLocal,
) -> WasteVial:
    """
    Select the solution in which to deposit into from the list of solution objects
    Args:
        solutions (list): The list of solution objects
        solution_name (str): The name of the solution to select
        volume (float): The volume to be pipetted
    Returns:
        solution (object): The solution object
    """
    # Fetch updated solutions from the db
    _, wate_vials = read_vials(db_session())
    solution_name = solution_name.lower()
    for waste_vial in wate_vials:
        if (
            waste_vial.name.lower() == solution_name
            and round((float(waste_vial.volume) + float(str(volume))), 6)
            < waste_vial.capacity
        ):
            logger.debug(
                "Selected waste vial: %s in position %s",
                waste_vial.name,
                waste_vial.position,
            )
            return waste_vial
    raise NoAvailableSolution(solution_name)


class VesselSelector:
    """Vessel selection and validation handler.

    This class provides static methods for selecting and validating
    source and destination vessels for liquid transfers.
    """

    @staticmethod
    def select_solution_vessel(
        solution_name: str, volume: float, db_session: Session = SessionLocal
    ) -> StockVial:
        """Select appropriate solution vessel based on requirements.

        Parameters
        ----------
        solution_name : str
            Name of the required solution
        volume : float
            Required volume in microliters
        db_session : Session, optional
            Database session for querying vessels, by default SessionLocal

        Returns
        -------
        StockVial
            Selected vessel meeting requirements

        Raises
        ------
        NoAvailableSolution
            If no suitable vessel is found
        """
        # Fetch updated solutions from the db
        stock_vials, _ = read_vials("stock", db_session)

        for solution in stock_vials:
            # if the solution names match and the requested volume is less than the available volume (volume - 10% of capacity)
            if solution.name.lower() == solution_name.lower() and round(
                float(solution.volume) - float(0.10) * float(solution.capacity), 6
            ) > (volume):
                logger.debug(
                    "Selected stock vial: %s in position %s",
                    solution.name,
                    solution.position,
                )
                return solution
        raise NoAvailableSolution(solution_name)

    @staticmethod
    def select_waste_vessel(
        solution_name: str, volume: float, db_session: Session = SessionLocal
    ) -> WasteVial:
        """Select appropriate waste vessel."""
        # Fetch updated solutions from the db
        _, wate_vials = read_vials(db_session())
        solution_name = solution_name.lower()
        for waste_vial in wate_vials:
            if (
                waste_vial.name.lower() == solution_name
                and round((float(waste_vial.volume) + float(str(volume))), 6)
                < waste_vial.capacity
            ):
                logger.debug(
                    "Selected waste vial: %s in position %s",
                    waste_vial.name,
                    waste_vial.position,
                )
                return waste_vial
        raise NoAvailableSolution(solution_name)

    @staticmethod
    def handle_source_vessels(
        volume: float,
        src_vessel: Union[str, Well, StockVial],
        pjct_logger: Logger = logger,
        source_concentration: Optional[float] = None,
        db_session: Session = SessionLocal,
    ) -> Tuple[List[Union[Vial, Well]], List[Tuple[Union[Vial, Well], float]]]:
        """Handle source vessel selection and volume distribution.

        Parameters
        ----------
        volume : float
            Required volume in microliters
        src_vessel : Union[str, Well, StockVial]
            Source vessel identifier or object
        pjct_logger : Logger, optional
            Project logger for operation tracking
        source_concentration : float, optional
            Target concentration in mM
        db_session : Session, optional
            Database session for queries

        Returns
        -------
        Tuple[List[Union[Vial, Well]], List[Tuple[Union[Vial, Well], float]]]
            Selected vessels and their volume allocations

        Raises
        ------
        ValueError
            If no suitable vessels are found or concentration cannot be determined
        """
        selected_source_vessels: List[Union[Vial, Well]] = []
        source_vessel_volumes: List[Tuple[Union[Vial, Well], float]] = []

        if isinstance(src_vessel, (str, Vial)):
            if isinstance(src_vessel, Vial):
                src_vessel = src_vessel.name.lower()
            else:
                src_vessel = src_vessel.lower()
            stock_vials, _ = read_vials(db_session())
            selected_source_vessels = [
                vial
                for vial in stock_vials
                if vial.name == src_vessel and vial.volume > 0.0
            ]

            if not selected_source_vessels:
                pjct_logger.error("No %s vials available", src_vessel)
                raise ValueError(f"No {src_vessel} vials available")

            if source_concentration is None:
                pjct_logger.warning(
                    "Source concentration not provided, using database value"
                )
                if selected_source_vessels[0].category == 0:
                    try:
                        source_concentration = float(
                            selected_source_vessels[0].concentration
                        )
                    except ValueError:
                        pjct_logger.error(
                            "Source concentration not provided and not available in the database"
                        )
                        raise ValueError(
                            "Source concentration not provided and not available in the database"
                        )

            source_vessel_volumes, deviation, volumes_by_position = solve_vials_ilp(
                vial_concentration_map={
                    vial.position: vial.concentration
                    for vial in selected_source_vessels
                },
                v_total=volume,
                c_target=source_concentration,
            )

            if source_vessel_volumes is None:
                raise ValueError(
                    f"No solution combinations found for {src_vessel} {source_concentration} mM"
                )

            pjct_logger.info("Deviation from target concentration: %s mM", deviation)

            source_vessel_volumes = [
                (vial, volumes_by_position[vial.position])
                for vial in selected_source_vessels
            ]

        elif isinstance(src_vessel, (Well, Vial)):
            source_vessel_volumes = [(src_vessel, volume)]
            pjct_logger.info(
                "Pipetting %f uL from %s", volume, src_vessel.name or src_vessel
            )

        return selected_source_vessels, source_vessel_volumes
