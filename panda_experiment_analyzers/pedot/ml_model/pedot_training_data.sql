--
-- File generated with SQLiteStudio v3.4.4 on Sat Sep 21 17:51:45 2024
--
-- Text encoding used: System
--
PRAGMA foreign_keys = off;
BEGIN TRANSACTION;

-- Table: ml_pedot_training_data
DROP TABLE IF EXISTS ml_pedot_training_data;

CREATE TABLE IF NOT EXISTS ml_pedot_training_data (
    id            INTEGER         PRIMARY KEY,
    delta_e       DECIMAL (18, 8),
    voltage       DECIMAL (18, 8),
    time          DECIMAL (18, 8),
    bleach_cp     DECIMAL (18, 8),
    concentration DECIMAL (18, 8),
    experiment_id INTEGER
);

INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (1, 22.15005312, 1.26, 4.2, 1.282230512, 0.1, NULL);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (2, 21.13255215, 1.38, 6.6, 1.504366282, 0.1, NULL);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (3, 20.38620672, 1.22, 12.2, 1.646379092, 0.1, NULL);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (4, 19.8592108, 1.41, 2.6, 1.313409752, 0.1, NULL);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (5, 18.90243966, 1.02, 8.1, 0.980163746, 0.1, NULL);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (6, 17.02124653, 0.96, 56.9, 2.221613715, 0.1, NULL);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (7, 13.90102569, 1.07, 50.2, 3.036894115, 0.1, NULL);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (8, 13.84305638, 1.52, 15, 1.92057435, 0.1, NULL);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (9, 12.58864948, 1.15, 1.8, 1.049852181, 0.1, NULL);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (10, 11.24153556, 0.942949728, 36.37135724, 0.845229218, 0.03, NULL);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (11, 11.15469852, 1.56, 33.7, 1.554583905, 0.1, NULL);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (12, 10.63355321, 1.556551081, 80.30651025, 1.154786614, 0.03, NULL);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (13, 9.371989194, 1.1, 1.2, 0.948319326, 0.1, NULL);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (14, 9.189772968, 1.48, 27.6, 2.910642024, 0.1, NULL);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (15, 8.47760379, 1.34, 94.7, 1.742267966, 0.1, NULL);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (16, 7.836381489, 1.072247862, 9.942700152, 0.991847401, 0.03, NULL);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (17, 7.470526349, 1.22126257, 45.8954972, 0.802049226, 0.03, NULL);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (18, 7.103112719, 1.194614655, 59.60546757, 0.834122902, 0.03, NULL);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (19, 6.350163474, 1.399574718, 19.99647276, 0.978611305, 0.03, NULL);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (20, 6.229782591, 1.290493376, 27.55509538, 0.697819656, 0.03, NULL);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (21, 5.257736804, 1.54445486, 3.141003597, 1.125221966, 0.03, NULL);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (22, 5.024680061, 1.417941178, 11.79534411, 0.813517482, 0.03, NULL);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (23, 4.726981697, 1.103574943, 3.797092889, 0.843193347, 0.03, NULL);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (24, 4.717167251, 1.302078029, 16.80250948, 0.730234074, 0.03, NULL);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (25, 4.423638278, 1.040741426, 1.542247632, 0.634036306, 0.03, NULL);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (26, 3.468944527, 1.464067178, 1.973997251, 0.792607165, 0.03, NULL);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (27, 3.050363222, 1.476284328, 80.64333778, 0.725985493, 0.01, NULL);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (28, 3.035407012, 0.980088091, 1.152476253, 0.487954869, 0.03, NULL);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (29, 2.93930697, 0.83, 19.6, 0.678668388, 0.1, NULL);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (30, 2.247216232, 1.362921311, 50.50406742, 0.800550353, 0.01, NULL);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (31, 1.90915917, 1.120957751, 4.800255552, 0.598215629, 0.01, NULL);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (32, 1.719663108, 0.832403577, 20.65278532, 0.179248415, 0.01, NULL);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (33, 1.654847411, 1.096680145, 66.35487927, 0.702556801, 0.01, NULL);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (34, 1.645571514, 0.898103037, 7.539866894, 0.190768776, 0.01, NULL);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (35, 1.645340585, 0.866789927, 4.302646073, 0.13413755, 0.03, NULL);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (36, 1.549496238, 0.996982271, 28.19759552, 0.407900009, 0.01, NULL);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (37, 1.511556099, 1.50705351, 1.044500861, 0.557276732, 0.01, NULL);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (38, 1.481273952, 1.580441339, 1.630583861, 0.70797176, 0.01, NULL);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (39, 1.286666582, 1.155223307, 2.145634869, 0.489560031, 0.01, NULL);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (40, 1.257342906, 1.013504235, 2.832101146, 0.14512127, 0.01, NULL);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (41, 1.036072496, 1.2315587, 13.20309211, 0.538277624, 0.01, NULL);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (42, 1.013637043, 1.413812047, 15.28245176, 0.639750696, 0.01, NULL);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (43, 0.836020784, 0.912147792, 41.14075221, 0.208379828, 0.01, NULL);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (44, 0.672891551, 0.842818578, 5.874526581, 0.128212552, 0.03, NULL);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (45, 0.536995121, 1.309069321, 3.319612441, 0.642637406, 0.01, NULL);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (46, 0.524058943, 1.252344976, 6.501574726, 0.683000882, 0.01, NULL);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (47, 0, 0.9, 1.3, 0.376127951, 0.1, NULL);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (48, 0, 0.89, 4.9, 0.27695286, 0.1, NULL);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (49, 23.86323649285064, 1.305, 5.762, 1.11495061131424, 0.1, 10000875);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (50, 20.74746801417566, 1.307, 5.249, 0.09805428634392, 0.1, 10000876);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (51, 22.65553974, 1.308, 5.493, 8.976421266, 0.1, 10000877);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (52, 22.57453936, 1.305, 5.4, 0.00020348, 0.1, 10000878);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (53, 22.49837549, 1.307, 5.408, 0.000370084, 0.1, 10000879);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (54, 19.34670348, 1.718, 7.674, 0.0000147, 0.1, 10000880);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (55, 13.14720119, 1.722, 8.027, 0.80832719, 0.1, 10000881);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (56, 6.193329715, 1.757, 24.636, 0.0000509, 0.056, 10000882);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (57, 22.57241064, 1.228, 6.546, 0.000120195, 0.1, 10000883);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (58, 21.89733825, 1.218, 6.674, 0.000209901, 0.1, 10000884);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (59, 21.38175993, 1.218, 6.619, 0.000208387, 0.1, 10000885);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (60, 20.97105217, 1.226, 6.356, 0.000345661, 0.1, 10000886);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (61, 21.13854722, 1.239, 6.14, 0.000136273, 0.1, 10000887);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (62, 20.25071276, 1.253, 6, 0.0000421, 0.1, 10000888);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (63, 19.85975206, 1.259, 5.827, 0.0000926, 0.1, 10000889);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (64, 17.67858134, 1.267, 5.637, 0.000107888, 0.1, 10000890);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (65, 17.13360519, 1.273, 5.67, 0.0000682, 0.1, 10000891);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (66, 16.87181274, 1.277, 5.845, 0.000154147, 0.1, 10000892);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (67, 17.26693918, 1.614, 1.805, 0.00016617, 0.1, 10000893);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (68, 13.43540868, 1.602, 1.757, 0.000123146, 0.1, 10000894);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (69, 22.30174061, 1.305, 5.762, 0.740467284, 0.1, 10000895);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (70, 21.38193384, 1.305, 5.762, 0.000407186, 0.1, 10000896);
INSERT INTO ml_pedot_training_data (id, delta_e, voltage, time, bleach_cp, concentration, experiment_id) VALUES (71, 21.41036124, 1.305, 5.762, 0.000195648, 0.1, 10000897);

COMMIT TRANSACTION;
PRAGMA foreign_keys = on;
