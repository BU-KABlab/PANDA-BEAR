from panda_lib.labware.services import RackService
from panda_shared.db_setup import SessionLocal

if __name__ == "__main__":
    rack_id = 1  # change to your actual rack ID
    overwrite = True

    session = SessionLocal()
    rack_service = RackService()

    count = rack_service.seed_tips_for_rack(session, rack_id, overwrite=overwrite)
    print(f"Seeded {count} tips for rack {rack_id}")
    session.close()
