import logging
from typing import List, Optional

from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from panda_lib.sql_tools.db_setup import SessionLocal
from panda_lib.sql_tools.panda_models import PlateTypes as PlateTypeDBModel
from panda_lib.sql_tools.panda_models import Vials  # SQLAlchemy models
from panda_lib.sql_tools.panda_models import WellModel as WellDBModel
from panda_lib.sql_tools.panda_models import Wellplates as WellPlateDBModel

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
                    vial.active = False
                    db_session.commit()
            except SQLAlchemyError as e:
                db_session.rollback()
                raise ValueError(f"Error deactivating existing vial: {e}")

            try:
                # Convert Pydantic model to SQLAlchemy model
                vial: Vials = Vials(**vial_data.model_dump())
                vial.active = True
                db_session.add(vial)
                db_session.commit()
                db_session.refresh(vial)
                return vial
            except SQLAlchemyError as e:
                db_session.rollback()
                raise ValueError(f"Error creating vial: {e}")

    def get_vial(self, position: str, active_only: bool = True) -> VialReadModel:
        """
        Fetches a vial by position from the database.

        Args:
            position (str): The position of the vial to fetch.

        Returns:
            VialModel: Pydantic model representing the vial.
        """
        with self.db_session_maker() as db_session:
            stmt = select(Vials).filter_by(position=position, active=active_only)
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
        with self.db_session_maker() as db_session:
            try:
                stmt = select(Vials).filter_by(position=position)
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
                    else:
                        self.logger.debug("Invalid attribute: %s. Not saved to db", key)
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

    def list_active_vials(self) -> List[VialReadModel]:
        """
        Lists all active vials in the database.

        Returns:
            List[VialModel]: List of Pydantic models representing active vials.
        """
        with self.db_session_maker() as db_session:
            stmt = select(Vials).filter_by(active=True)
            result = db_session.execute(stmt)
            vials = result.scalars().all() if result else []

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
            stmt = select(Vials).filter_by(active=False)
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
    def __init__(self, session_maker: sessionmaker = SessionLocal):
        self.session_maker = session_maker

    def create_well(self, well_data: WellWriteModel) -> WellDBModel:
        with self.session_maker() as active_db_session:
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
                stmt = select(WellDBModel).filter_by(well_id=well_id, plate_id=plate_id)
                well = active_db_session.execute(stmt).scalar()
                if not well:
                    raise ValueError(f"Well with id {well_id} not found.")
                for key, value in updates.items():
                    if hasattr(well, key):
                        setattr(well, key, value)
                    else:
                        raise ValueError(f"Invalid attribute: {key}")
                active_db_session.commit()
                active_db_session.refresh(well)
                return well
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
        db_session: Session,
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

        if plate_id and not type_id:
            # Fetch the plate using plate_id to get its type_id
            stmt = select(WellPlateDBModel).filter_by(id=plate_id)
            plate = db_session.execute(stmt).scalar_one_or_none()
            if not plate:
                raise ValueError(f"Plate with given id {plate_id} not found.")

            if type_id != plate.type_id and type_id is not None:
                raise ValueError(
                    f"Type id {type_id} does not match the given plate type id {plate.type_id}"
                )
            type_id = plate.type_id

        # Fetch the plate type using type_id
        stmt = select(PlateTypeDBModel).filter_by(id=type_id)
        plate_type = db_session.execute(stmt).scalar_one_or_none()
        if not plate_type:
            raise ValueError(f"Plate type with id {type_id} not found.")

        return PlateTypeModel.model_validate(plate_type)


class WellplateService:
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

    def get_wells(self, plate_id: int) -> List[WellWriteModel]:
        with self.session_maker() as db_session:
            stmt = select(WellDBModel).filter_by(plate_id=plate_id)
            wells = db_session.execute(stmt).scalars().all()
            return [WellWriteModel.model_validate(well) for well in wells]

    def update_plate(self, plate_id: int, updates: dict) -> WellPlateDBModel:
        with self.session_maker() as db_session:
            try:
                stmt = select(WellPlateDBModel).filter_by(id=plate_id)
                plate = db_session.execute(stmt).scalar()
                if not plate:
                    raise ValueError(f"Plate with id {plate_id} not found.")
                for key, value in updates.items():
                    if key in WellplateWriteModel.model_fields:
                        setattr(plate, key, value)
                    else:
                        print(f"Skipping read-only or invalid attribute: {key}")
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
