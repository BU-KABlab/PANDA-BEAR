UPDATE panda_vials SET coordinates = '{"x": -17.1, "y": -0.9, "z": -182}' WHERE id = 1;
UPDATE panda_vials SET coordinates = '{"x": -17.1, "y": -33.9, "z": -182}' WHERE id = 2;
UPDATE panda_vials SET coordinates = '{"x": -17.1, "y": -66.9,"z": -182}' WHERE id = 3;
UPDATE panda_vials SET coordinates = '{"x": -17.1, "y": -99.9, "z": -182}' WHERE id = 4;
UPDATE panda_vials SET coordinates = '{"x": -17.1, "y": -132.9, "z": -182}' WHERE id = 5;
UPDATE panda_vials SET coordinates = '{"x": -17.1, "y": -165.9, "z": -182}', volume = '20000' WHERE id = 6;
UPDATE panda_vials SET coordinates = '{"x": -17.1, "y": -198.9, "z": -182}' WHERE id = 7;
UPDATE panda_vials SET coordinates = '{"x": -17.1, "y": -231.9, "z": -182}' WHERE id = 8;
UPDATE panda_vials SET coordinates = '{"x": -17.1, "y": -264.9, "z": -182}' WHERE id = 9;
UPDATE panda_vials SET coordinates = '{"x": -17.1, "y": -297.9, "z": -182}' WHERE id = 10;
UPDATE panda_vials SET coordinates = '{"x": -394, "y": -92, "z": -197.8}' WHERE id = 11;


UPDATE panda_well_hx SET base_thickness = '1.2' WHERE plate_id = 111;

UPDATE panda_vials SET name = 'pama_200', contents = '{"pama": 3000}', concentration = '200', volume = '3000' WHERE id = 1;
UPDATE panda_vials SET name = 'peo_70', contents = '{"peo_70": 3000}', concentration = '70', volume = '3000' WHERE id = 2;
UPDATE panda_vials SET contents = '{"water": 0}', volume = '1000' WHERE id = 8;
UPDATE panda_vials SET contents = '{"water": 0}', volume = '1000' WHERE id = 9;
UPDATE panda_vials SET volume = '15000' WHERE id = 4;
UPDATE panda_vials SET volume = '15000' WHERE id = 5;
UPDATE panda_vials SET volume = '3000' WHERE id = 2;


INSERT INTO panda_projects (id, project_name) VALUES ('400', 'solid_handling');




UPDATE panda_vials SET base_thickness = '1' WHERE id = 2;

UPDATE panda_tip_hx SET status = 'new' WHERE tip_id = 'A1';
UPDATE panda_tip_hx SET status = 'used' WHERE tip_id = 'A9';
UPDATE panda_tip_hx SET status = 'used' WHERE tip_id = 'A10';
UPDATE panda_tip_hx SET status = 'used' WHERE tip_id = 'A11';

UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 111 AND well_id = 'A1';
UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 111 AND well_id = 'A2';
UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 111 AND well_id = 'A3';
UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 111 AND well_id = 'A4';

UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 111 AND well_id = 'A5';
UPDATE panda_well_hx SET status = 'unuseable' WHERE plate_id = 111 AND well_id = 'A6';
UPDATE panda_well_hx SET status = 'unuseable' WHERE plate_id = 111 AND well_id = 'A7';
UPDATE panda_well_hx SET status = 'unuseable' WHERE plate_id = 111 AND well_id = 'A8';

UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 111 AND well_id = 'B1';
UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 111 AND well_id = 'B2';
UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 111 AND well_id = 'B3';
UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 111 AND well_id = 'B4';

UPDATE panda_well_hx SET status = 'unuseable' WHERE plate_id = 111 AND well_id = 'B5';
UPDATE panda_well_hx SET status = 'unuseable' WHERE plate_id = 111 AND well_id = 'B6';
UPDATE panda_well_hx SET status = 'unuseable' WHERE plate_id = 111 AND well_id = 'B7';
UPDATE panda_well_hx SET status = 'unuseable' WHERE plate_id = 111 AND well_id = 'B8';

UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 111 AND well_id = 'C1';
UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 111 AND well_id = 'C2';
UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 111 AND well_id = 'C3';
UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 111 AND well_id = 'C4';

UPDATE panda_well_hx SET status = 'unuseable' WHERE plate_id = 111 AND well_id = 'C5';
UPDATE panda_well_hx SET status = 'unuseable' WHERE plate_id = 111 AND well_id = 'C6';
UPDATE panda_well_hx SET status = 'unuseable' WHERE plate_id = 111 AND well_id = 'C7';
UPDATE panda_well_hx SET status = 'unuseable' WHERE plate_id = 111 AND well_id = 'C8';

UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 111 AND well_id = 'D1';
UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 111 AND well_id = 'D2';
UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 111 AND well_id = 'D3';
UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 111 AND well_id = 'D4';

UPDATE panda_well_hx SET status = 'unuseable' WHERE plate_id = 111 AND well_id = 'D5';
UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 120 AND well_id = 'D6';
UPDATE panda_well_hx SET status = 'unuseable' WHERE plate_id = 111 AND well_id = 'D7';
UPDATE panda_well_hx SET status = 'unuseable' WHERE plate_id = 111 AND well_id = 'D8';

UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 111 AND well_id = 'E1';
UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 111 AND well_id = 'E2';
UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 111 AND well_id = 'E3';
UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 111 AND well_id = 'E4';

UPDATE panda_well_hx SET status = 'unuseable' WHERE plate_id = 111 AND well_id = 'E5';
UPDATE panda_well_hx SET status = 'unuseable' WHERE plate_id = 111 AND well_id = 'E6';
UPDATE panda_well_hx SET status = 'unuseable' WHERE plate_id = 111 AND well_id = 'E7';
UPDATE panda_well_hx SET status = 'unuseable' WHERE plate_id = 111 AND well_id = 'E8';

UPDATE panda_well_hx SET coordinates = '{"x": -282.6, "y": -249.4, "z": -194.3}' WHERE plate_id = 111 AND well_id = 'E7';


UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 111 AND well_id = 'A2';
UPDATE panda_well_hx SET status = 'new', contents = '{}', volume = '0' WHERE plate_id = 111 AND well_id = 'B7';
UPDATE panda_wellplates SET echem_height = '-187' WHERE id = 111;

UPDATE panda_tip_hx SET status = 'new' WHERE rack_id = 1;

UPDATE panda_tip_hx SET drop_coordinates = '{"x":-113.1,"y":-6.3,"z":-188.8}' WHERE rack_id = 1;

UPDATE panda_tip_hx SET pickup_height = '-189.4' WHERE rack_id = 1;
UPDATE panda_tip_hx SET status = 'discarded' WHERE rack_id = 1 AND tip_id = 'A12';
UPDATE panda_tip_hx SET status = 'discarded' WHERE rack_id = 1 AND tip_id = 'B12';

UPDATE panda_tip_hx SET pickup_height = '-189.2' WHERE rack_id = 1;

UPDATE panda_tip_hx SET status = 'new' WHERE rack_id = 1 AND tip_id = 'A1';
UPDATE panda_tip_hx SET status = 'new' WHERE rack_id = 1 AND tip_id = 'A2';
UPDATE panda_tip_hx SET status = 'new' WHERE rack_id = 1 AND tip_id = 'A3';
UPDATE panda_tip_hx SET status = 'new' WHERE rack_id = 1 AND tip_id = 'A4';
UPDATE panda_tip_hx SET status = 'new' WHERE rack_id = 1 AND tip_id = 'A5';
UPDATE panda_tip_hx SET status = 'new' WHERE rack_id = 1 AND tip_id = 'A6';
UPDATE panda_tip_hx SET status = 'new' WHERE rack_id = 1 AND tip_id = 'A7';
UPDATE panda_tip_hx SET status = 'new', pickup_height='-189' WHERE rack_id = 1 AND tip_id = 'B10';



DELETE FROM panda_pipette WHERE id = 1;

UPDATE panda_vials SET dead_volume = '1000' WHERE category = 0;
UPDATE panda_vials SET contents = '{"acn": 19000}', volume = '19000' WHERE id = 4;
UPDATE panda_vials SET contents = '{"ipa": 19000}', volume = '19000' WHERE id = 5;
UPDATE panda_vials SET contents = '{"waste": 0}', volume = '1000' WHERE id = 7;
UPDATE panda_vials SET contents = '{"waste": 0}', volume = '1000' WHERE id = 8;
UPDATE panda_vials SET contents = '{"waste": 0}', volume = '1000' WHERE id = 9;

UPDATE panda_well_hx SET coordinates = '{"x": -227.6, "y": -154.4, "z": -194.3}' WHERE plate_id = 111 AND well_id = 'A1';
UPDATE panda_well_hx SET coordinates = '{"x": -227.6, "y": -168.1, "z": -194.3}' WHERE plate_id = 111 AND well_id = 'A2';
UPDATE panda_well_hx SET coordinates = '{"x": -227.6, "y": -181.8, "z": -194.3}' WHERE plate_id = 111 AND well_id = 'A3';
UPDATE panda_well_hx SET coordinates = '{"x": -227.6, "y": -195.5, "z": -194.3}' WHERE plate_id = 111 AND well_id = 'A4';

UPDATE panda_well_hx SET coordinates = '{"x": -216.6, "y": -90.8, "z": -194.3}' WHERE plate_id = 111 AND well_id = 'A5';

UPDATE panda_well_hx SET coordinates = '{"x": -227.6, "y": -223.0, "z": -194.3}' WHERE plate_id = 111 AND well_id = 'A6';
UPDATE panda_well_hx SET coordinates = '{"x": -227.6, "y": -236.7, "z": -194.3}' WHERE plate_id = 111 AND well_id = 'A7';
UPDATE panda_well_hx SET coordinates = '{"x": -227.6, "y": -250.4, "z": -194.3}' WHERE plate_id = 111 AND well_id = 'A8';
UPDATE panda_well_hx SET coordinates = '{"x": -241.3, "y": -154.4, "z": -194.3}' WHERE plate_id = 111 AND well_id = 'B1';
UPDATE panda_well_hx SET coordinates = '{"x": -241.3, "y": -168.1, "z": -194.3}' WHERE plate_id = 111 AND well_id = 'B2';
UPDATE panda_well_hx SET coordinates = '{"x": -241.3, "y": -181.8, "z": -194.3}' WHERE plate_id = 111 AND well_id = 'B3';
UPDATE panda_well_hx SET coordinates = '{"x": -241.3, "y": -195.5, "z": -194.3}' WHERE plate_id = 111 AND well_id = 'B4';
UPDATE panda_well_hx SET coordinates = '{"x": -241.3, "y": -209.3, "z": -194.3}' WHERE plate_id = 111 AND well_id = 'B5';
UPDATE panda_well_hx SET coordinates = '{"x": -241.3, "y": -223.0, "z": -194.3}' WHERE plate_id = 111 AND well_id = 'B6';
UPDATE panda_well_hx SET coordinates = '{"x": -241.3, "y": -236.7, "z": -194.3}' WHERE plate_id = 111 AND well_id = 'B7';
UPDATE panda_well_hx SET coordinates = '{"x": -241.3, "y": -250.4, "z": -194.3}' WHERE plate_id = 111 AND well_id = 'B8';
UPDATE panda_well_hx SET coordinates = '{"x": -255.1, "y": -154.4, "z": -194.3}' WHERE plate_id = 111 AND well_id = 'C1';
UPDATE panda_well_hx SET coordinates = '{"x": -255.1, "y": -168.1, "z": -194.3}' WHERE plate_id = 111 AND well_id = 'C2';
UPDATE panda_well_hx SET coordinates = '{"x": -255.1, "y": -181.8, "z": -194.3}' WHERE plate_id = 111 AND well_id = 'C3';
UPDATE panda_well_hx SET coordinates = '{"x": -255.1, "y": -195.5, "z": -194.3}' WHERE plate_d = 111 AND well_id = 'C4';
UPDATE panda_well_hx SET coordinates = '{"x": -255.1, "y": -209.3, "z": -194.3}' WHERE plate_id = 111 AND well_id = 'C5';
UPDATE panda_well_hx SET coordinates = '{"x": -255.1, "y": -223.0, "z": -194.3}' WHERE plate_id = 111 AND well_id = 'C6';
UPDATE panda_well_hx SET coordinates = '{"x": -255.1, "y": -236.7, "z": -194.3}' WHERE plate_id = 111 AND well_id = 'C7';
UPDATE panda_well_hx SET coordinates = '{"x": -255.1, "y": -250.4, "z": -194.3}' WHERE plate_id = 111 AND well_id = 'C8';
UPDATE panda_well_hx SET coordinates = '{"x": -269.5, "y": -154.4, "z": -194.3}' WHERE plate_id = 111 AND well_id = 'D1';
UPDATE panda_well_hx SET coordinates = '{"x": -269.5, "y": -168.1, "z": -194.3}' WHERE plate_id = 111 AND well_id = 'D2';
UPDATE panda_well_hx SET coordinates = '{"x": -269.5, "y": -181.8, "z": -194.3}' WHERE plate_id = 111 AND well_id = 'D3';
UPDATE panda_well_hx SET coordinates = '{"x": -269.5, "y": -195.5, "z": -194.3}' WHERE plate_id = 111 AND well_id = 'D4';
UPDATE panda_well_hx SET coordinates = '{"x": -269.5, "y": -209.3, "z": -194.3}' WHERE plate_id = 111 AND well_id = 'D5';
UPDATE panda_well_hx SET coordinates = '{"x": -269.5, "y": -223.0, "z": -194.3}' WHERE plate_id = 111 AND well_id = 'D6';
UPDATE panda_well_hx SET coordinates = '{"x": -269.5, "y": -236.7, "z": -194.3}' WHERE plate_id = 111 AND well_id = 'D7';
UPDATE panda_well_hx SET coordinates = '{"x": -269.5, "y": -250.4, "z": -194.3}' WHERE plate_id = 111 AND well_id = 'D8';
UPDATE panda_well_hx SET coordinates = '{"x": -283.6, "y": -154.4, "z": -194.3}' WHERE plate_id = 111 AND well_id = 'E1';
UPDATE panda_well_hx SET coordinates = '{"x": -283.6, "y": -168.1, "z": -194.3}' WHERE plate_id = 111 AND well_id = 'E2';
UPDATE panda_well_hx SET coordinates = '{"x": -283.6, "y": -181.8, "z": -194.3}' WHERE plate_id = 111 AND well_id = 'E3';
UPDATE panda_well_hx SET coordinates = '{"x": -283.6, "y": -195.5, "z": -194.3}' WHERE plate_id = 111 AND well_id = 'E4';
UPDATE panda_well_hx SET coordinates = '{"x": -283.6, "y": -209.3, "z": -194.3}' WHERE plate_id = 111 AND well_id = 'E5';
UPDATE panda_well_hx SET coordinates = '{"x": -283.6, "y": -223.0, "z": -194.3}' WHERE plate_id = 111 AND well_id = 'E6';
UPDATE panda_well_hx SET coordinates = '{"x": -283.6, "y": -236.7, "z": -194.3}' WHERE plate_id = 111 AND well_id = 'E7';
UPDATE panda_well_hx SET coordinates = '{"x": -283.6, "y": -250.4, "z": -194.3}' WHERE plate_id = 111 AND well_id = 'E8';


UPDATE panda_well_hx SET base_thickness = '1.2' WHERE plate_id = 111;



UPDATE panda_vials SET name = 'pama_200', contents = '{"pama_200": 5500}', dead_volume='0', concentration='200', contamination='0', volume = '5500' WHERE id = 1;
UPDATE panda_vials SET name = 'peo_70', contents = '{"peo_70": 5000}', dead_volume='0', concentration='70', contamination='0', volume = '5000' WHERE id = 2;
UPDATE panda_vials SET name = 'electrolyte', contents = '{"electrolyte": 15000}', dead_volume='0', contamination='0', volume = '15000' WHERE id = 3;
UPDATE panda_vials SET name = 'dmf', contents = '{"dmf": 18000}', dead_volume='0', contamination='0', volume = '18000' WHERE id = 4;
UPDATE panda_vials SET name = 'acn', contents = '{"acn": 18000}', dead_volume='0', contamination='0', volume = '18000' WHERE id = 5;
UPDATE panda_vials SET name = 'ipa', contents = '{"ipa": 18000}', dead_volume='0', contamination='0', volume = '18000' WHERE id = 6;
UPDATE panda_vials SET name = 'water', category = '0', position = 's7', contents = '{"water": 18000}', dead_volume='0', contamination='0', volume = '18000', capacity='20000' WHERE id = 7;
UPDATE panda_vials SET name = 'waste', contents = '{"water": 500}', dead_volume='0', contamination='0', volume = '500', capacity='20000' WHERE id = 8;
UPDATE panda_vials SET name = 'waste', contents = '{"water": 500}', dead_volume='0', contamination='0', volume = '500', capacity='20000' WHERE id = 9;



UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 111 AND well_id = 'C5';
UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 111 AND well_id = 'C6';
UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 111 AND well_id = 'C7';
UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 111 AND well_id = 'C8';
UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 111 AND well_id = 'D1';
UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 111 AND well_id = 'D2';

UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 111 AND well_id = 'D3';
UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 111 AND well_id = 'D4';
UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 111 AND well_id = 'D5';
UPDATE panda_well_hx SET status = 'new' WHERE plate_id = 111 AND well_id = 'D6';




INSERT INTO panda_wellplate_types (id, substrate, gasket, count, shape, radius_mm, x_spacing, gasket_height_mm, max_liquid_height_mm, capacity_ul, rows, cols, y_spacing, gasket_length_mm, gasket_width_mm, x_offset, y_offset, base_thickness) VALUES ('');
