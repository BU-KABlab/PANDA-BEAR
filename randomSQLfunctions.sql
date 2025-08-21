UPDATE panda_vials SET coordinates = '{"x": -17.1, "y": -0.9, "z": -182}' WHERE id = 1;
UPDATE panda_vials SET coordinates = '{"x": -17.1, "y": -33.9, "z": -182}' WHERE id = 2;
UPDATE panda_vials SET coordinates = '{"x": -17.1, "y": -66.9, "z": -182}' WHERE id = 3;
UPDATE panda_vials SET coordinates = '{"x": -17.1, "y": -99.9, "z": -182}' WHERE id = 4;
UPDATE panda_vials SET coordinates = '{"x": -17.1, "y": -132.9, "z": -182}' WHERE id = 5;
UPDATE panda_vials SET coordinates = '{"x": -17.1, "y": -165.9, "z": -182}', volume = '20000' WHERE id = 6;
UPDATE panda_vials SET coordinates = '{"x": -17.1, "y": -198.9, "z": -182}' WHERE id = 7;
UPDATE panda_vials SET coordinates = '{"x": -17.1, "y": -231.9, "z": -182}' WHERE id = 8;
UPDATE panda_vials SET coordinates = '{"x": -17.1, "y": -264.9, "z": -182}' WHERE id = 9;
UPDATE panda_vials SET coordinates = '{"x": -17.1, "y": -297.9, "z": -182}' WHERE id = 10;
UPDATE panda_vials SET coordinates = '{"x": -394, "y": -92, "z": -197.8}' WHERE id = 11;


UPDATE panda_well_hx SET base_thickness = '1.5' WHERE plate_id = 120;

UPDATE panda_vials SET capacity = '13999.9' WHERE id = 8;

UPDATE panda_tip_hx SET status = 'new' WHERE tip_id = 'A1';
UPDATE panda_tip_hx SET status = 'new' WHERE tip_id = 'A2';

UPDATE panda_well_hx SET status = 'error' WHERE plate_id = 120 AND well_id = 'A1';
UPDATE panda_well_hx SET status = 'error' WHERE plate_id = 120 AND well_id = 'A2';
UPDATE panda_well_hx SET status = 'error' WHERE plate_id = 120 AND well_id = 'A3';
UPDATE panda_well_hx SET status = 'error' WHERE plate_id = 120 AND well_id = 'A4';

UPDATE panda_well_hx SET status = 'complete' WHERE plate_id = 120 AND well_id = 'A5';
UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 120 AND well_id = 'A6';
UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 120 AND well_id = 'A7';
UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 120 AND well_id = 'A8';

UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 120 AND well_id = 'B1';
UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 120 AND well_id = 'B2';
UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 120 AND well_id = 'B3';
UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 120 AND well_id = 'B4';
UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 120 AND well_id = 'B5';
UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 120 AND well_id = 'B6';
UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 120 AND well_id = 'B7';
UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 120 AND well_id = 'B8';
UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 120 AND well_id = 'C1';
UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 120 AND well_id = 'C2';
UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 120 AND well_id = 'C3';
UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 120 AND well_id = 'C4';
UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 120 AND well_id = 'C5';



UPDATE panda_well_hx SET status = 'complete' WHERE plate_id = 120 AND well_id = 'B7';


UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 120 AND well_id = 'A2';
UPDATE panda_well_hx SET status = 'new', contents = '{}', volume = '0' WHERE plate_id = 120 AND well_id = 'B7';
UPDATE panda_wellplates SET echem_height = '-187' WHERE id = 120;

UPDATE panda_tip_hx SET status = 'new' WHERE rack_id = 1;

DELETE FROM panda_pipette WHERE id = 1;

UPDATE panda_vials SET dead_volume = '1000' WHERE category = 0;
UPDATE panda_vials SET contents = '{"acn": 19000}', volume = '19000' WHERE id = 4;
UPDATE panda_vials SET contents = '{"ipa": 19000}', volume = '19000' WHERE id = 5;
UPDATE panda_vials SET contents = '{"waste": 0}', volume = '1000' WHERE id = 7;

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
