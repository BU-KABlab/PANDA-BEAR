# Utility Scripts

This directory contains standalone utility scripts for various tasks.

## Scripts

### panda-slack-bot.py

Standalone Slack bot runner for PANDA SDL. Allows running the Slack bot in parallel with the main PANDA SDL application.

**Usage:**
```bash
# Production mode (default)
python scripts/panda-slack-bot.py

# Testing mode
python scripts/panda-slack-bot.py --testing
```

**Note**: After installation, you can also use the CLI command:
```bash
panda-slack-bot [--testing] [--production]
```

See [SLACK_BOT_ORGANIZATION.md](../SLACK_BOT_ORGANIZATION.md) for detailed documentation.

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

These scripts are utility tools and are not part of the core PANDA-BEAR library. They may require modification for your specific use case.
