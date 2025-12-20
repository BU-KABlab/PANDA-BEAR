# Utility Scripts

This directory contains standalone utility scripts for various tasks.

## Scripts

### LHSgenerator.py

Generates Latin Hypercube samples for experimental design.

**Usage:**
```bash
python scripts/LHSgenerator.py
```

Generates a CSV file with parameter combinations for polymer experiments.

### SQLwellplategenerator.py

Generates SQL UPDATE statements for wellplate coordinates based on corner coordinates.

**Usage:**
```bash
# Edit the script to set your plate_id and coordinates
python scripts/SQLwellplategenerator.py
```

**Configuration:**
Edit the script to set:
- `plate_id`: The database ID of your wellplate
- `rows`: Row letters (e.g., "ABCDE")
- `cols`: Number of columns
- `a1`: A1 corner coordinates (x, y, z)
- `e8`: E8 corner coordinates (x, y, z)

## Notes

These scripts are utility tools and are not part of the core PANDA-SDL library. They may require modification for your specific use case.
