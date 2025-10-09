import logging
import re
from typing import List, Optional, Callable, ClassVar, Tuple
from datetime import datetime, timezone
from sqlalchemy import select, update, delete, func, text, Integer, cast
from sqlalchemy.sql import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from panda_shared.config.config_tools import get_unit_id
from panda_shared.db_setup import SessionLocal

from ..sql_tools import PlateTypes as PlateTypeDBModel
from ..sql_tools import Vials  # SQLAlchemy models
from ..sql_tools import WellModel as WellDBModel
from ..sql_tools import Wellplates as WellPlateDBModel
from ..sql_tools import TipModel as TipDBModel
from ..sql_tools import Racks as RackDBModel
from ..sql_tools import RackTypes as RackTypeDBModel
from .schemas import (  # PyDanctic models
    PlateTypeModel,
    TipReadModel,
    TipWriteModel,
    RackTypeModel,
    RackReadModel,
    RackWriteModel,
    VialReadModel,
    VialWriteModel,
    WellplateReadModel,
    WellplateWriteModel,
    WellReadModel,
    WellWriteModel,
)

def _now_dt():
    return datetime.now(timezone.utc)

class TipService:
    def __init__(self, session_maker=SessionLocal):
        self.session_maker = session_maker

    # (optional) legacy shim — safe to keep
    def execute(self, stmt, params=None, *, return_scalars=False, fetch_all=True):
        with self.session_maker() as s:
            res = s.execute(text(stmt) if isinstance(stmt, str) else stmt, params or {})
            if return_scalars:
                return res.scalars().all() if fetch_all else res.scalars().first()
            return res.fetchall() if fetch_all else res.first()

    def get_tip(self, tip_id: str, rack_id: int) -> Optional[TipReadModel]:
        with self.session_maker() as session:
            tip = session.execute(
                select(TipDBModel).where(
                    TipDBModel.rack_id == rack_id, TipDBModel.tip_id == tip_id
                )
            ).scalar_one_or_none()
            return TipReadModel.model_validate(tip) if tip else None

    def compute_tip_xy(
        self,
        rack_id: int,
        tip_id: str,
        session: Optional[Session] = None,
    ) -> Tuple[float, float, float]:
        def _solve(s: Session) -> Tuple[float, float, float]:
            rack: RackDBModel = s.execute(
                select(RackDBModel).where(RackDBModel.id == rack_id)
            ).scalar_one()
            tt: RackTypeDBModel = rack.type

            # parse "A1"
            row_label = "".join(ch for ch in tip_id if ch.isalpha()).upper()
            col_num = int("".join(ch for ch in tip_id if ch.isdigit()))
            r = tt.rows.index(row_label)   # 0-based
            c = col_num - 1                # 0-based

            # A1 origin
            x = rack.a1_x + tt.x_spacing * c
            y = rack.a1_y + tt.y_spacing * r

            orient = (rack.orientation or "standard").lower()
            rows_count = len(tt.rows)
            cols_count = tt.cols
            if orient == "rot180":
                x = rack.a1_x + tt.x_spacing * (cols_count - 1 - c)
                y = rack.a1_y + tt.y_spacing * (rows_count - 1 - r)
            elif orient == "mirror_x":
                x = rack.a1_x + tt.x_spacing * (cols_count - 1 - c)
            elif orient == "mirror_y":
                y = rack.a1_y + tt.y_spacing * (rows_count - 1 - r)

            return x, y, rack.pickup_height

        if session is None:
            with self.session_maker() as s:
                return _solve(s)
        return _solve(session)

    def get_tip_coordinates(self, rack_id: int, tip_id: str) -> tuple[float, float, float]:
        with self.session_maker() as session:
            return self.compute_tip_xy(session, rack_id, tip_id)

    def get_first_unused_tip(self, rack_id: int) -> Optional[TipReadModel]:
        """
        Return the first tip with status 'new' on the given rack, ordered A1..A12, B1..B12, ...
        Assumes tip_id like 'A1', 'B12', etc.
        """
        with self.session_maker() as session:
            stmt = (
                select(TipDBModel)
                .where(
                    TipDBModel.rack_id == rack_id,
                    func.lower(TipDBModel.status) == "new",  # robust to case
                )
                .order_by(
                    func.substr(TipDBModel.tip_id, 1, 1).asc(),                 # row letter
                    cast(func.substr(TipDBModel.tip_id, 2), Integer).asc(),      # numeric col
                )
                .limit(1)
            )
            tip = session.execute(stmt).scalars().first()
            return TipReadModel.model_validate(tip) if tip else None


    def update_tip(self, tip_id: str, rack_id: int, updates: dict) -> TipDBModel:
            with self.session_maker() as s:
                try:
                    tip = s.execute(
                        select(TipDBModel).filter_by(tip_id=tip_id, rack_id=rack_id)
                    ).scalar()
                    if not tip:
                        raise ValueError(f"Tip not found for rack_id={rack_id}, tip_id={tip_id}")

                    payload = {"tip_id": tip_id, "rack_id": rack_id, **(updates or {})}

                    now = _now_dt()
                    # always bump updated
                    payload.setdefault("updated", now)
                    # set status_date only when status actually changes
                    if "status" in payload:
                        new_status = str(payload["status"]).lower()
                        old_status = (tip.status or "").lower()
                        if new_status != old_status:
                            payload.setdefault("status_date", now)

                    # If you use Pydantic, make sure its field types match (see below)
                    try:
                        data = TipWriteModel(**payload).model_dump(exclude_none=True)
                    except NameError:
                        data = {k: v for k, v in payload.items() if v is not None}

                    for k, v in data.items():
                        setattr(tip, k, v)

                    s.commit(); s.refresh(tip)
                    return tip
                except SQLAlchemyError as e:
                    s.rollback()
                    raise ValueError(f"Error updating tip: {e}") from e


    def delete_tip(self, tip_id: str, rack_id: int) -> None:
        with self.session_maker() as active_db_session:
            try:
                stmt = select(TipDBModel).filter_by(tip_id=tip_id, rack_id=rack_id)
                tip = active_db_session.execute(stmt).scalar()
                if not tip:
                    raise ValueError(f"Tip with id {tip_id} (rack {rack_id}) not found.")
                active_db_session.delete(tip)
                active_db_session.commit()
            except SQLAlchemyError as e:
                active_db_session.rollback()
                raise ValueError(f"Error deleting tip: {e}")


    def fetch_tip_type_characteristics(
        self,
        db_session: sessionmaker = SessionLocal,
        rack_id: Optional[int] = None,
        type_id: Optional[int] = None,
    ) -> RackTypeModel:
        """
        Fetches the characteristics of a tip rack type.

        Args:
            db_session (Session): The database session.
            rack_id (Optional[int]): The ID of the tip rack.
            type_id (Optional[int]): The ID of the tip rack type.

        Returns:
            RackTypeModel: The validated model of the tip rack type.

        Raises:
            ValueError: If neither rack_id nor type_id is provided.
            ValueError: If the tip rack type is not found.

        """
        if not rack_id and not type_id:
            raise ValueError("Either rack_id or type_id must be provided.")
        with db_session() as active_db_session:
            active_db_session: Session
            if rack_id and not type_id:
                # Fetch the plate using plate_id to get its type_id
                stmt = select(RackDBModel).filter_by(id=rack_id)
                rack: RackDBModel = active_db_session.execute(
                    stmt
                ).scalar_one_or_none()
                if not rack:
                    raise ValueError(f"Rack with given id {rack_id} not found.")

                if type_id != rack.type_id and type_id is not None:
                    raise ValueError(
                        f"Type id {type_id} does not match the given rack type id {rack.type_id}"
                    )
                type_id = rack.type_id

            # Fetch the plate type using type_id
            stmt = select(RackTypeDBModel).filter_by(id=type_id)
            rack_type = active_db_session.execute(stmt).scalar_one_or_none()
            if not rack_type:
                raise ValueError(f"Rack type with id {type_id} not found.")

        return RackTypeModel.model_validate(rack_type)
    
    def get_rack_for_tip(self, rack_id: int):
        # defer to RackService using the same session_maker
        return RackService(self.session_maker).get_rack(rack_id)

    
class RackService:
    """
    Service class for interacting with tip racks in the database.
    """

    def __init__(self, session_maker: sessionmaker = SessionLocal):
        self.session_maker = session_maker

    def create_rack(self, rack_data: RackWriteModel) -> RackDBModel:
        with self.session_maker() as db_session:
            try:
                rack_data.panda_unit_id = get_unit_id()
                rack: RackDBModel = RackDBModel(**rack_data.model_dump())
                db_session.add(rack)
                db_session.commit()
                db_session.refresh(rack)
                return rack
            except SQLAlchemyError as e:
                db_session.rollback()
                raise ValueError(f"Error creating rack: {e}")

    def get_rack(self, rack_id: int) -> RackReadModel:
        with self.session_maker() as db_session:
            stmt = select(RackDBModel).filter_by(id=rack_id)
            rack = db_session.execute(stmt).scalar()
            if not rack:
                # raise ValueError(f"rack with id {rack_id} not found.")
                return None
            return RackReadModel.model_validate(rack)

    def get_rack_type(self, type_id: int) -> RackTypeModel:
        with self.session_maker() as db_session:
            stmt = select(RackTypeDBModel).filter_by(id=type_id)
            rack = db_session.execute(stmt).scalar()
            if not rack:
                raise ValueError(f"rack type with id {type_id} not found.")
            return RackTypeModel.model_validate(rack)

    def get_tips(self, rack_id: int) -> List[TipReadModel]:
        with self.session_maker() as db_session:
            stmt = select(TipDBModel).filter_by(rack_id=rack_id)
            tips = db_session.execute(stmt).scalars().all()
            return [TipReadModel.model_validate(tip) for tip in tips]

    def update_rack(self, rack_id: int, updates: dict) -> RackDBModel:
        with self.session_maker() as db_session:
            try:
                updates = RackWriteModel(**updates).model_dump()
                stmt = select(RackDBModel).filter_by(id=rack_id)
                rack = db_session.execute(stmt).scalar()
                if not rack:
                    raise ValueError(f"rack with id {rack_id} not found.")
                for key, value in updates.items():
                    setattr(rack, key, value)
                db_session.commit()
                db_session.refresh(rack)
                return rack
            except SQLAlchemyError as e:
                db_session.rollback()
                raise ValueError(f"Error updating rack: {e}")

    def activate_rack(self, rack_id: int) -> RackReadModel:
        with self.session_maker() as db_session:
            try:
                db_session.execute(update(RackDBModel).values(current=False))
                stmt = select(RackDBModel).filter_by(id=rack_id)
                rack = db_session.execute(stmt).scalar()
                if not rack:
                    raise ValueError(f"rack with id {rack_id} not found.")
                rack.current = True
                db_session.commit()

                return RackReadModel.model_validate(rack)
            except SQLAlchemyError as e:
                db_session.rollback()
                raise ValueError(f"Error activating rack: {e}")

    def deactivate_rack(
        self, rack_id: int, new_active_rack_id: int = None
    ) -> RackReadModel:
        with self.session_maker() as db_session:
            try:
                stmt = select(RackDBModel).filter_by(id=rack_id)
                rack = db_session.execute(stmt).scalar()
                if not rack:
                    raise ValueError(f"rack with id {rack_id} not found.")
                rack.current = False
                db_session.commit()
                if new_active_rack_id:
                    new_active_rack = db_session.execute(
                        select(RackDBModel).filter_by(id=new_active_rack_id)
                    ).scalar_one_or_none()
                    if new_active_rack:
                        new_active_rack.current = True
                        db_session.commit()

                return RackReadModel.model_validate(rack)
            except SQLAlchemyError as e:
                db_session.rollback()
                raise ValueError(f"Error deactivating rack: {e}")

    def get_active_rack(self) -> RackReadModel:
        with self.session_maker() as db_session:
            stmt = select(RackDBModel).filter_by(current=True)
            rack = db_session.execute(stmt).scalar()
            if not rack:
                return None
            if not rack.name:
                rack.name = f"{rack.id}"
                db_session.commit()
            return RackReadModel.model_validate(rack)

    def check_rack_exists(self, rack_id: int) -> bool:
        with self.session_maker() as db_session:
            stmt = select(RackDBModel).filter_by(id=rack_id)
            rack = db_session.execute(stmt).scalar()
            return rack is not None

    def get_rack_types(self) -> List[RackTypeModel]:
        """
        Fetches all rack types from the database.

        Returns:
            List[RackTypeModel]: List of Pydantic models representing all rack types.
            str: Formatted string table of rack types.
        """
        with self.session_maker() as db_session:
            stmt = select(RackTypeDBModel)
            rack_types = db_session.execute(stmt).scalars().all()
            rack_type_list = [
                RackTypeModel.model_validate(rack_type) for rack_type in rack_types
            ]

            return rack_type_list

    def tabulate_rack_type_list(self, rack_types: List[RackTypeModel] = None) -> str:
        """
        Prints a formatted string table of rack types.

        Returns:
            str: Formatted string table of rack types.
        """
        if not rack_types:
            rack_types = self.get_rack_types()
        if not rack_types:
            return "No rack types found."

        header = f"{'ID':<5} {'Count':<6}"
        separator = "-" * len(header)
        rows = [
            f"{rack.id:<5} {rack.count:<6}"
            for rack in rack_types
        ]

        return "\n".join([header, separator] + rows)
    
    @staticmethod
    def _generate_positions_rows_x_cols_y(
        a1_x: float,
        a1_y: float,
        rows: str,
        cols: int,
        x_spacing: float,
        y_spacing: float,
        orientation: int = 0,
    ):
        o = orientation % 360

        def base_xy(r_idx, c_idx):
            return a1_x + r_idx * x_spacing, a1_y + c_idx * y_spacing

        def rotate(x, y):
            if o == 0:
                return x, y
            dx, dy = x - a1_x, y - a1_y
            if o == 90:   
                return a1_x - dy, a1_y + dx
            if o == 180:  
                return a1_x - dx, a1_y - dy
            if o == 270:  
                return a1_x + dy, a1_y - dx
            return x, y

        out = []
        for r_idx, row_letter in enumerate(rows):
            for c_idx in range(cols):
                tip_id = f"{row_letter}{c_idx + 1}"
                x, y = rotate(*base_xy(r_idx, c_idx))
                out.append((tip_id, x, y))
        return out

    def seed_tips_for_rack(
        self,                     # <-- add self
        session: Session,
        rack_id: int,
        *,
        overwrite: bool = False,
        default_status: str = "new",
    ) -> int:
        rack = session.execute(
            select(RackDBModel).where(RackDBModel.id == rack_id)
        ).scalar_one_or_none()
        if not rack:
            raise ValueError(f"Rack {rack_id} not found")

        rtype = session.execute(
            select(RackTypeDBModel).where(RackTypeDBModel.id == rack.type_id)
        ).scalar_one_or_none()
        if not rtype:
            raise ValueError(f"RackType {rack.type_id} not found for rack {rack_id}")

        # count existing tips (avoid .scalars().count())
        existing_count = session.execute(
            select(func.count(TipDBModel.id)).where(TipDBModel.rack_id == rack_id)
        ).scalar_one()

        if existing_count and not overwrite:
            return 0
        if existing_count and overwrite:
            session.execute(delete(TipDBModel).where(TipDBModel.rack_id == rack_id))

        positions = self._generate_positions_rows_x_cols_y(
            a1_x=rack.a1_x,
            a1_y=rack.a1_y,
            rows=rack.rows,
            cols=rack.cols,
            x_spacing=rtype.x_spacing,
            y_spacing=rtype.y_spacing,
            orientation=rack.orientation,
        )

        tips = [
            TipDBModel(
                rack_id=rack_id,
                tip_id=tip_id,
                status=default_status,
                coordinates={"x": float(x), "y": float(y), "z": float(rack.pickup_height)},
            )
            for tip_id, x, y in positions
        ]
        session.add_all(tips)
        session.commit()
        return len(tips)


class RackTypeService:
    """
    Class for interacting with tip types in the database, adding, updating, and deleting tip types.
    """

    def __init__(self, session_maker: sessionmaker = SessionLocal):
        self.session_maker = session_maker

    def create_rack_type(self, rack_type_data: RackTypeModel) -> RackTypeDBModel:
        """
        Creates a new tip rack type in the database.

        Args:
            rack_type_data (RackTypeModel): Pydantic model with tip rack type details.

        Returns:
            RackTypeDBModel: SQLAlchemy model instance representing the new tip rack type.
        """
        with self.session_maker() as db_session:
            try:
                rack_type: RackTypeDBModel = RackTypeDBModel(
                    **rack_type_data.model_dump()
                )
                db_session.add(rack_type)
                db_session.commit()
                db_session.refresh(rack_type)
                return rack_type
            except SQLAlchemyError as e:
                db_session.rollback()
                raise ValueError(f"Error creating rack type: {e}")

    def get_rack_type(self, type_id: int) -> RackTypeModel:
        """
        Fetches a tip rack type by ID from the database.

        Args:
            type_id (int): The ID of the tip rack type to fetch.

        Returns:
            RackTypeModel: Pydantic model representing the tip rack type.
        """
        with self.session_maker() as db_session:
            stmt = select(RackTypeDBModel).filter_by(id=type_id)
            rack_type = db_session.execute(stmt).scalar()
            if not rack_type:
                raise ValueError(f"rack type with id {type_id} not found.")
            return RackTypeModel.model_validate(rack_type)

    def update_rack_type(self, type_id: int, updates: dict) -> RackTypeDBModel:
        """
        Updates an existing tip rack type in the database.

        Args:
            type_id (int): The ID of the tip rack type to update.
            updates (dict): Key-value pairs of attributes to update.

        Returns:
            RackTypeDBModel: Updated SQLAlchemy model instance.
        """
        with self.session_maker() as db_session:
            try:
                updates = RackTypeModel(**updates).model_dump()
                stmt = select(RackTypeDBModel).filter_by(id=type_id)
                rack_type = db_session.execute(stmt).scalar()
                if not rack_type:
                    raise ValueError(f"rack type with id {type_id} not found.")
                for key, value in updates.items():
                    setattr(rack_type, key, value)
                db_session.commit()
                db_session.refresh(rack_type)
                return rack_type
            except SQLAlchemyError as e:
                db_session.rollback()
                raise ValueError(f"Error updating rack type: {e}")

    def delete_rack_type(self, type_id: int) -> None:
        """
        Deletes a tip rack type from the database.

        Args:
            type_id (int): The ID of the tip rack type to delete.
        """
        with self.session_maker() as db_session:
            try:
                stmt = select(RackTypeDBModel).filter_by(id=type_id)
                rack_type = db_session.execute(stmt).scalar()
                if not rack_type:
                    raise ValueError(f"rack type with id {type_id} not found.")
                db_session.delete(rack_type)
                db_session.commit()
            except SQLAlchemyError as e:
                db_session.rollback()
                raise ValueError(f"Error deleting rack type: {e}")

    def list_rack_types(self) -> List[RackTypeModel]:
        """
        Lists all tip rack types in the database.
        Returns:
            List[RackTypeModel]: List of Pydantic models representing all tip rack types.
        """
        with self.session_maker() as db_session:
            stmt = select(RackTypeDBModel)
            rack_types = db_session.execute(stmt).scalars().all()
            return [
                RackTypeModel.model_validate(rack_type) for rack_type in rack_types
            ]


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
                stmt = select(Vials).filter_by(
                    position=vial_data.position,
                    panda_unit_id=get_unit_id(),
                )
                vials = db_session.execute(stmt).scalars().all()
                for vial in vials:
                    vial.active = 0
                    db_session.commit()
            except SQLAlchemyError as e:
                db_session.rollback()
                raise ValueError(f"Error deactivating existing vial: {e}")

            try:
                # Convert Pydantic model to SQLAlchemy model
                vial_data.panda_unit_id = get_unit_id()
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
                stmt = select(Vials).filter_by(
                    name=name,
                    active=active_only,
                    panda_unit_id=get_unit_id(),
                )
            elif position:
                stmt = select(Vials).filter_by(
                    position=position,
                    active=active_only,
                    panda_unit_id=get_unit_id(),
                )
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
                        id=vial_id,
                        position=position,
                        active=1,
                        panda_unit_id=get_unit_id(),
                    )
                else:
                    stmt = select(Vials).filter_by(
                        position=position,
                        active=1,
                        panda_unit_id=get_unit_id(),
                    )
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
                stmt = select(Vials).filter_by(
                    position=position,
                    panda_unit_id=get_unit_id(),
                )
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
            stmt = select(Vials).filter_by(active=1, panda_unit_id=get_unit_id())
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
            stmt = select(Vials).filter_by(panda_unit_id=get_unit_id())
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
            stmt = select(Vials).filter_by(active=0, panda_unit_id=get_unit_id())
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
                plate_data.panda_unit_id = get_unit_id()
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
