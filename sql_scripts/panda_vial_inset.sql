--
-- File generated with SQLiteStudio v3.4.17 on Wed Apr 23 14:44:32 2025
--
-- Text encoding used: System
--
PRAGMA foreign_keys = off;
BEGIN TRANSACTION;

INSERT INTO panda_vials
("position", category, name, contents, viscosity_cp, concentration, density, height, radius, volume, capacity, contamination, coordinates, base_thickness, dead_volume, updated, active, panda_unit_id)
VALUES('s1', 0, 'pama_200', '{"pama_200": 10000.0}', 1.0, 200.0, 1.0, 66.0, 14.0, 10000.0, 20000.0, 0, '{"x": -14, "y": 5, "z": -181.0}', 1.0, 0.0, '2025-07-23', 1, 2);
INSERT INTO panda_vials
("position", category, name, contents, viscosity_cp, concentration, density, height, radius, volume, capacity, contamination, coordinates, base_thickness, dead_volume, updated, active, panda_unit_id)
VALUES('s2', 0, 'electrolyte', '{"electrolyte": 10000.0}', 1.0, 0.0, 1.0, 66.0, 14.0, 10000.0, 20000.0, 0, '{"x": -14, "y": -28, "z": -181.0}', 1.0, 0.0, '2025-07-23 17:47:23', 1, 2);
INSERT INTO panda_vials
("position", category, name, contents, viscosity_cp, concentration, density, height, radius, volume, capacity, contamination, coordinates, base_thickness, dead_volume, updated, active, panda_unit_id)
VALUES('s3', 0, 'dmf', '{"dmf": 10000.0}', 1.0, 0.0, 1.0, 66.0, 14.0, 10000.0, 20000.0, 0, '{"x": -14, "y": -61, "z": -181.0}', 1.0, 0.0, '2025-07-23 17:47:23', 1, 2);
INSERT INTO panda_vials
("position", category, name, contents, viscosity_cp, concentration, density, height, radius, volume, capacity, contamination, coordinates, base_thickness, dead_volume, updated, active, panda_unit_id)
VALUES('s4', 0, 'acn', '{"acn": 10000.0}', 1.0, 0.0, 1.0, 66.0, 14.0, 10000.0, 20000.0, 0, '{"x": -14, "y": -94, "z": -181.0}', 1.0, 0.0, '2025-07-23 17:47:23', 1, 2);
INSERT INTO panda_vials
("position", category, name, contents, viscosity_cp, concentration, density, height, radius, volume, capacity, contamination, coordinates, base_thickness, dead_volume, updated, active, panda_unit_id)
VALUES('s5', 0, 'ipa', '{"ipa": 20000.0}', 1.0, 0.0, 1.0, 66.0, 14.0, 20000.0, 20000.0, 0, '{"x": -14, "y": -127, "z": -181.0}', 1.0, 0.0, '2025-07-23 17:47:23', 1, 2);
INSERT INTO panda_vials
("position", category, name, contents, viscosity_cp, concentration, density, height, radius, volume, capacity, contamination, coordinates, base_thickness, dead_volume, updated, active, panda_unit_id)
VALUES('s6', 0, 'water', '{"water": 10000.0}', 1.0, 0.0, 1.0, 66.0, 14.0, 10000.0, 20000.0, 0, '{"x": -14, "y": -160, "z": -181.0}', 1.0, 0.0, '2025-07-23 17:47:24', 1, 2);
INSERT INTO panda_vials
("position", category, name, contents, viscosity_cp, concentration, density, height, radius, volume, capacity, contamination, coordinates, base_thickness, dead_volume, updated, active, panda_unit_id)
VALUES('w0', 1, 'waste', '{"water": 0.0}', 1.0, 0.0, 1.0, 66.0, 14.0, 0.0, 20000.0, 0, '{"x": -114, "y": 5, "z": -196.0}', 1.0, 0.0, '2025-07-23 17:52:22', 1, 2);
INSERT INTO panda_vials
("position", category, name, contents, viscosity_cp, concentration, density, height, radius, volume, capacity, contamination, coordinates, base_thickness, dead_volume, updated, active, panda_unit_id)
VALUES('w1', 1, 'waste', '{"water": 0.0}', 1.0, 0.0, 1.0, 66.0, 14.0, 0.0, 20000.0, 0, '{"x": -114, "y": -28, "z": -196.0}', 1.0, 0.0, '2025-07-23 17:52:22', 1, 2);
INSERT INTO panda_vials
("position", category, name, contents, viscosity_cp, concentration, density, height, radius, volume, capacity, contamination, coordinates, base_thickness, dead_volume, updated, active, panda_unit_id)
VALUES('w2', 1, 'waste', '{"water": 0.0}', 1.0, 0.0, 1.0, 66.0, 14.0, 0.0, 20000.0, 0, '{"x": -114, "y": -61, "z": -196.0}', 1.0, 0.0, '2025-07-23 17:52:22', 1, 2);
INSERT INTO panda_vials
("position", category, name, contents, viscosity_cp, concentration, density, height, radius, volume, capacity, contamination, coordinates, base_thickness, dead_volume, updated, active, panda_unit_id)
VALUES('w3', 1, 'waste', '{"water": 0.0}', 1.0, 0.0, 1.0, 66.0, 14.0, 0.0, 20000.0, 0, '{"x": -114, "y": -94, "z": -196.0}', 1.0, 0.0, '2025-07-23 17:52:22', 1, 2);


COMMIT TRANSACTION;
PRAGMA foreign_keys = on;
