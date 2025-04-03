SELECT p.experiment_id,
       p.ca_step_1_voltage AS dep_v,
       p.ca_step_1_time AS dep_t,
       p.edot_concentration AS concentration,
       MAX(CASE WHEN r.result_type = 'PEDOT_Predicted_Mean' THEN r.result_value END) AS predicted_delta_e,
       MAX(CASE WHEN r.result_type = 'PEDOT_Predicted_Uncertainty' THEN r.result_value END) AS predicted_standard_dev,
       MAX(CASE WHEN r.result_type = 'delta_e00' THEN r.result_value END) AS actual_delta_e,
       MAX(CASE WHEN r.result_type = 'BleachChargePassed' THEN r.result_value END) AS actual_q_bleach_charge_passed,
       MAX(CASE WHEN r.result_type = 'image' AND 
                     r.context = 'AfterDeposition' THEN r.result_value END) AS after_dep_img_file_path,
       MAX(CASE WHEN r.result_type = 'image' AND 
                     r.context = 'AfterBleaching' THEN r.result_value END) AS after_bleaching_img_file_path,
       MAX(CASE WHEN r.result_type = 'image' AND 
                     r.context = 'AfterColoring' THEN r.result_value END) AS after_coloring_img_file_path
  FROM experiment_params AS p
       JOIN
       experiment_results AS r ON p.experiment_id = r.experiment_id
 WHERE p.experiment_id BETWEEN 10000875 AND 10000894
 GROUP BY p.experiment_id,
          dep_v,
          dep_t,
          concentration;
