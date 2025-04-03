--
-- File generated with SQLiteStudio v3.4.4 on Mon Nov 25 21:37:43 2024
--
-- Text encoding used: System
--
PRAGMA foreign_keys = off;
BEGIN TRANSACTION;

-- Table: panda_experiment_parameters
DROP TABLE IF EXISTS panda_experiment_parameters;

CREATE TABLE IF NOT EXISTS panda_experiment_parameters (
    id              INTEGER NOT NULL
                            PRIMARY KEY AUTOINCREMENT,
    experiment_id   INTEGER,
    parameter_name  TEXT,
    parameter_value TEXT,
    created         TEXT    DEFAULT (CURRENT_TIMESTAMP) 
                            NOT NULL ON CONFLICT REPLACE,
    updated         TEXT    DEFAULT (CURRENT_TIMESTAMP) 
                            NOT NULL ON CONFLICT REPLACE
);


-- Table: panda_experiment_results
DROP TABLE IF EXISTS panda_experiment_results;

CREATE TABLE IF NOT EXISTS panda_experiment_results (
    id            INTEGER PRIMARY KEY,
    experiment_id INTEGER,
    result_type   TEXT,
    result_value  TEXT,
    created       TEXT    DEFAULT (CURRENT_TIMESTAMP),
    updated       TEXT    DEFAULT (CURRENT_TIMESTAMP),
    context       TEXT
);


-- Table: panda_experiments
DROP TABLE IF EXISTS panda_experiments;

CREATE TABLE IF NOT EXISTS panda_experiments (
    experiment_id       BIGINT  PRIMARY KEY,
    project_id          INTEGER,
    project_campaign_id INTEGER,
    well_type           INTEGER,
    protocol_id         INTEGER,
    pin                 TEXT,
    experiment_type     INTEGER,
    jira_issue_key      TEXT,
    priority            INTEGER DEFAULT 0,
    process_type        INTEGER DEFAULT 0,
    filename            TEXT    DEFAULT NULL,
    created             TEXT    DEFAULT (CURRENT_TIMESTAMP),
    updated             TEXT    DEFAULT (CURRENT_TIMESTAMP),
    needs_analysis      INTEGER DEFAULT (0),
    analysis_id         INTEGER
);


-- Table: panda_generators
DROP TABLE IF EXISTS panda_generators;

CREATE TABLE IF NOT EXISTS panda_generators (
    id          INTEGER NOT NULL
                        PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER,
    protocol_id INTEGER,
    name        TEXT,
    filepath    TEXT
);

INSERT INTO panda_generators (id, project_id, protocol_id, name, filepath) VALUES (15, '', '', 'system_test.py', 'system_test.py');

-- Table: panda_labware
DROP TABLE IF EXISTS panda_labware;

CREATE TABLE IF NOT EXISTS panda_labware (
    id              INTEGER PRIMARY KEY ASC ON CONFLICT ROLLBACK AUTOINCREMENT,
    name            TEXT    NOT NULL
                            CONSTRAINT [Unique labware names] UNIQUE ON CONFLICT ROLLBACK,
    count           INTEGER NOT NULL,
    max_volume_ul,
    shape           REAL    NOT NULL,
    length_mm       REAL    NOT NULL,
    width_mm        REAL    NOT NULL,
    height_mm       REAL    NOT NULL,
    depth_mm        REAL    NOT NULL,
    total_length_mm REAL    NOT NULL,
    diameter        REAL    NOT NULL,
    x_size_mm       REAL,
    y_size_mm       REAL    NOT NULL,
    x_spacing_mm    REAL    NOT NULL,
    y_spacing_mm    REAL    NOT NULL,
    x_offset_mm     REAL    NOT NULL,
    y_offset_mm     REAL    NOT NULL
);


-- Table: panda_ml_pedot_best_test_points
DROP TABLE IF EXISTS panda_ml_pedot_best_test_points;

CREATE TABLE IF NOT EXISTS panda_ml_pedot_best_test_points (
    model_id                 INT          NOT NULL
                                          PRIMARY KEY,
    experiment_id            INT          UNIQUE,
    best_test_point_scalar   TEXT,
    best_test_point_original TEXT,
    best_test_point          TEXT,
    v_dep                    REAL (18, 8),
    t_dep                    REAL (18, 8),
    edot_concentration       REAL (18, 8),
    predicted_response       REAL (18, 8),
    standard_deviation       REAL (18, 8),
    models_current_rmse      REAL (18, 8) 
);


-- Table: panda_pipette
DROP TABLE IF EXISTS panda_pipette;

CREATE TABLE IF NOT EXISTS panda_pipette (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    capacity_ul REAL    NOT NULL,
    capacity_ml REAL    NOT NULL,
    volume_ul   REAL    NOT NULL,
    volume_ml   REAL    NOT NULL,
    contents    TEXT,
    updated     TEXT    DEFAULT (CURRENT_TIMESTAMP),
    active      INTEGER,
    uses        INTEGER DEFAULT (0) 
);

INSERT INTO panda_pipette (id, capacity_ul, capacity_ml, volume_ul, volume_ml, contents, updated, active, uses) VALUES (1, 200.0, 0.2, 0.0, 0.0, '{}', '2024-11-26 02:28:12.196', 1, 0);

-- Table: panda_pipette_log
DROP TABLE IF EXISTS panda_pipette_log;

CREATE TABLE IF NOT EXISTS panda_pipette_log (
    id         INTEGER PRIMARY KEY,
    pipette_id INTEGER,
    volume_ul  REAL    NOT NULL,
    volume_ml  REAL    NOT NULL,
    updated    TEXT    DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (
        pipette_id
    )
    REFERENCES panda_pipette (id) 
);

INSERT INTO panda_pipette_log (id, pipette_id, volume_ul, volume_ml, updated) VALUES (1, 1, 0.0, 0.0, '2024-11-26 02:28:12.196');

-- Table: panda_plate_types
DROP TABLE IF EXISTS panda_plate_types;

CREATE TABLE IF NOT EXISTS panda_plate_types (
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
    y_offset             REAL
);

INSERT INTO panda_plate_types (id, substrate, gasket, count, shape, radius_mm, x_spacing, gasket_height_mm, max_liquid_height_mm, capacity_ul, rows, cols, y_spacing, gasket_length_mm, gasket_width_mm, x_offset, y_offset) VALUES (1, 'gold', 'grace bio-labs', 96, 'square', 4.0, 9.0, 7.0, 6.0, 300.0, 'ABCDEFGH', 12, 9.0, 110.0, 74.0, 10.5, 10.5);
INSERT INTO panda_plate_types (id, substrate, gasket, count, shape, radius_mm, x_spacing, gasket_height_mm, max_liquid_height_mm, capacity_ul, rows, cols, y_spacing, gasket_length_mm, gasket_width_mm, x_offset, y_offset) VALUES (2, 'ito', 'grace bio-labs', 96, 'square', 4.0, 9.0, 7.0, 6.0, 300.0, 'ABCDEFGH', 12, 9.0, 110.0, 74.0, 10.5, 10.5);
INSERT INTO panda_plate_types (id, substrate, gasket, count, shape, radius_mm, x_spacing, gasket_height_mm, max_liquid_height_mm, capacity_ul, rows, cols, y_spacing, gasket_length_mm, gasket_width_mm, x_offset, y_offset) VALUES (3, 'gold', 'pdms', 96, 'circular', 3.25, 8.9, 6.0, 4.5, 150.0, 'ABCDEFGH', 12, 8.9, 110.0, 74.0, 10.5, 10.5);
INSERT INTO panda_plate_types (id, substrate, gasket, count, shape, radius_mm, x_spacing, gasket_height_mm, max_liquid_height_mm, capacity_ul, rows, cols, y_spacing, gasket_length_mm, gasket_width_mm, x_offset, y_offset) VALUES (4, 'ito', 'pdms', 96, 'circular', 3.25, 9.0, 6.0, 4.5, 150.0, 'ABCDEFGH', 12, 9.0, 110.0, 74.0, 5.5, 5.5);
INSERT INTO panda_plate_types (id, substrate, gasket, count, shape, radius_mm, x_spacing, gasket_height_mm, max_liquid_height_mm, capacity_ul, rows, cols, y_spacing, gasket_length_mm, gasket_width_mm, x_offset, y_offset) VALUES (5, 'plastic', 'standard', 96, 'circular', 3.48, 9.0, 10.9, 8.5, 500.0, 'ABCDEFGH', 12, 9.0, 110.0, 74.0, 10.5, 10.5);
INSERT INTO panda_plate_types (id, substrate, gasket, count, shape, radius_mm, x_spacing, gasket_height_mm, max_liquid_height_mm, capacity_ul, rows, cols, y_spacing, gasket_length_mm, gasket_width_mm, x_offset, y_offset) VALUES (6, 'pipette tip box', 'standard', 96, 'circular', 3.48, 9.0, 45.0, 8.5, 300000.0, 'ABCDEFGH', 12, 9.0, 110.0, 74.0, 10.5, 10.5);
INSERT INTO panda_plate_types (id, substrate, gasket, count, shape, radius_mm, x_spacing, gasket_height_mm, max_liquid_height_mm, capacity_ul, rows, cols, y_spacing, gasket_length_mm, gasket_width_mm, x_offset, y_offset) VALUES (7, 'gold', 'pdms', 50, 'circular', 5.0, 13.5, 6.0, 4.5, 350.0, 'ABCDE', 8, 14.0, 110.0, 74.0, 7.75, 9.0);

-- Table: panda_potentiostat_readouts
DROP TABLE IF EXISTS panda_potentiostat_readouts;

CREATE TABLE IF NOT EXISTS panda_potentiostat_readouts (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp      TEXT    NOT NULL,
    interface      TEXT    NOT NULL,
    technique      TEXT    NOT NULL,
    readout_values TEXT    NOT NULL,
    experiment_id  INTEGER NOT NULL,
    FOREIGN KEY (
        experiment_id
    )
    REFERENCES panda_experiments (experiment_id) 
);


-- Table: panda_potentiostat_techniques
DROP TABLE IF EXISTS panda_potentiostat_techniques;

CREATE TABLE IF NOT EXISTS panda_potentiostat_techniques (
    id                    INTEGER PRIMARY KEY,
    technique             TEXT    NOT NULL,
    technique_description TEXT,
    technique_params      JSON,
    gamry_1010T           BOOLEAN NOT NULL,
    gamry_1010B           BOOLEAN NOT NULL,
    gamry_1010E           BOOLEAN NOT NULL
);


-- Table: panda_projects
DROP TABLE IF EXISTS panda_projects;

CREATE TABLE IF NOT EXISTS panda_projects (
    id           INTEGER PRIMARY KEY,
    project_name TEXT,
    added        TEXT    DEFAULT (CURRENT_TIMESTAMP) 
);

INSERT INTO panda_projects (id, project_name, added) VALUES (999, 'TEST', '2024-09-24 01:16:14');

-- Table: panda_protocols
DROP TABLE IF EXISTS panda_protocols;

CREATE TABLE IF NOT EXISTS panda_protocols (
    id       INTEGER PRIMARY KEY,
    project  INTEGER,
    name     TEXT,
    filepath TEXT
);

INSERT INTO panda_protocols (id, project, name, filepath) VALUES (18, '', 'system_test', 'system_test.py');
INSERT INTO panda_protocols (id, project, name, filepath) VALUES (19, '', 'PGMA-protocol-C2', 'PGMA-protocol-C2.py');
INSERT INTO panda_protocols (id, project, name, filepath) VALUES (20, '', 'system_test_v2', 'system_test_v2.py');

-- Table: panda_slack_tickets
DROP TABLE IF EXISTS panda_slack_tickets;

CREATE TABLE IF NOT EXISTS panda_slack_tickets (
    msg_id              TEXT    PRIMARY KEY
                                NOT NULL
                                UNIQUE,
    channel_id          TEXT    NOT NULL,
    message             TEXT    NOT NULL,
    response            INTEGER,
    timestamp           TEXT,
    addressed_timestamp TEXT,
    db_timestamp        TEXT    DEFAULT (CURRENT_TIMESTAMP) 
);


-- Table: panda_system_status
DROP TABLE IF EXISTS panda_system_status;

CREATE TABLE IF NOT EXISTS panda_system_status (
    id          INTEGER   PRIMARY KEY AUTOINCREMENT,
    status      TEXT      NOT NULL,
    comment     TEXT,
    status_time TIMESTAMP DEFAULT (CURRENT_TIMESTAMP),
    test_mode   BOOLEAN
);


-- Table: panda_system_versions
DROP TABLE IF EXISTS panda_system_versions;

CREATE TABLE IF NOT EXISTS panda_system_versions (
    id                  INTEGER PRIMARY KEY,
    mill                INTEGER NOT NULL,
    pump                TEXT    DEFAULT '00',
    potentiostat        TEXT    DEFAULT '00',
    reference_electrode TEXT    DEFAULT '00',
    working_electrode   TEXT    DEFAULT '00',
    wells               TEXT    DEFAULT '00',
    pipette_adapter     TEXT    DEFAULT '00',
    optics              TEXT    DEFAULT '00',
    scale               TEXT    DEFAULT '00',
    camera              TEXT    DEFAULT '00',
    lens                TEXT    DEFAULT '00',
    pin                 [TEXT ] GENERATED ALWAYS AS (CAST (mill AS TEXT) || ' ' || CAST (pump AS TEXT) || ' ' || CAST (potentiostat AS TEXT) || ' ' || CAST (reference_electrode AS TEXT) || ' ' || CAST (working_electrode AS TEXT) || ' ' || CAST (wells AS TEXT) || ' ' || CAST (pipette_adapter AS TEXT) || ' ' || CAST (optics AS TEXT) || ' ' || CAST (scale AS TEXT) || ' ' || CAST (camera AS TEXT) || ' ' || CAST (lens AS TEXT) ) STORED
);

INSERT INTO panda_system_versions (id, mill, pump, potentiostat, reference_electrode, working_electrode, wells, pipette_adapter, optics, scale, camera, lens) VALUES (1, 2, '01', '01', '01', '02', '04', '05', '00', '00', '01', '01');
INSERT INTO panda_system_versions (id, mill, pump, potentiostat, reference_electrode, working_electrode, wells, pipette_adapter, optics, scale, camera, lens) VALUES (2, 2, '01', '01', '02', '02', '07', '18', '00', '00', '01', '01');

-- Table: panda_user_projects
DROP TABLE IF EXISTS panda_user_projects;

CREATE TABLE IF NOT EXISTS panda_user_projects (
    user_id    INTEGER CONSTRAINT [User ID Constraint] REFERENCES panda_users (id) ON DELETE CASCADE,
    project_id INTEGER CONSTRAINT [Project ID Constraint] REFERENCES panda_projects (id),
    current    BOOLEAN DEFAULT (TRUE) 
                       NOT NULL ON CONFLICT REPLACE,
    timestamp  TEXT    DEFAULT (CURRENT_TIMESTAMP) 
                       NOT NULL ON CONFLICT REPLACE,
    PRIMARY KEY (
        user_id,
        project_id
    ),
    FOREIGN KEY (
        user_id
    )
    REFERENCES panda_users (id),
    FOREIGN KEY (
        project_id
    )
    REFERENCES panda_projects (id) 
);

INSERT INTO panda_user_projects (user_id, project_id, current, timestamp) VALUES (1, 999, 1, '2024-09-24 02:19:59');
INSERT INTO panda_user_projects (user_id, project_id, current, timestamp) VALUES (2, 999, 1, '2024-09-24 02:19:59');
INSERT INTO panda_user_projects (user_id, project_id, current, timestamp) VALUES (3, 999, 1, '2024-09-24 02:19:59');

-- Table: panda_users
DROP TABLE IF EXISTS panda_users;

CREATE TABLE IF NOT EXISTS panda_users (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    first      TEXT,
    last,
    [full]             GENERATED ALWAYS AS (first || ' ' || last) STORED,
    email      TEXT    UNIQUE,
    password   TEXT    CONSTRAINT [Unique Password] UNIQUE ON CONFLICT ABORT,
    active     BOOLEAN DEFAULT 0,
    created_at TEXT    DEFAULT CURRENT_TIMESTAMP,
    updated    TEXT    DEFAULT (CURRENT_TIMESTAMP),
    username   TEXT    CONSTRAINT Username UNIQUE ON CONFLICT ROLLBACK
);

INSERT INTO panda_users (id, first, last, email, password, active, created_at, updated, username) VALUES (1, 'john', 'doe', 'jdoe@email.com', 'pass123', 1, '2024-03-08 15:34:47', '2024-09-24 01:39:49', NULL);
INSERT INTO panda_users (id, first, last, email, password, active, created_at, updated, username) VALUES (2, 'Greg', 'Robben', 'grobben@bu.edu', 'grobben@bu.edu', 1, NULL, '2024-09-24 01:39:49', NULL);
INSERT INTO panda_users (id, first, last, email, password, active, created_at, updated, username) VALUES (3, 'Harley', 'Quinn', 'hjquinn@bu.edu', 'hjquinn@bu.edu', 1, NULL, '2024-09-24 01:39:49', NULL);

-- Table: panda_vial_hx
DROP TABLE IF EXISTS panda_vial_hx;

CREATE TABLE IF NOT EXISTS panda_vial_hx (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    position         TEXT,
    contents         TEXT,
    viscosity_cp     REAL,
    concentration    REAL,
    density          REAL,
    category         INTEGER,
    radius           INTEGER,
    height           INTEGER,
    depth            INTEGER,
    name             TEXT,
    volume           REAL,
    capacity         INTEGER,
    contamination    INTEGER,
    vial_coordinates TEXT,
    updated          TEXT    DEFAULT (CURRENT_TIMESTAMP),
    wall_thickness   REAL    DEFAULT (1.0) 
);

INSERT INTO panda_vial_hx (id, position, contents, viscosity_cp, concentration, density, category, radius, height, depth, name, volume, capacity, contamination, vial_coordinates, updated, wall_thickness) VALUES (7672, 'e1', 'None', 1.0, 1.0, 1.0, 0, 14, 57, -19.5194, 'none', 20000.0, 20000, 0, '{"x": -409, "y": -35, "z_top": 7.0, "z_bottom": -50}', '2024-11-26 02:37:22.445', 1.0);
INSERT INTO panda_vial_hx (id, position, contents, viscosity_cp, concentration, density, category, radius, height, depth, name, volume, capacity, contamination, vial_coordinates, updated, wall_thickness) VALUES (7673, 's0', 'edot', 1.0, 0.01, 1.0, 0, 14, 57, -47.4171, 'edot', 20000.0, 20000, 0, '{"x": -4, "y": -39, "z_top": -17.0, "z_bottom": -74}', '2024-11-26 02:37:22.446', 1.0);
INSERT INTO panda_vial_hx (id, position, contents, viscosity_cp, concentration, density, category, radius, height, depth, name, volume, capacity, contamination, vial_coordinates, updated, wall_thickness) VALUES (7674, 's1', 'liclo4', 1.0, 1.0, 1.0, 0, 14, 57, -50.0935, 'liclo4', 20000.0, 20000, 0, '{"x": -4, "y": -72, "z_top": -17.0, "z_bottom": -74}', '2024-11-26 02:37:22.447', 1.0);
INSERT INTO panda_vial_hx (id, position, contents, viscosity_cp, concentration, density, category, radius, height, depth, name, volume, capacity, contamination, vial_coordinates, updated, wall_thickness) VALUES (7675, 's2', 'rinse', 1.0, 1.0, 1.0, 0, 14, 57, -70.5044, 'rinse', 20000.0, 20000, 0, '{"x": -4, "y": -105, "z_top": -17.0, "z_bottom": -74}', '2024-11-26 02:37:22.448', 1.0);
INSERT INTO panda_vial_hx (id, position, contents, viscosity_cp, concentration, density, category, radius, height, depth, name, volume, capacity, contamination, vial_coordinates, updated, wall_thickness) VALUES (7676, 's3', 'rinse', 1.0, 1.0, 1.0, 0, 14, 57, -43.5194, 'rinse', 20000.0, 20000, 0, '{"x": -4, "y": -138, "z_top": -17.0, "z_bottom": -74}', '2024-11-26 02:37:22.448', 1.0);
INSERT INTO panda_vial_hx (id, position, contents, viscosity_cp, concentration, density, category, radius, height, depth, name, volume, capacity, contamination, vial_coordinates, updated, wall_thickness) VALUES (7677, 's4', 'None', 1.0, 1.0, 1.0, 0, 14, 57, -43.5194, 'none', 20000.0, 20000, 0, '{"x": -4, "y": -171, "z_top": -17.0, "z_bottom": -74}', '2024-11-26 02:37:22.449', 1.0);
INSERT INTO panda_vial_hx (id, position, contents, viscosity_cp, concentration, density, category, radius, height, depth, name, volume, capacity, contamination, vial_coordinates, updated, wall_thickness) VALUES (7678, 's5', 'None', 1.0, 1.0, 1.0, 0, 14, 57, -43.5194, 'none', 20000.0, 20000, 0, '{"x": -4, "y": -204, "z_top": -17.0, "z_bottom": -74}', '2024-11-26 02:37:22.450', 1.0);
INSERT INTO panda_vial_hx (id, position, contents, viscosity_cp, concentration, density, category, radius, height, depth, name, volume, capacity, contamination, vial_coordinates, updated, wall_thickness) VALUES (7679, 's6', 'None', 1.0, 1.0, 1.0, 0, 14, 57, -43.5194, 'none', 20000.0, 20000, 0, '{"x": -4, "y": -237, "z_top": -17.0, "z_bottom": -74}', '2024-11-26 02:37:22.450', 1.0);
INSERT INTO panda_vial_hx (id, position, contents, viscosity_cp, concentration, density, category, radius, height, depth, name, volume, capacity, contamination, vial_coordinates, updated, wall_thickness) VALUES (7680, 's7', 'None', 1.0, 1.0, 1.0, 0, 14, 57, -43.5194, 'none', 20000.0, 20000, 0, '{"x": -4, "y": -270, "z_top": -17.0, "z_bottom": -74}', '2024-11-26 02:37:22.451', 1.0);
INSERT INTO panda_vial_hx (id, position, contents, viscosity_cp, concentration, density, category, radius, height, depth, name, volume, capacity, contamination, vial_coordinates, updated, wall_thickness) VALUES (7681, 'w0', '{}', 0.0, NULL, 0.0, 1, 14, 57, -43.6176, 'waste', 1000.0, 20000, 0, '{"x": -50, "y": -7, "z_top": -17.0, "z_bottom": -74}', '2024-11-26 02:37:22.452', 1.0);
INSERT INTO panda_vial_hx (id, position, contents, viscosity_cp, concentration, density, category, radius, height, depth, name, volume, capacity, contamination, vial_coordinates, updated, wall_thickness) VALUES (7682, 'w1', '{}', 0.0, NULL, 0.0, 1, 14, 57, -68.0673, 'waste', 1000.0, 20000, 0, '{"x": -50, "y": -40, "z_top": -17.0, "z_bottom": -74}', '2024-11-26 02:37:22.453', 1.0);
INSERT INTO panda_vial_hx (id, position, contents, viscosity_cp, concentration, density, category, radius, height, depth, name, volume, capacity, contamination, vial_coordinates, updated, wall_thickness) VALUES (7683, 'w2', '{}', 0.0, NULL, 0.0, 1, 14, 57, -73, 'waste', 1000.0, 20000, 0, '{"x": -50, "y": -73, "z_top": -17.0, "z_bottom": -74}', '2024-11-26 02:37:22.454', 1.0);
INSERT INTO panda_vial_hx (id, position, contents, viscosity_cp, concentration, density, category, radius, height, depth, name, volume, capacity, contamination, vial_coordinates, updated, wall_thickness) VALUES (7684, 'w3', '{}', 0.0, NULL, 0.0, 1, 14, 57, -73, 'waste', 1000.0, 20000, 0, '{"x": -50, "y": -106, "z_top": -17.0, "z_bottom": -74}', '2024-11-26 02:37:22.455', 1.0);
INSERT INTO panda_vial_hx (id, position, contents, viscosity_cp, concentration, density, category, radius, height, depth, name, volume, capacity, contamination, vial_coordinates, updated, wall_thickness) VALUES (7685, 'w4', '{}', 0.0, NULL, 0.0, 1, 14, 57, -73, 'waste', 1000.0, 20000, 0, '{"x": -50, "y": -139, "z_top": -17.0, "z_bottom": -74}', '2024-11-26 02:37:22.455', 1.0);
INSERT INTO panda_vial_hx (id, position, contents, viscosity_cp, concentration, density, category, radius, height, depth, name, volume, capacity, contamination, vial_coordinates, updated, wall_thickness) VALUES (7686, 'w5', '{}', 0.0, NULL, 0.0, 1, 14, 57, -73, 'waste', 1000.0, 20000, 0, '{"x": -50, "y": -172, "z_top": -17.0, "z_bottom": -74}', '2024-11-26 02:37:22.456', 1.0);
INSERT INTO panda_vial_hx (id, position, contents, viscosity_cp, concentration, density, category, radius, height, depth, name, volume, capacity, contamination, vial_coordinates, updated, wall_thickness) VALUES (7687, 'w6', '{}', 0.0, NULL, 0.0, 1, 14, 57, -73, 'waste', 1000.0, 20000, 0, '{"x": -50, "y": -205, "z_top": -17.0, "z_bottom": -74}', '2024-11-26 02:37:22.457', 1.0);
INSERT INTO panda_vial_hx (id, position, contents, viscosity_cp, concentration, density, category, radius, height, depth, name, volume, capacity, contamination, vial_coordinates, updated, wall_thickness) VALUES (7688, 'w7', '{}', 0.0, NULL, 0.0, 1, 14, 57, -73, 'waste', 1000.0, 20000, 0, '{"x": -50, "y": -238, "z_top": -17.0, "z_bottom": -74}', '2024-11-26 02:37:22.457', 1.0);

-- Table: panda_well_hx
DROP TABLE IF EXISTS panda_well_hx;

CREATE TABLE IF NOT EXISTS panda_well_hx (
    plate_id      INTEGER,
    well_id       TEXT,
    experiment_id INTEGER,
    project_id    INTEGER,
    status        TEXT,
    status_date   TEXT    DEFAULT (CURRENT_TIMESTAMP) 
                          NOT NULL ON CONFLICT REPLACE,
    contents      JSON,
    volume        REAL,
    coordinates   JSON,
    updated       TEXT    DEFAULT (CURRENT_TIMESTAMP) 
                          NOT NULL ON CONFLICT REPLACE,
    PRIMARY KEY (
        plate_id,
        well_id
    )
);


-- Table: panda_wellplates
DROP TABLE IF EXISTS panda_wellplates;

CREATE TABLE IF NOT EXISTS panda_wellplates (
    id           INTEGER NOT NULL
                         PRIMARY KEY,
    type_id      INTEGER,
    current      BOOLEAN DEFAULT 0,
    a1_x         NUMERIC CONSTRAINT [Defualt A1_X] DEFAULT ( -221.75),
    a1_y         NUMERIC CONSTRAINT [Defualt A1_Y] DEFAULT ( -78.5),
    orientation  INTEGER CONSTRAINT [DEFAULT ORIENTATION] DEFAULT (0),
    rows         INTEGER CONSTRAINT [DEFUALT ROWS] DEFAULT (13),
    cols         TEXT    CONSTRAINT [DEFAULT COLUMNS] DEFAULT ABCDEFGH,
    z_bottom     NUMERIC CONSTRAINT [DEFUALT Z-BOTTOM] DEFAULT ( -71.75),
    z_top        NUMERIC CONSTRAINT [DEFAULT Z-TOP] DEFAULT ( -66.0),
    echem_height NUMERIC CONSTRAINT [DEFAULT ECHEM HEIGHT] DEFAULT ( -70),
    image_height REAL    DEFAULT (0),
    FOREIGN KEY (
        type_id
    )
    REFERENCES panda_plate_types (id) 
);

INSERT INTO panda_wellplates (id, type_id, current, a1_x, a1_y, orientation, rows, cols, z_bottom, z_top, echem_height, image_height) VALUES (999, 4, 0, -222.5, -78, 0, 'ABCDEFGH', '12', -71, -65, -72.5, -50.0);

-- Index: idx_unique_active
DROP INDEX IF EXISTS idx_unique_active;

CREATE INDEX IF NOT EXISTS idx_unique_active ON panda_pipette (
    active
)
WHERE active = 1;


-- Index: idx_unique_current
DROP INDEX IF EXISTS idx_unique_current;

CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_current ON panda_wellplates (
    current
)
WHERE current = 1;


-- Index: idx_vials_position
DROP INDEX IF EXISTS idx_vials_position;

CREATE INDEX IF NOT EXISTS idx_vials_position ON panda_vial_hx (
    position
);


-- Index: idx_vials_updated
DROP INDEX IF EXISTS idx_vials_updated;

CREATE INDEX IF NOT EXISTS idx_vials_updated ON panda_vial_hx (
    updated
);


-- Index: msg_id_index
DROP INDEX IF EXISTS msg_id_index;

CREATE INDEX IF NOT EXISTS msg_id_index ON panda_slack_tickets (
    msg_id,
    timestamp DESC
);


-- Trigger: on_insert_timestamp
DROP TRIGGER IF EXISTS on_insert_timestamp;
CREATE TRIGGER IF NOT EXISTS on_insert_timestamp
                       AFTER INSERT
                          ON panda_vial_hx
                    FOR EACH ROW
BEGIN
    UPDATE panda_vial_hx
       SET updated = strftime('%Y-%m-%d %H:%M:%f', 'now') 
     WHERE id = NEW.id;
END;


-- Trigger: update_log
DROP TRIGGER IF EXISTS update_log;
CREATE TRIGGER IF NOT EXISTS update_log
                       AFTER UPDATE OF id,
                                       capacity_ul,
                                       capacity_ml,
                                       volume_ul,
                                       volume_ml,
                                       contents
                          ON panda_pipette
                    FOR EACH ROW
BEGIN
    INSERT INTO panda_pipette_log (
                                      pipette_id,
                                      volume_ul,
                                      volume_ml,
                                      updated
                                  )
                                  VALUES (
                                      NEW.id,
                                      NEW.volume_ul,
                                      NEW.volume_ml,
                                      strftime('%Y-%m-%d %H:%M:%f', 'now') 
                                  );
END;


-- Trigger: update_timestamp_experiments
DROP TRIGGER IF EXISTS update_timestamp_experiments;
CREATE TRIGGER IF NOT EXISTS update_timestamp_experiments
                       AFTER UPDATE OF experiment_id,
                                       project_id,
                                       project_campaign_id,
                                       well_type,
                                       protocol_id,
                                       pin,
                                       experiment_type,
                                       jira_issue_key,
                                       priority,
                                       process_type,
                                       filename,
                                       created
                          ON panda_experiments
                    FOR EACH ROW
BEGIN
    UPDATE panda_experiments
       SET updated = datetime('now') 
     WHERE experiment_id = OLD.experiment_id;
END;


-- Trigger: update_timestamp_pipette
DROP TRIGGER IF EXISTS update_timestamp_pipette;
CREATE TRIGGER IF NOT EXISTS update_timestamp_pipette
                       AFTER UPDATE OF capacity_ul,
                                       capacity_ml,
                                       volume_ul,
                                       volume_ml,
                                       contents,
                                       active
                          ON panda_pipette
                    FOR EACH ROW
BEGIN
    UPDATE panda_pipette
       SET updated = strftime('%Y-%m-%d %H:%M:%f', 'now') 
     WHERE id = OLD.id;
END;


-- Trigger: update_timestamp_vials
DROP TRIGGER IF EXISTS update_timestamp_vials;
CREATE TRIGGER IF NOT EXISTS update_timestamp_vials
                       AFTER UPDATE OF position,
                                       contents,
                                       viscosity_cp,
                                       concentration,
                                       density,
                                       category,
                                       radius,
                                       height,
                                       depth,
                                       name,
                                       volume,
                                       capacity,
                                       contamination,
                                       vial_coordinates
                          ON panda_vial_hx
                    FOR EACH ROW
BEGIN
    UPDATE panda_vial_hx
       SET updated = strftime('%Y-%m-%d %H:%M:%f', 'now') 
     WHERE id = OLD.id;
END;


-- Trigger: update_timestamp_well_hx
DROP TRIGGER IF EXISTS update_timestamp_well_hx;
CREATE TRIGGER IF NOT EXISTS update_timestamp_well_hx
                       AFTER UPDATE OF plate_id,
                                       well_id,
                                       experiment_id,
                                       project_id,
                                       status,
                                       status_date,
                                       contents,
                                       volume,
                                       coordinates
                          ON panda_well_hx
                    FOR EACH ROW
BEGIN
    UPDATE panda_well_hx
       SET updated = datetime('now') 
     WHERE plate_id = OLD.plate_id AND 
           well_id = OLD.well_id;
END;


-- Trigger: update_timstamp_parameters
DROP TRIGGER IF EXISTS update_timstamp_parameters;
CREATE TRIGGER IF NOT EXISTS update_timstamp_parameters
                      BEFORE UPDATE OF experiment_id,
                                       parameter_name,
                                       parameter_value,
                                       created
                          ON panda_experiment_parameters
                    FOR EACH ROW
BEGIN
    UPDATE panda_experiment_parameters
       SET updated = datetime('now') 
     WHERE id = OLD.id;
END;


-- Trigger: update_timstamp_results
DROP TRIGGER IF EXISTS update_timstamp_results;
CREATE TRIGGER IF NOT EXISTS update_timstamp_results
                       AFTER UPDATE OF experiment_id,
                                       result_type,
                                       result_value,
                                       created,
                                       context
                          ON panda_experiment_results
                    FOR EACH ROW
BEGIN
    UPDATE panda_experiment_results
       SET updated = datetime('now') 
     WHERE id = OLD.id;
END;


-- Trigger: update_when_used
DROP TRIGGER IF EXISTS update_when_used;
CREATE TRIGGER IF NOT EXISTS update_when_used
                       AFTER UPDATE OF volume_ul
                          ON panda_pipette
                    FOR EACH ROW
BEGIN
    UPDATE panda_pipette
       SET uses = uses + 1
     WHERE id = OLD.id;
END;


-- View: panda_experiment_params
DROP VIEW IF EXISTS panda_experiment_params;
CREATE VIEW IF NOT EXISTS panda_experiment_params AS
    SELECT experiment_id,
           MAX(CASE WHEN parameter_name = 'experiment_name' THEN parameter_value END) AS experiment_name,
           MAX(CASE WHEN parameter_name = 'solutions' THEN parameter_value END) AS solutions,
           MAX(CASE WHEN parameter_name = 'solutions_corrected' THEN parameter_value END) AS solutions_corrected,
           MAX(CASE WHEN parameter_name = 'well_type_number' THEN parameter_value END) AS well_type_number,
           MAX(CASE WHEN parameter_name = 'pumping_rate' THEN parameter_value END) AS pumping_rate,
           MAX(CASE WHEN parameter_name = 'plate_id' THEN parameter_value END) AS plate_id,
           MAX(CASE WHEN parameter_name = 'override_well_selection' THEN parameter_value END) AS override_well_selection,
           MAX(CASE WHEN parameter_name = 'ocp' THEN parameter_value END) AS ocp,
           MAX(CASE WHEN parameter_name = 'ca' THEN parameter_value END) AS ca,
           MAX(CASE WHEN parameter_name = 'cv' THEN parameter_value END) AS cv,
           MAX(CASE WHEN parameter_name = 'baseline' THEN parameter_value END) AS baseline,
           MAX(CASE WHEN parameter_name = 'flush_sol_name' THEN parameter_value END) AS flush_sol_name,
           MAX(CASE WHEN parameter_name = 'flush_vol' THEN parameter_value END) AS flush_vol,
           MAX(CASE WHEN parameter_name = 'mix_count' THEN parameter_value END) AS mix_count,
           MAX(CASE WHEN parameter_name = 'mix_volume' THEN parameter_value END) AS mix_volume,
           MAX(CASE WHEN parameter_name = 'rinse_count' THEN parameter_value END) AS rinse_count,
           MAX(CASE WHEN parameter_name = 'rinse_vol' THEN parameter_value END) AS rinse_vol,
           MAX(CASE WHEN parameter_name = 'ca_sample_period' THEN parameter_value END) AS ca_sample_period,
           MAX(CASE WHEN parameter_name = 'ca_prestep_voltage' THEN parameter_value END) AS ca_prestep_voltage,
           MAX(CASE WHEN parameter_name = 'ca_prestep_time_delay' THEN parameter_value END) AS ca_prestep_time_delay,
           MAX(CASE WHEN parameter_name = 'ca_step_1_voltage' THEN parameter_value END) AS ca_step_1_voltage,
           MAX(CASE WHEN parameter_name = 'ca_step_1_time' THEN parameter_value END) AS ca_step_1_time,
           MAX(CASE WHEN parameter_name = 'ca_step_2_voltage' THEN parameter_value END) AS ca_step_2_voltage,
           MAX(CASE WHEN parameter_name = 'ca_step_2_time' THEN parameter_value END) AS ca_step_2_time,
           MAX(CASE WHEN parameter_name = 'ca_sample_rate' THEN parameter_value END) AS ca_sample_rate,
           MAX(CASE WHEN parameter_name = 'char_sol_name' THEN parameter_value END) AS char_sol_name,
           MAX(CASE WHEN parameter_name = 'char_vol' THEN parameter_value END) AS char_vol,
           MAX(CASE WHEN parameter_name = 'cv_sample_period' THEN parameter_value END) AS cv_sample_period,
           MAX(CASE WHEN parameter_name = 'cv_initial_voltage' THEN parameter_value END) AS cv_initial_voltage,
           MAX(CASE WHEN parameter_name = 'cv_first_anodic_peak' THEN parameter_value END) AS cv_first_anodic_peak,
           MAX(CASE WHEN parameter_name = 'cv_second_anodic_peak' THEN parameter_value END) AS cv_second_anodic_peak,
           MAX(CASE WHEN parameter_name = 'cv_final_voltage' THEN parameter_value END) AS cv_final_voltage,
           MAX(CASE WHEN parameter_name = 'cv_step_size' THEN parameter_value END) AS cv_step_size,
           MAX(CASE WHEN parameter_name = 'cv_cycle_count' THEN parameter_value END) AS cv_cycle_count,
           MAX(CASE WHEN parameter_name = 'cv_scan_rate_cycle_1' THEN parameter_value END) AS cv_scan_rate_cycle_1,
           MAX(CASE WHEN parameter_name = 'cv_scan_rate_cycle_2' THEN parameter_value END) AS cv_scan_rate_cycle_2,
           MAX(CASE WHEN parameter_name = 'cv_scan_rate_cycle_3' THEN parameter_value END) AS cv_scan_rate_cycle_3,
           MAX(CASE WHEN parameter_name = 'edot_concentration' THEN parameter_value END) AS edot_concentration
      FROM panda_experiment_parameters
     GROUP BY experiment_id
     ORDER BY experiment_id DESC;


-- View: panda_experiment_status
DROP VIEW IF EXISTS panda_experiment_status;
CREATE VIEW IF NOT EXISTS panda_experiment_status AS
    SELECT experiment_id,
           status
      FROM panda_well_hx
     WHERE experiment_id IS NOT NULL
     ORDER BY experiment_id ASC;


-- View: panda_new_wellplates
DROP VIEW IF EXISTS panda_new_wellplates;
CREATE VIEW IF NOT EXISTS panda_new_wellplates AS
    SELECT wh.plate_id,
           wp.type_id
      FROM panda_well_hx wh
           JOIN
           panda_wellplates wp ON wh.plate_id = wp.id
     WHERE wh.status = 'new'
     GROUP BY wh.plate_id
    HAVING COUNT( * ) = 96;


-- View: panda_pipette_status
DROP VIEW IF EXISTS panda_pipette_status;
CREATE VIEW IF NOT EXISTS panda_pipette_status AS
    SELECT *
      FROM panda_pipette-- WHERE updated = (SELECT MAX(updated) FROM pipette)
     WHERE id = (
                    SELECT MAX(id) 
                      FROM panda_pipette
                )
     LIMIT 1;


-- View: panda_queue
DROP VIEW IF EXISTS panda_queue;
CREATE VIEW IF NOT EXISTS panda_queue AS
    SELECT a.experiment_id,
           a.project_id,
           a.project_campaign_id,
           a.priority,
           a.process_type,
           a.filename,
           a.well_type AS [well type],
           c.well_id,
           c.status,
           c.status_date
      FROM panda_experiments AS a
           JOIN
           panda_wellplates AS b ON a.well_type = b.type_id
           JOIN
           panda_well_hx AS c ON a.experiment_id = c.experiment_id AND 
                                 c.status IN ('queued', 'waiting') 
     WHERE b.current = 1
     ORDER BY a.priority ASC,
              a.experiment_id ASC;


-- View: panda_vial_status
DROP VIEW IF EXISTS panda_vial_status;
CREATE VIEW IF NOT EXISTS panda_vial_status AS
    SELECT v1.*
      FROM panda_vial_hx v1
           LEFT JOIN
           panda_vial_hx v2 ON v1.position = v2.position AND 
                               (v1.updated < v2.updated OR 
                                (v1.updated = v2.updated AND 
                                 v1.id < v2.id) ) 
     WHERE v2.id IS NULL
     ORDER BY v1.position ASC;


-- View: panda_well_status
DROP VIEW IF EXISTS panda_well_status;
CREATE VIEW IF NOT EXISTS panda_well_status AS
    SELECT a.plate_id,
           b.type_id AS type_number,
           a.well_id,
           a.status,
           a.status_date,
           a.contents,
           a.experiment_id,
           a.project_id,
           a.volume,
           a.coordinates,
           c.capacity_ul AS capacity,
           c.gasket_height_mm AS height
      FROM panda_well_hx AS a
           JOIN
           panda_wellplates AS b ON a.plate_id = b.id
           JOIN
           panda_plate_types AS c ON b.type_id = c.id
     WHERE b.current = 1
     ORDER BY SUBSTRING(a.well_id, 1, 1),
              CAST (SUBSTRING(a.well_id, 2) AS UNSIGNED);


COMMIT TRANSACTION;
PRAGMA foreign_keys = on;
