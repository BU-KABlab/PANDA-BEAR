import logging
from typing import List, Optional

from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from shared_utilities.db_setup import SessionLocal

from ..sql_tools.panda_models import PlateTypes as PlateTypeDBModel
from ..sql_tools.panda_models import Vials  # SQLAlchemy models
from ..sql_tools.panda_models import WellModel as WellDBModel
from ..sql_tools.panda_models import Wellplates as WellPlateDBModel
from .schemas import (  # PyDanctic models
    PlateTypeModel,
    VialReadModel,
    VialWriteModel,
    WellplateReadModel,
    WellplateWriteModel,
    WellReadModel,
    WellWriteModel,
)


class VialService:
    """
    Service class for interacting with vials in the database.
    """

    def __init__(self, db_session_maker: sessionmaker = SessionLocal):
        self.db_session_maker = db_session_maker
        self.logger = logging.getLogger(__name__)

    def create_vial(self, vial_data: VialWriteModel) -> Vials:
        """
        Creates a new Vial in the database.

        Args:
            vial_data (VialModel): Pydantic model with vial details.

        Returns:
            Vials: SQLAlchemy model instance representing the new vial.
        """
        with self.db_session_maker() as db_session:
            # Check if the vial position is currently active, and deactivate it if so
            try:
                stmt = select(Vials).filter_by(position=vial_data.position)
                vials = db_session.execute(stmt).scalars().all()
                for vial in vials:
                    vial.active = 0
                    db_session.commit()
            except SQLAlchemyError as e:
                db_session.rollback()
                raise ValueError(f"Error deactivating existing vial: {e}")

            try:
                # Convert Pydantic model to SQLAlchemy model
                vial: Vials = Vials(**vial_data.model_dump())
                vial.active = 1
                db_session.add(vial)
                db_session.commit()
                db_session.refresh(vial)
                return vial
            except SQLAlchemyError as e:
                db_session.rollback()
                raise ValueError(f"Error creating vial: {e}")

    def get_vial(
        self, position: str = None, name: str = None, active_only: bool = True
    ) -> VialReadModel:
        """
        Fetches a vial by position from the database.

        Args:
            position (str): The position of the vial to fetch.

        Returns:
            VialModel: Pydantic model representing the vial.
        """
        with self.db_session_maker() as db_session:
            active_only = 1 if active_only else 0
            if name:
                stmt = select(Vials).filter_by(name=name, active=active_only)
            elif position:
                stmt = select(Vials).filter_by(position=position, active=active_only)
            else:
                raise ValueError("Either position or name must be provided.")
            vial = db_session.execute(stmt).scalar()
            if not vial:
                raise ValueError(f"Vial at position {position} not found.")
            # elif len(vial) > 1:
            # raise ValueError(f"Multiple vials found at position {position}.")
            # Convert SQLAlchemy model to Pydantic model
            return VialReadModel.model_validate(vial)

    def update_vial(self, position: str, updates: dict) -> Vials:
        """
        Updates an existing vial in the database.

        Args:
            position (str): The position of the vial to update.
            updates (dict): Key-value pairs of attributes to update.

        Returns:
            Vials: Updated SQLAlchemy model instance.
        """
        vial_id = updates.get("id", None)
        with self.db_session_maker() as db_session:
            try:
                if vial_id:
                    stmt = select(Vials).filter_by(
                        id=vial_id, position=position, active=1
                    )
                else:
                    stmt = select(Vials).filter_by(position=position, active=1)
                vial = db_session.execute(stmt).scalar()
                if not vial:
                    raise ValueError(f"Vial at position {position} not found.")
                # elif len(vial) > 1:
                #     raise ValueError(f"Multiple vials found at position {position}.")
                for key, value in updates.items():
                    if hasattr(vial, key) and (
                        key in VialWriteModel.model_fields.keys()
                    ):
                        setattr(vial, key, value)
                    # else:
                    #     self.logger.debug("Invalid attribute: %s. Not saved to db", key)
                db_session.commit()
                db_session.refresh(vial)
                return vial
            except SQLAlchemyError as e:
                db_session.rollback()
                raise ValueError(f"Error updating vial: {e}")

    def delete_vial(self, position: str) -> None:
        """
        Deletes a vial from the database.

        Args:
            position (str): The position of the vial to delete.
        """
        with self.db_session_maker() as db_session:
            try:
                stmt = select(Vials).filter_by(position=position)
                vial = db_session.execute(stmt).scalar()
                if not vial:
                    raise ValueError(f"Vial at position {position} not found.")
                # elif len(vial) > 1:
                #     raise ValueError(f"Multiple vials found at position {position}.")
                db_session.delete(vial)
                db_session.commit()
            except SQLAlchemyError as e:
                db_session.rollback()
                raise ValueError(f"Error deleting vial: {e}")

    def list_active_vials(self, cat: Optional[int] = None) -> List[VialReadModel]:
        """
        Lists all active vials in the database.

        Returns:
            List[VialModel]: List of Pydantic models representing active vials.
        """
        with self.db_session_maker() as db_session:
            stmt = select(Vials).filter_by(active=1)
            result = db_session.execute(stmt)
            vials = result.scalars().all() if result else []
            vials = [vial for vial in vials if vial.category == cat] if cat else vials
            # Log the raw data for debugging
            self.logger.debug("Fetched vials: %s", vials)

            try:
                return [VialReadModel.model_validate(vial) for vial in vials]
            except Exception as e:
                self.logger.error("Error converting vials to Pydantic models: %s", e)
                raise ValueError(f"Error converting vials to Pydantic models: {e}")

    def list_all_vials(self) -> List[VialReadModel]:
        """
        Lists all vials in the database.

        Returns:
            List[VialModel]: List of Pydantic models representing all vials.
        """
        with self.db_session_maker() as db_session:
            stmt = select(Vials)
            result = db_session.execute(stmt)
            vials = result.scalars().all() if result else []

            # Log the raw data for debugging
            self.logger.debug("Fetched vials: %s", vials)

            try:
                return [VialReadModel.model_validate(vial) for vial in vials]
            except Exception as e:
                self.logger.error("Error converting vials to Pydantic models: %s", e)
                raise ValueError(f"Error converting vials to Pydantic models: {e}")

    def list_inactive_vials(self) -> List[VialReadModel]:
        """
        Lists all inactive vials in the database.

        Returns:
            List[VialModel]: List of Pydantic models representing inactive vials.
        """
        with self.db_session_maker() as db_session:
            stmt = select(Vials).filter_by(active=0)
            result = db_session.execute(stmt)
            vials = result.scalars().all() if result else []

            # Log the raw data for debugging
            self.logger.debug("Fetched vials: %s", vials)

            try:
                return [VialReadModel.model_validate(vial) for vial in vials]
            except Exception as e:
                self.logger.error("Error converting vials to Pydantic models: %s", e)
                raise ValueError(f"Error converting vials to Pydantic models: {e}")


class WellService:
    """
    Service class for interacting with wells in the database.
    """

    def __init__(self, session_maker: sessionmaker = SessionLocal):
        self.session_maker = session_maker

    def create_well(self, well_data: WellWriteModel) -> WellDBModel:
        with self.session_maker() as active_db_session:
            active_db_session: Session
            try:
                well: WellDBModel = WellDBModel(**well_data.model_dump())
                active_db_session.add(well)
                active_db_session.commit()
                active_db_session.refresh(well)
                return well
            except SQLAlchemyError as e:
                active_db_session.rollback()
                raise ValueError(f"Error creating well: {e}")

    def get_well(self, well_id: str, plate_id: int) -> WellReadModel:
        with self.session_maker() as active_db_session:
            stmt = select(WellDBModel).filter_by(well_id=well_id, plate_id=plate_id)
            well = active_db_session.execute(stmt).scalar()
            if not well:
                raise ValueError(f"Well with id {well_id} not found.")

            active_db_session.refresh(well)
            return WellReadModel.model_validate(well)

    def update_well(self, well_id: str, plate_id: int, updates: dict) -> WellDBModel:
        with self.session_maker() as active_db_session:
            try:
                updated_model = WellWriteModel(**updates).model_dump()
                stmt = select(WellDBModel).filter_by(well_id=well_id, plate_id=plate_id)
                well = active_db_session.execute(stmt).scalar()
                if not well:
                    raise ValueError(f"Well with id {well_id} not found.")
                for key, value in updated_model.items():
                    setattr(well, key, value)
                active_db_session.commit()
                active_db_session.refresh(well)
                return well
            except ValueError as e:
                raise e
            except SQLAlchemyError as e:
                active_db_session.rollback()
                raise ValueError(f"Error updating well: {e}")

    def delete_well(self, well_id: str) -> None:
        with self.session_maker() as active_db_session:
            try:
                stmt = select(WellDBModel).filter_by(well_id=well_id)
                well = active_db_session.execute(stmt).scalar()
                if not well:
                    raise ValueError(f"Well with id {well_id} not found.")
                active_db_session.delete(well)
                active_db_session.commit()
            except SQLAlchemyError as e:
                active_db_session.rollback()
                raise ValueError(f"Error deleting well: {e}")

    def fetch_well_type_characteristics(
        self,
        db_session: sessionmaker = SessionLocal,
        plate_id: Optional[int] = None,
        type_id: Optional[int] = None,
    ) -> PlateTypeModel:
        """
        Fetches the characteristics of a well plate type.

        Args:
            db_session (Session): The database session.
            plate_id (Optional[int]): The ID of the well plate.
            type_id (Optional[int]): The ID of the plate type.

        Returns:
            PlateTypeModel: The validated model of the plate type.

        Raises:
            ValueError: If neither plate_id nor type_id is provided.
            ValueError: If the plate type is not found.

        """
        if not plate_id and not type_id:
            raise ValueError("Either plate_id or type_id must be provided.")
        with db_session() as active_db_session:
            active_db_session: Session
            if plate_id and not type_id:
                # Fetch the plate using plate_id to get its type_id
                stmt = select(WellPlateDBModel).filter_by(id=plate_id)
                plate: WellPlateDBModel = active_db_session.execute(
                    stmt
                ).scalar_one_or_none()
                if not plate:
                    raise ValueError(f"Plate with given id {plate_id} not found.")

                if type_id != plate.type_id and type_id is not None:
                    raise ValueError(
                        f"Type id {type_id} does not match the given plate type id {plate.type_id}"
                    )
                type_id = plate.type_id

            # Fetch the plate type using type_id
            stmt = select(PlateTypeDBModel).filter_by(id=type_id)
            plate_type = active_db_session.execute(stmt).scalar_one_or_none()
            if not plate_type:
                raise ValueError(f"Plate type with id {type_id} not found.")

        return PlateTypeModel.model_validate(plate_type)


class WellplateService:
    """
    Service class for interacting with well plates in the database.
    """

    def __init__(self, session_maker: sessionmaker = SessionLocal):
        self.session_maker = session_maker

    def create_plate(self, plate_data: WellplateWriteModel) -> WellPlateDBModel:
        with self.session_maker() as db_session:
            try:
                plate: WellPlateDBModel = WellPlateDBModel(**plate_data.model_dump())
                db_session.add(plate)
                db_session.commit()
                db_session.refresh(plate)
                return plate
            except SQLAlchemyError as e:
                db_session.rollback()
                raise ValueError(f"Error creating plate: {e}")

    def get_plate(self, plate_id: int) -> WellplateReadModel:
        with self.session_maker() as db_session:
            stmt = select(WellPlateDBModel).filter_by(id=plate_id)
            plate = db_session.execute(stmt).scalar()
            if not plate:
                # raise ValueError(f"Plate with id {plate_id} not found.")
                return None
            return WellplateReadModel.model_validate(plate)

    def get_plate_type(self, type_id: int) -> PlateTypeModel:
        with self.session_maker() as db_session:
            stmt = select(PlateTypeDBModel).filter_by(id=type_id)
            plate = db_session.execute(stmt).scalar()
            if not plate:
                raise ValueError(f"Plate type with id {type_id} not found.")
            return PlateTypeModel.model_validate(plate)

    def get_wells(self, plate_id: int) -> List[WellReadModel]:
        with self.session_maker() as db_session:
            stmt = select(WellDBModel).filter_by(plate_id=plate_id)
            wells = db_session.execute(stmt).scalars().all()
            return [WellReadModel.model_validate(well) for well in wells]

    def update_plate(self, plate_id: int, updates: dict) -> WellPlateDBModel:
        with self.session_maker() as db_session:
            try:
                updates = WellplateWriteModel(**updates).model_dump()
                stmt = select(WellPlateDBModel).filter_by(id=plate_id)
                plate = db_session.execute(stmt).scalar()
                if not plate:
                    raise ValueError(f"Plate with id {plate_id} not found.")
                for key, value in updates.items():
                    setattr(plate, key, value)
                db_session.commit()
                db_session.refresh(plate)
                return plate
            except SQLAlchemyError as e:
                db_session.rollback()
                raise ValueError(f"Error updating plate: {e}")

    def activate_plate(self, plate_id: int) -> WellplateReadModel:
        with self.session_maker() as db_session:
            try:
                db_session.execute(update(WellPlateDBModel).values(current=False))
                stmt = select(WellPlateDBModel).filter_by(id=plate_id)
                plate = db_session.execute(stmt).scalar()
                if not plate:
                    raise ValueError(f"Plate with id {plate_id} not found.")
                plate.current = True
                db_session.commit()

                return WellplateReadModel.model_validate(plate)
            except SQLAlchemyError as e:
                db_session.rollback()
                raise ValueError(f"Error activating plate: {e}")

    def deactivate_plate(
        self, plate_id: int, new_active_plate_id: int = None
    ) -> WellplateReadModel:
        with self.session_maker() as db_session:
            try:
                stmt = select(WellPlateDBModel).filter_by(id=plate_id)
                plate = db_session.execute(stmt).scalar()
                if not plate:
                    raise ValueError(f"Plate with id {plate_id} not found.")
                plate.current = False
                db_session.commit()
                if new_active_plate_id:
                    new_active_plate = db_session.execute(
                        select(WellPlateDBModel).filter_by(id=new_active_plate_id)
                    ).scalar_one_or_none()
                    if new_active_plate:
                        new_active_plate.current = True
                        db_session.commit()

                return WellplateReadModel.model_validate(plate)
            except SQLAlchemyError as e:
                db_session.rollback()
                raise ValueError(f"Error deactivating plate: {e}")

    def get_active_plate(self) -> WellplateReadModel:
        with self.session_maker() as db_session:
            stmt = select(WellPlateDBModel).filter_by(current=True)
            plate = db_session.execute(stmt).scalar()
            if not plate:
                return None
            if not plate.name:
                plate.name = f"{plate.id}"
                db_session.commit()
            return WellplateReadModel.model_validate(plate)

    def check_plate_exists(self, plate_id: int) -> bool:
        with self.session_maker() as db_session:
            stmt = select(WellPlateDBModel).filter_by(id=plate_id)
            plate = db_session.execute(stmt).scalar()
            return plate is not None

    def get_plate_types(self) -> List[PlateTypeModel]:
        """
        Fetches all plate types from the database.

        Returns:
            List[PlateTypeModel]: List of Pydantic models representing all plate types.
            str: Formatted string table of plate types.
        """
        with self.session_maker() as db_session:
            stmt = select(PlateTypeDBModel)
            plate_types = db_session.execute(stmt).scalars().all()
            plate_type_list = [
                PlateTypeModel.model_validate(plate_type) for plate_type in plate_types
            ]

            return plate_type_list

    def tabulate_plate_type_list(self, plate_types: List[PlateTypeModel] = None) -> str:
        """
        Prints a formatted string table of plate types.

        Returns:
            str: Formatted string table of plate types.
        """
        if not plate_types:
            plate_types = self.get_plate_types()
        if not plate_types:
            return "No plate types found."

        header = f"{'ID':<5} {'Substrate':<15} {'Gasket':<15} {'Count':<6}"
        separator = "-" * len(header)
        rows = [
            f"{plate.id:<5} {plate.substrate:<15} {plate.gasket:<15} {plate.count:<6}"
            for plate in plate_types
        ]

        return "\n".join([header, separator] + rows)


class WellTypeService:
    """
    Class for interacting with well types in the database, adding, updating, and deleting well types.
    """

    def __init__(self, session_maker: sessionmaker = SessionLocal):
        self.session_maker = session_maker

    def create_plate_type(self, plate_type_data: PlateTypeModel) -> PlateTypeDBModel:
        """
        Creates a new well plate type in the database.

        Args:
            plate_type_data (PlateTypeModel): Pydantic model with well plate type details.

        Returns:
            PlateTypeDBModel: SQLAlchemy model instance representing the new well plate type.
        """
        with self.session_maker() as db_session:
            try:
                plate_type: PlateTypeDBModel = PlateTypeDBModel(
                    **plate_type_data.model_dump()
                )
                db_session.add(plate_type)
                db_session.commit()
                db_session.refresh(plate_type)
                return plate_type
            except SQLAlchemyError as e:
                db_session.rollback()
                raise ValueError(f"Error creating plate type: {e}")

    def get_plate_type(self, type_id: int) -> PlateTypeModel:
        """
        Fetches a well plate type by ID from the database.

        Args:
            type_id (int): The ID of the well plate type to fetch.

        Returns:
            PlateTypeModel: Pydantic model representing the well plate type.
        """
        with self.session_maker() as db_session:
            stmt = select(PlateTypeDBModel).filter_by(id=type_id)
            plate_type = db_session.execute(stmt).scalar()
            if not plate_type:
                raise ValueError(f"Plate type with id {type_id} not found.")
            return PlateTypeModel.model_validate(plate_type)

    def update_plate_type(self, type_id: int, updates: dict) -> PlateTypeDBModel:
        """
        Updates an existing well plate type in the database.

        Args:
            type_id (int): The ID of the well plate type to update.
            updates (dict): Key-value pairs of attributes to update.

        Returns:
            PlateTypeDBModel: Updated SQLAlchemy model instance.
        """
        with self.session_maker() as db_session:
            try:
                updates = PlateTypeModel(**updates).model_dump()
                stmt = select(PlateTypeDBModel).filter_by(id=type_id)
                plate_type = db_session.execute(stmt).scalar()
                if not plate_type:
                    raise ValueError(f"Plate type with id {type_id} not found.")
                for key, value in updates.items():
                    setattr(
                        plate=db_session.execute(stmt).scalar(), name=key, value=value
                    )
                    setattr(plate_type, key, value)
                db_session.commit()
                db_session.refresh(plate_type)
                return plate_type
            except SQLAlchemyError as e:
                db_session.rollback()
                raise ValueError(f"Error updating plate type: {e}")

    def delete_plate_type(self, type_id: int) -> None:
        """
        Deletes a well plate type from the database.

        Args:
            type_id (int): The ID of the well plate type to delete.
        """
        with self.session_maker() as db_session:
            try:
                stmt = select(PlateTypeDBModel).filter_by(id=type_id)
                plate_type = db_session.execute(stmt).scalar()
                if not plate_type:
                    raise ValueError(f"Plate type with id {type_id} not found.")
                db_session.delete(plate_type)
                db_session.commit()
            except SQLAlchemyError as e:
                db_session.rollback()
                raise ValueError(f"Error deleting plate type: {e}")

    def list_plate_types(self) -> List[PlateTypeModel]:
        """
        Lists all well plate types in the database.
        Returns:
            List[PlateTypeModel]: List of Pydantic models representing all well plate types.
        """
        with self.session_maker() as db_session:
            stmt = select(PlateTypeDBModel)
            plate_types = db_session.execute(stmt).scalars().all()
            return [
                PlateTypeModel.model_validate(plate_type) for plate_type in plate_types
            ]
