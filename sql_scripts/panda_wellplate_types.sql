--
-- File generated with SQLiteStudio v3.4.17 on Wed Apr 23 14:44:32 2025
--
-- Text encoding used: System
--
PRAGMA foreign_keys = off;
BEGIN TRANSACTION;

-- Table: panda_wellplate_types
DROP TABLE IF EXISTS panda_wellplate_types;

CREATE TABLE IF NOT EXISTS panda_wellplate_types (
    id                   INTEGER PRIMARY KEY,
    substrate            TEXT,
    gasket               TEXT,
    count                INTEGER,
    shape                TEXT,
    radius_mm            REAL,
    x_spacing            REAL,
    gasket_height_mm     REAL,
    max_liquid_height_mm REAL,
    capacity_ul          REAL,
    rows                 TEXT    DEFAULT ABCDEFGH,
    cols                 INTEGER DEFAULT (12),
    y_spacing            REAL,
    gasket_length_mm     REAL,
    gasket_width_mm      REAL,
    x_offset             REAL,
    y_offset             REAL,
    base_thickness       REAL    DEFAULT (1) 
);


INSERT INTO panda_wellplate_types (
                                      id,
                                      substrate,
                                      gasket,
                                      count,
                                      shape,
                                      radius_mm,
                                      x_spacing,
                                      gasket_height_mm,
                                      max_liquid_height_mm,
                                      capacity_ul,
                                      rows,
                                      cols,
                                      y_spacing,
                                      gasket_length_mm,
                                      gasket_width_mm,
                                      x_offset,
                                      y_offset,
                                      base_thickness
                                  )
                                  VALUES (
                                      3,
                                      'gold',
                                      'pdms',
                                      96,
                                      'circular',
                                      3.25,
                                      8.9,
                                      6.0,
                                      4.5,
                                      150.0,
                                      'ABCDEFGH',
                                      12,
                                      8.9,
                                      110.0,
                                      74.0,
                                      10.5,
                                      10.5,
                                      1.0
                                  );

INSERT INTO panda_wellplate_types (
                                      id,
                                      substrate,
                                      gasket,
                                      count,
                                      shape,
                                      radius_mm,
                                      x_spacing,
                                      gasket_height_mm,
                                      max_liquid_height_mm,
                                      capacity_ul,
                                      rows,
                                      cols,
                                      y_spacing,
                                      gasket_length_mm,
                                      gasket_width_mm,
                                      x_offset,
                                      y_offset,
                                      base_thickness
                                  )
                                  VALUES (
                                      4,
                                      'ito',
                                      'pdms',
                                      96,
                                      'circular',
                                      3.25,
                                      9.0,
                                      6.0,
                                      4.0,
                                      130.0,
                                      'ABCDEFGH',
                                      12,
                                      9.0,
                                      110.0,
                                      74.0,
                                      5.5,
                                      5.5,
                                      1.0
                                  );

INSERT INTO panda_wellplate_types (
                                      id,
                                      substrate,
                                      gasket,
                                      count,
                                      shape,
                                      radius_mm,
                                      x_spacing,
                                      gasket_height_mm,
                                      max_liquid_height_mm,
                                      capacity_ul,
                                      rows,
                                      cols,
                                      y_spacing,
                                      gasket_length_mm,
                                      gasket_width_mm,
                                      x_offset,
                                      y_offset,
                                      base_thickness
                                  )
                                  VALUES (
                                      5,
                                      'plastic',
                                      'standard',
                                      96,
                                      'circular',
                                      3.48,
                                      9.0,
                                      10.9,
                                      8.5,
                                      500.0,
                                      'ABCDEFGH',
                                      12,
                                      9.0,
                                      110.0,
                                      74.0,
                                      10.5,
                                      10.5,
                                      1.0
                                  );

INSERT INTO panda_wellplate_types (
                                      id,
                                      substrate,
                                      gasket,
                                      count,
                                      shape,
                                      radius_mm,
                                      x_spacing,
                                      gasket_height_mm,
                                      max_liquid_height_mm,
                                      capacity_ul,
                                      rows,
                                      cols,
                                      y_spacing,
                                      gasket_length_mm,
                                      gasket_width_mm,
                                      x_offset,
                                      y_offset,
                                      base_thickness
                                  )
                                  VALUES (
                                      7,
                                      'gold',
                                      'pdms',
                                      50,
                                      'circular',
                                      5.0,
                                      13.5,
                                      6.0,
                                      4.5,
                                      350.0,
                                      'ABCDE',
                                      8,
                                      14.0,
                                      110.0,
                                      74.0,
                                      7.75,
                                      9.0,
                                      1.0
                                  );

COMMIT TRANSACTION;
PRAGMA foreign_keys = on;
