import os
import sys

# from datetime import datetime

# import pytest
# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker

# from hardware.pipette.sql_pipette import Pipette as PipetteModel
# from panda_lib.sql_tools.panda_models import Base

# Add the root directory of your project to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# DATABASE_URL = "sqlite:///:memory:"


# @pytest.fixture(scope="function")
# def db_session():
#     """Create a new database session for a test."""
#     engine = create_engine(DATABASE_URL)
#     SessionLocal = sessionmaker(bind=engine)
#     Base.metadata.create_all(engine)
#     session = SessionLocal()
#     yield session
#     session.close()
#     Base.metadata.drop_all(engine)


# @pytest.fixture(scope="function")
# def session_maker():
#     engine = create_engine(DATABASE_URL)
#     return sessionmaker(bind=engine)


# @pytest.fixture(scope="function")
# def populate_pipette_table(session_maker):
#     """Populate the panda_pipette table with initial data."""
#     pipette_data = [
#         (
#             1,
#             200,
#             0.2,
#             0,
#             0,
#             {"edot": 0.0, "rinse": 0.0, "liclo4": 0.0},
#             datetime(2024, 12, 27, 1, 52, 35, 723000),
#             0,
#             159,
#         ),
#         (2, 200, 0.2, 0, 0, {}, datetime(2024, 12, 27, 1, 52, 35, 724000), 1, 0),
#     ]
#     session = session_maker()
#     for pipette in pipette_data:
#         session.add(
#             PipetteModel(
#                 id=pipette[0],
#                 capacity_ul=pipette[1],
#                 capacity_ml=pipette[2],
#                 volume_ul=pipette[3],
#                 volume_ml=pipette[4],
#                 contents=pipette[5],
#                 created_at=pipette[6],
#                 is_active=pipette[7],
#                 user_id=pipette[8],
#             )
#         )
#     session.commit()
#     yield
#     session.query(PipetteModel).delete()
#     session.commit()
#     session.close()
