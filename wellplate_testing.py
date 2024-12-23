from panda_lib.sql_tools.db_setup import SessionLocal
from panda_lib.wellplate_v2 import Well_v2 as Well
from panda_lib.wellplate_v2 import Wellplate

# new_wellplate = Wellplate(
#     session=SessionLocal(),
#     plate_id=999,
#     type_id=4,
#     create_new=True,
#     a1_x=-222.5,
#     a1_y=-78,
#     orientation=3,
#     rows="ABCDEFGH",
#     cols=12,
#     echem_height=2,
#     image_height=25,
#     coordinates={"x": 0, "y": 0, "z": 0},
#     base_thickness=1,
#     height=10,
#     top=10,
#     bottom=0,
#     name="Test Wellplate 1",
# )

# print(new_wellplate)

existing_wellplate: Wellplate = Wellplate(
    session=SessionLocal(),
    plate_id=999,
    create_new=False,
)

print(existing_wellplate)

a1: Well = existing_wellplate.wells["A1"]

a1.update_contents({"name": "Test Chemical", "concentration": 1.0, "volume": 10}, 140)
print(a1.contents)
print(a1.volume)
print(a1.volume_height)
a1.update_contents({"name": "Test Chemical", "concentration": 1.0, "volume": 10}, -20)
print(a1.contents)
print(a1.volume)
print(a1.volume_height)
a1.update_contents({"name": "Test Chemical", "concentration": 1.0, "volume": 10}, 0)
print(a1.contents)
print(a1.volume)
print(a1.volume_height)
a1.update_contents({"name": "Test Chemical", "concentration": 1.0, "volume": 10}, -120)
print(a1.contents)
print(a1.volume)
print(a1.volume_height)
