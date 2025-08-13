UPDATE panda_vials SET coordinates = '{"x": -20, "y": 7, "z": -182.7}' WHERE id = 1;
UPDATE panda_vials SET coordinates = '{"x": -20, "y": -26, "z": -182.7}' WHERE id = 2;
UPDATE panda_vials SET coordinates = '{"x": -20, "y": -59, "z": -182.7}' WHERE id = 3;
UPDATE panda_vials SET coordinates = '{"x": -20, "y": -92, "z": -182.7}' WHERE id = 4;
UPDATE panda_vials SET coordinates = '{"x": -20, "y": -125, "z": -182.7}' WHERE id = 5;
UPDATE panda_vials SET coordinates = '{"x": -20, "y": -158, "z": -182.7}' WHERE id = 6;
UPDATE panda_vials SET coordinates = '{"x": -122, "y": 2, "z": -197.8}' WHERE id = 7;
UPDATE panda_vials SET coordinates = '{"x": -122, "y": -31, "z": -197.8}' WHERE id = 8;
UPDATE panda_vials SET coordinates = '{"x": -122, "y": -64, "z": -197.8}' WHERE id = 9;
UPDATE panda_vials SET coordinates = '{"x": -122, "y": -97, "z": -197.8}' WHERE id = 10;
UPDATE panda_vials SET coordinates = '{"x": -394, "y": -92, "z": -197.8}' WHERE id = 11;


UPDATE panda_well_hx SET status = 'errored' WHERE plate_id = 120 AND well_id = 'A1';
UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 120 AND well_id = 'A2';
UPDATE panda_well_hx SET status = 'new', contents = '{}', volume = '0' WHERE plate_id = 120 AND well_id = 'B7';
UPDATE panda_wellplates SET echem_height = '-187' WHERE id = 120;

UPDATE panda_tip_hx SET pickup_height = '-188.8' WHERE rack_id = 1;

DELETE FROM panda_pipette WHERE id = 1;

UPDATE panda_vials SET contents = '{"dmf": 19000}', volume = '19000' WHERE id = 3;
UPDATE panda_vials SET contents = '{"acn": 19000}', volume = '19000' WHERE id = 4;
UPDATE panda_vials SET contents = '{"ipa": 19000}', volume = '19000' WHERE id = 5;
UPDATE panda_vials SET contents = '{"ipa": 1000}', volume = '1000' WHERE id = 7;

UPDATE panda_well_hx SET coordinates = '{"x": -228, "y": -151.0, "z": -194}' WHERE plate_id = 120 AND well_id = 'A1';
UPDATE panda_well_hx SET coordinates = '{"x": -228, "y": -164.5, "z": -194}' WHERE plate_id = 120 AND well_id = 'A2';
UPDATE panda_well_hx SET coordinates = '{"x": -228, "y": -178, "z": -194}' WHERE plate_id = 120 AND well_id = 'A3';
UPDATE panda_well_hx SET coordinates = '{"x": -228, "y": -191.5, "z": -194}' WHERE plate_id = 120 AND well_id = 'A4';
UPDATE panda_well_hx SET coordinates = '{"x": -228, "y": -205, "z": -194}' WHERE plate_id = 120 AND well_id = 'A5';
UPDATE panda_well_hx SET coordinates = '{"x": -228, "y": -218.5, "z": -194}' WHERE plate_id = 120 AND well_id = 'A6';
UPDATE panda_well_hx SET coordinates = '{"x": -228, "y": -232, "z": -194}' WHERE plate_id = 120 AND well_id = 'A7';
UPDATE panda_well_hx SET coordinates = '{"x": -228, "y": -245.5, "z": -194}' WHERE plate_id = 120 AND well_id = 'A8';
UPDATE panda_well_hx SET coordinates = '{"x": -242, "y": -151.0, "z": -194}' WHERE plate_id = 120 AND well_id = 'B1';
UPDATE panda_well_hx SET coordinates = '{"x": -242, "y": -164.5, "z": -194}' WHERE plate_id = 120 AND well_id = 'B2';
UPDATE panda_well_hx SET coordinates = '{"x": -242, "y": -178, "z": -194}' WHERE plate_id = 120 AND well_id = 'B3';
UPDATE panda_well_hx SET coordinates = '{"x": -242, "y": -191.5, "z": -194}' WHERE plate_id = 120 AND well_id = 'B4';
UPDATE panda_well_hx SET coordinates = '{"x": -242, "y": -205, "z": -194}' WHERE plate_id = 120 AND well_id = 'B5';
UPDATE panda_well_hx SET coordinates = '{"x": -242, "y": -218.5, "z": -194}' WHERE plate_id = 120 AND well_id = 'B6';
UPDATE panda_well_hx SET coordinates = '{"x": -242, "y": -232, "z": -194}' WHERE plate_id = 120 AND well_id = 'B7';
UPDATE panda_well_hx SET coordinates = '{"x": -242, "y": -245.5, "z": -194}' WHERE plate_id = 120 AND well_id = 'B8';
UPDATE panda_well_hx SET coordinates = '{"x": -256, "y": -151.0, "z": -194}' WHERE plate_id = 120 AND well_id = 'C1';
UPDATE panda_well_hx SET coordinates = '{"x": -256, "y": -164.5, "z": -194}' WHERE plate_id = 120 AND well_id = 'C2';
UPDATE panda_well_hx SET coordinates = '{"x": -256, "y": -178, "z": -194}' WHERE plate_id = 120 AND well_id = 'C3';
UPDATE panda_well_hx SET coordinates = '{"x": -256, "y": -191.5, "z": -194}' WHERE plate_id = 120 AND well_id = 'C4';
UPDATE panda_well_hx SET coordinates = '{"x": -256, "y": -205, "z": -194}' WHERE plate_id = 120 AND well_id = 'C5';
UPDATE panda_well_hx SET coordinates = '{"x": -256, "y": -218.5, "z": -194}' WHERE plate_id = 120 AND well_id = 'C6';
UPDATE panda_well_hx SET coordinates = '{"x": -256, "y": -232, "z": -194}' WHERE plate_id = 120 AND well_id = 'C7';
UPDATE panda_well_hx SET coordinates = '{"x": -256, "y": -245.5, "z": -194}' WHERE plate_id = 120 AND well_id = 'C8';
UPDATE panda_well_hx SET coordinates = '{"x": -270, "y": -151.0, "z": -194}' WHERE plate_id = 120 AND well_id = 'D1';
UPDATE panda_well_hx SET coordinates = '{"x": -270, "y": -164.5, "z": -194}' WHERE plate_id = 120 AND well_id = 'D2';
UPDATE panda_well_hx SET coordinates = '{"x": -270, "y": -178, "z": -194}' WHERE plate_id = 120 AND well_id = 'D3';
UPDATE panda_well_hx SET coordinates = '{"x": -270, "y": -191.5, "z": -194}' WHERE plate_id = 120 AND well_id = 'D4';
UPDATE panda_well_hx SET coordinates = '{"x": -270, "y": -205, "z": -194}' WHERE plate_id = 120 AND well_id = 'D5';
UPDATE panda_well_hx SET coordinates = '{"x": -270, "y": -218.5, "z": -194}' WHERE plate_id = 120 AND well_id = 'D6';
UPDATE panda_well_hx SET coordinates = '{"x": -270, "y": -232, "z": -194}' WHERE plate_id = 120 AND well_id = 'D7';
UPDATE panda_well_hx SET coordinates = '{"x": -270, "y": -245.5, "z": -194}' WHERE plate_id = 120 AND well_id = 'D8';
UPDATE panda_well_hx SET coordinates = '{"x": -284, "y": -151.0, "z": -194}' WHERE plate_id = 120 AND well_id = 'E1';
UPDATE panda_well_hx SET coordinates = '{"x": -284, "y": -164.5, "z": -194}' WHERE plate_id = 120 AND well_id = 'E2';
UPDATE panda_well_hx SET coordinates = '{"x": -284, "y": -178, "z": -194}' WHERE plate_id = 120 AND well_id = 'E3';
UPDATE panda_well_hx SET coordinates = '{"x": -284, "y": -191.5, "z": -194}' WHERE plate_id = 120 AND well_id = 'E4';
UPDATE panda_well_hx SET coordinates = '{"x": -284, "y": -205, "z": -194}' WHERE plate_id = 120 AND well_id = 'E5';
UPDATE panda_well_hx SET coordinates = '{"x": -284, "y": -218.5, "z": -194}' WHERE plate_id = 120 AND well_id = 'E6';
UPDATE panda_well_hx SET coordinates = '{"x": -284, "y": -232, "z": -194}' WHERE plate_id = 120 AND well_id = 'E7';
UPDATE panda_well_hx SET coordinates = '{"x": -284, "y": -245.5, "z": -194}' WHERE plate_id = 120 AND well_id = 'E8';

UPDATE panda_well_hx SET base_thickness = '0' WHERE plate_id = 120;
