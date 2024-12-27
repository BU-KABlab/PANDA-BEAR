from panda_lib.vials import (
    import_vial_csv_file,
    input_new_vial_values,
    read_vials,
)

# # Setup an in-memory SQLite database for testing
# DATABASE_URL = "sqlite:///:memory:"
# engine = create_engine(DATABASE_URL)
# SessionLocal = sessionmaker(bind=engine)

# # Create the tables in the in-memory database
# Base.metadata.create_all(engine)

# Create new vials
input_new_vial_values("stock")
input_new_vial_values("waste")

a, b = read_vials()

print("Stock Vials")
for vial in a:
    print(vial)

print("Waste Vials")
for vial in b:
    print(vial)

# Export the template csv
# generate_template_vial_csv_file()

# Import a csv file
import_vial_csv_file()
