--
-- File generated with SQLiteStudio v3.4.4 on Thu Sep 26 18:46:25 2024
--
-- Text encoding used: System
--
PRAGMA foreign_keys = off;
BEGIN TRANSACTION;

-- Table: experiment_parameters
DROP TABLE IF EXISTS experiment_parameters;

CREATE TABLE IF NOT EXISTS experiment_parameters (
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


-- Table: experiment_results
DROP TABLE IF EXISTS experiment_results;

CREATE TABLE IF NOT EXISTS experiment_results (
    id            INTEGER PRIMARY KEY,
    experiment_id INTEGER,
    result_type   TEXT,
    result_value  TEXT,
    created       TEXT    DEFAULT (CURRENT_TIMESTAMP),
    updated       TEXT    DEFAULT (CURRENT_TIMESTAMP),
    context       TEXT
);


-- Table: experiments
DROP TABLE IF EXISTS experiments;

CREATE TABLE IF NOT EXISTS experiments (
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
    updated             TEXT    DEFAULT (CURRENT_TIMESTAMP) 
);


-- Table: generators
DROP TABLE IF EXISTS generators;

CREATE TABLE IF NOT EXISTS generators (
    id          INTEGER NOT NULL
                        PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER,
    protocol_id INTEGER,
    name        TEXT,
    filepath    TEXT
);

INSERT INTO generators (id, project_id, protocol_id, name, filepath) VALUES (15, '', '', 'system_test.py', 'system_test.py');
INSERT INTO generators (id, project_id, protocol_id, name, filepath) VALUES (17, '', '', 'PGMA-generator-C2.py', 'PGMA-generator-C2.py');
INSERT INTO generators (id, project_id, protocol_id, name, filepath) VALUES (18, '', '', 'PGMA-generator-C2-dry-run.py', 'PGMA-generator-C2-dry-run.py');

-- Table: mill_config
DROP TABLE IF EXISTS mill_config;

CREATE TABLE IF NOT EXISTS mill_config (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    config    JSON,
    timestamp TEXT    DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO mill_config (id, config, timestamp) VALUES (1, '{
    "instrument_offsets": {
      "electrode": {
        "x": 40.2,
        "y": 26.2,
        "z": 0
      },
      "pipette": {
        "x": -82.5,
        "y": -2.5,
        "z": 0
      },
      "lens": {
        "x": 0,
        "y": 0,
        "z": 0
      },
      "center": {
        "x": 0,
        "y": 0,
        "z": 0
      }
    },
    "working_volume": {
      "x": -415,
      "y": -300,
      "z": -80
    },
    "electrode_bath": {
      "x": -409.6,
      "y": -34.4,
      "z": -50
    },
    "safe_height_floor": -20,
    "settings": {
      "$0": 10,
      "$1": 255,
      "$2": 0,
      "$3": 0,
      "$4": 0,
      "$5": 0,
      "$6": 0,
      "$10": 3,
      "$11": 0.010,
      "$12": 0.002,
      "$13": 0,
      "$20": 0,
      "$21": 1,
      "$22": 1,
      "$23": 0,
      "$24": 150.000,
      "$25": 1000.000,
      "$26": 250,
      "$27": 3.000,
      "$30": 10000,
      "$31": 0,
      "$32": 0,
      "$100": 160.000,
      "$101": 160.000,
      "$102": 160.000,
      "$110": 2000.000,
      "$111": 2000.000,
      "$112": 2000.000,
      "$120": 300.000,
      "$121": 300.000,
      "$122": 300.000,
      "$130": 400.000,
      "$131": 300.000,
      "$132": 110.000
    }
}', '2024-07-21 00:41:23');
INSERT INTO mill_config (id, config, timestamp) VALUES (4, '{
    "instrument_offsets": {
      "electrode": {
        "x": 34.5,
        "y": 35.0,
        "z": 0
      },
      "pipette": {
        "x": -85.5,
        "y": -1,
        "z": -2
      },
      "lens": {
        "x": 0,
        "y": 0,
        "z": 0
      },
      "center": {
        "x": 0,
        "y": 0,
        "z": 0
      }
    },
    "working_volume": {
      "x": -415,
      "y": -300,
      "z": -80
    },
    "electrode_bath":{"x": -409, "y": -35, "z": -50},
    "safe_height_floor": -15,
    "settings": {
      "$0": 10,
      "$1": 255,
      "$2": 0,
      "$3": 0,
      "$4": 0,
      "$5": 0,
      "$6": 0,
      "$10": 3,
      "$11": 0.010,
      "$12": 0.002,
      "$13": 0,
      "$20": 0,
      "$21": 1,
      "$22": 1,
      "$23": 0,
      "$24": 150.000,
      "$25": 1000.000,
      "$26": 250,
      "$27": 3.000,
      "$30": 10000,
      "$31": 0,
      "$32": 0,
      "$100": 160.000,
      "$101": 160.000,
      "$102": 160.000,
      "$110": 2000.000,
      "$111": 2000.000,
      "$112": 2000.000,
      "$120": 300.000,
      "$121": 300.000,
      "$122": 300.000,
      "$130": 400.000,
      "$131": 300.000,
      "$132": 110.000
    }
}', '2024-09-11 22:26:21.072071');

-- Table: ml_pedot_best_test_points
DROP TABLE IF EXISTS ml_pedot_best_test_points;

CREATE TABLE IF NOT EXISTS ml_pedot_best_test_points (
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


-- Table: pipette
DROP TABLE IF EXISTS pipette;

CREATE TABLE IF NOT EXISTS pipette (
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

INSERT INTO pipette (id, capacity_ul, capacity_ml, volume_ul, volume_ml, contents, updated, active, uses) VALUES (1, 200.0, 0.2, 0.0, 0.0, '{}', '2024-09-26 17:23:20.516', 0, 1113);

-- Table: pipette_log
DROP TABLE IF EXISTS pipette_log;

CREATE TABLE IF NOT EXISTS pipette_log (
    id         INTEGER PRIMARY KEY,
    pipette_id INTEGER,
    volume_ul  REAL    NOT NULL,
    volume_ml  REAL    NOT NULL,
    updated    TEXT    DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (
        pipette_id
    )
    REFERENCES pipette (id) 
);


-- Table: plate_types
DROP TABLE IF EXISTS plate_types;

CREATE TABLE IF NOT EXISTS plate_types (
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

INSERT INTO plate_types (id, substrate, gasket, count, shape, radius_mm, x_spacing, gasket_height_mm, max_liquid_height_mm, capacity_ul, rows, cols, y_spacing, gasket_length_mm, gasket_width_mm, x_offset, y_offset) VALUES (1, 'gold', 'grace bio-labs', 96, 'square', 4.0, 9.0, 7.0, 6.0, 300.0, 'ABCDEFGH', 12, 9.0, 110.0, 74.0, 10.5, 10.5);
INSERT INTO plate_types (id, substrate, gasket, count, shape, radius_mm, x_spacing, gasket_height_mm, max_liquid_height_mm, capacity_ul, rows, cols, y_spacing, gasket_length_mm, gasket_width_mm, x_offset, y_offset) VALUES (2, 'ito', 'grace bio-labs', 96, 'square', 4.0, 9.0, 7.0, 6.0, 300.0, 'ABCDEFGH', 12, 9.0, 110.0, 74.0, 10.5, 10.5);
INSERT INTO plate_types (id, substrate, gasket, count, shape, radius_mm, x_spacing, gasket_height_mm, max_liquid_height_mm, capacity_ul, rows, cols, y_spacing, gasket_length_mm, gasket_width_mm, x_offset, y_offset) VALUES (3, 'gold', 'pdms', 96, 'circular', 3.25, 8.9, 6.0, 4.5, 150.0, 'ABCDEFGH', 12, 8.9, 110.0, 74.0, 10.5, 10.5);
INSERT INTO plate_types (id, substrate, gasket, count, shape, radius_mm, x_spacing, gasket_height_mm, max_liquid_height_mm, capacity_ul, rows, cols, y_spacing, gasket_length_mm, gasket_width_mm, x_offset, y_offset) VALUES (4, 'ito', 'pdms', 96, 'circular', 3.25, 9.0, 6.0, 4.5, 150.0, 'ABCDEFGH', 12, 9.0, 110.0, 74.0, 5.5, 5.5);
INSERT INTO plate_types (id, substrate, gasket, count, shape, radius_mm, x_spacing, gasket_height_mm, max_liquid_height_mm, capacity_ul, rows, cols, y_spacing, gasket_length_mm, gasket_width_mm, x_offset, y_offset) VALUES (5, 'plastic', 'standard', 96, 'circular', 3.48, 9.0, 10.9, 8.5, 500.0, 'ABCDEFGH', 12, 9.0, 110.0, 74.0, 10.5, 10.5);
INSERT INTO plate_types (id, substrate, gasket, count, shape, radius_mm, x_spacing, gasket_height_mm, max_liquid_height_mm, capacity_ul, rows, cols, y_spacing, gasket_length_mm, gasket_width_mm, x_offset, y_offset) VALUES (6, 'pipette tip box', 'standard', 96, 'circular', 3.48, 9.0, 45.0, 8.5, 300000.0, 'ABCDEFGH', 12, 9.0, 110.0, 74.0, 10.5, 10.5);
INSERT INTO plate_types (id, substrate, gasket, count, shape, radius_mm, x_spacing, gasket_height_mm, max_liquid_height_mm, capacity_ul, rows, cols, y_spacing, gasket_length_mm, gasket_width_mm, x_offset, y_offset) VALUES (7, 'gold', 'pdms', 50, 'circular', 5.0, 13.5, 6.0, 4.5, 350.0, 'ABCDE', 8, 14.0, 110.0, 74.0, 7.75, 9.0);

-- Table: projects
DROP TABLE IF EXISTS projects;

CREATE TABLE IF NOT EXISTS projects (
    id           INTEGER PRIMARY KEY,
    project_name TEXT,
    added        TEXT    DEFAULT (CURRENT_TIMESTAMP) 
);

INSERT INTO projects (id, project_name, added) VALUES (999, 'TEST', '2024-09-24 01:16:14');

-- Table: protocols
DROP TABLE IF EXISTS protocols;

CREATE TABLE IF NOT EXISTS protocols (
    id       INTEGER PRIMARY KEY,
    project  INTEGER,
    name     TEXT,
    filepath TEXT
);

INSERT INTO protocols (id, project, name, filepath) VALUES (18, '', 'system_test', 'system_test.py');

-- Table: slack_tickets
DROP TABLE IF EXISTS slack_tickets;

CREATE TABLE IF NOT EXISTS slack_tickets (
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


-- Table: system_status
DROP TABLE IF EXISTS system_status;

CREATE TABLE IF NOT EXISTS system_status (
    id          INTEGER   PRIMARY KEY AUTOINCREMENT,
    status      TEXT      NOT NULL,
    comment     TEXT,
    status_time TIMESTAMP DEFAULT (CURRENT_TIMESTAMP),
    test_mode   BOOLEAN
);


-- Table: system_versions
DROP TABLE IF EXISTS system_versions;

CREATE TABLE IF NOT EXISTS system_versions (
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

INSERT INTO system_versions (id, mill, pump, potentiostat, reference_electrode, working_electrode, wells, pipette_adapter, optics, scale, camera, lens) VALUES (1, 2, '01', '01', '01', '02', '04', '05', '00', '00', '01', '01');
INSERT INTO system_versions (id, mill, pump, potentiostat, reference_electrode, working_electrode, wells, pipette_adapter, optics, scale, camera, lens) VALUES (2, 2, '01', '01', '02', '02', '07', '18', '00', '00', '01', '01');

-- Table: user_projects
DROP TABLE IF EXISTS user_projects;

CREATE TABLE IF NOT EXISTS user_projects (
    user_id    INTEGER CONSTRAINT [User ID Constraint] REFERENCES users (id) ON DELETE CASCADE,
    project_id INTEGER CONSTRAINT [Project ID Constraint] REFERENCES projects (id),
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
    REFERENCES users (id),
    FOREIGN KEY (
        project_id
    )
    REFERENCES projects (id) 
);

INSERT INTO user_projects (user_id, project_id, current, timestamp) VALUES (1, 999, 1, '2024-09-24 02:19:59');
INSERT INTO user_projects (user_id, project_id, current, timestamp) VALUES (2, 999, 1, '2024-09-24 02:19:59');
INSERT INTO user_projects (user_id, project_id, current, timestamp) VALUES (3, 999, 1, '2024-09-24 02:19:59');

-- Table: users
DROP TABLE IF EXISTS users;

CREATE TABLE IF NOT EXISTS users (
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

INSERT INTO users (id, first, last, email, password, active, created_at, updated, username) VALUES (1, 'john', 'doe', 'jdoe@email.com', 'pass123', 1, '2024-03-08 15:34:47', '2024-09-24 01:39:49', NULL);
INSERT INTO users (id, first, last, email, password, active, created_at, updated, username) VALUES (2, 'Greg', 'Robben', 'grobben@bu.edu', 'grobben@bu.edu', 1, NULL, '2024-09-24 01:39:49', NULL);
INSERT INTO users (id, first, last, email, password, active, created_at, updated, username) VALUES (3, 'Harley', 'Quinn', 'hjquinn@bu.edu', 'hjquinn@bu.edu', 1, NULL, '2024-09-24 01:39:49', NULL);

-- Table: vials
DROP TABLE IF EXISTS vials;

CREATE TABLE IF NOT EXISTS vials (
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
    updated          TEXT    DEFAULT (CURRENT_TIMESTAMP) 
);

INSERT INTO vials (id, position, contents, viscosity_cp, concentration, density, category, radius, height, depth, name, volume, capacity, contamination, vial_coordinates, updated) VALUES (5094, 's0', 'water', 1.0, 1.0, 1.0, 0, 14, 57, -72.7519, 'water', 2000.0, 2000, 0, '{''x'': -4, ''y'': -39, ''z_top'': -17.0, ''z_bottom'': -74}', '2024-09-23 14:56:33.709');
INSERT INTO vials (id, position, contents, viscosity_cp, concentration, density, category, radius, height, depth, name, volume, capacity, contamination, vial_coordinates, updated) VALUES (5095, 's1', 'pgma-phenol', 1.0, 1.0, 1.0, 0, 14, 57, -43.5194, 'pgma-phenol', 20000.0, 20000, 0, '{''x'': -4, ''y'': -72, ''z_top'': -17.0, ''z_bottom'': -74}', '2024-09-23 14:56:34.527');
INSERT INTO vials (id, position, contents, viscosity_cp, concentration, density, category, radius, height, depth, name, volume, capacity, contamination, vial_coordinates, updated) VALUES (5096, 's2', 'fc', 1.0, 1.0, 1.0, 0, 14, 57, -43.5194, 'fc', 20000.0, 20000, 0, '{''x'': -4, ''y'': -105, ''z_top'': -17.0, ''z_bottom'': -74}', '2024-09-23 14:56:35.066');
INSERT INTO vials (id, position, contents, viscosity_cp, concentration, density, category, radius, height, depth, name, volume, capacity, contamination, vial_coordinates, updated) VALUES (5097, 's3', 'dmf-tbaprinse', 1.0, 1.0, 1.0, 0, 14, 57, -43.5194, 'dmf-tbaprinse', 20000.0, 20000, 0, '{''x'': -4, ''y'': -138, ''z_top'': -17.0, ''z_bottom'': -74}', '2024-09-23 14:56:35.652');
INSERT INTO vials (id, position, contents, viscosity_cp, concentration, density, category, radius, height, depth, name, volume, capacity, contamination, vial_coordinates, updated) VALUES (5098, 's4', 'dmfrinse', 1.0, 1.0, 1.0, 0, 14, 57, -43.5194, 'dmfrinse', 20000.0, 20000, 0, '{''x'': -4, ''y'': -171, ''z_top'': -17.0, ''z_bottom'': -74}', '2024-09-23 14:56:36.316');
INSERT INTO vials (id, position, contents, viscosity_cp, concentration, density, category, radius, height, depth, name, volume, capacity, contamination, vial_coordinates, updated) VALUES (5099, 's5', 'acnrinse', 1.0, 1.0, 1.0, 0, 14, 57, -43.5194, 'acnrinse', 20000.0, 20000, 0, '{''x'': -4, ''y'': -204, ''z_top'': -17.0, ''z_bottom'': -74}', '2024-09-23 14:56:39.657');
INSERT INTO vials (id, position, contents, viscosity_cp, concentration, density, category, radius, height, depth, name, volume, capacity, contamination, vial_coordinates, updated) VALUES (5100, 's6', 'none', 1.0, 1.0, 1.0, 0, 14, 57, -43.5194, 'none', 20000.0, 20000, 0, '{''x'': -4, ''y'': -237, ''z_top'': -17.0, ''z_bottom'': -74}', '2024-09-23 14:56:40.112');
INSERT INTO vials (id, position, contents, viscosity_cp, concentration, density, category, radius, height, depth, name, volume, capacity, contamination, vial_coordinates, updated) VALUES (5101, 's7', 'none', 1.0, 1.0, 1.0, 0, 14, 57, -43.5194, 'none', 20000.0, 20000, 0, '{''x'': -4, ''y'': -270, ''z_top'': -17.0, ''z_bottom'': -74}', '2024-09-23 14:56:40.650');
INSERT INTO vials (id, position, contents, viscosity_cp, concentration, density, category, radius, height, depth, name, volume, capacity, contamination, vial_coordinates, updated) VALUES (5102, 'e1', 'none', 1.0, 1.0, 1.0, 0, 14, 57, -19.5194, 'none', 20000.0, 20000, 0, '{''x'': -409, ''y'': -35, ''z_top'': 7.0, ''z_bottom'': -50}', '2024-09-23 14:56:41.188');
INSERT INTO vials (id, position, contents, viscosity_cp, concentration, density, category, radius, height, depth, name, volume, capacity, contamination, vial_coordinates, updated) VALUES (5103, 'w0', '{}', 0.0, 0.0, 0.0, 1, 14, 57, -73, 'waste', 1000.0, 20000, 0, '{''x'': -50, ''y'': -7, ''z_top'': -17.0, ''z_bottom'': -74}', '2024-09-23 14:56:41.201');
INSERT INTO vials (id, position, contents, viscosity_cp, concentration, density, category, radius, height, depth, name, volume, capacity, contamination, vial_coordinates, updated) VALUES (5104, 'w1', '{}', 0.0, 0.0, 0.0, 1, 14, 57, -73, 'waste', 1000.0, 20000, 0, '{''x'': -50, ''y'': -40, ''z_top'': -17.0, ''z_bottom'': -74}', '2024-09-23 14:56:41.215');
INSERT INTO vials (id, position, contents, viscosity_cp, concentration, density, category, radius, height, depth, name, volume, capacity, contamination, vial_coordinates, updated) VALUES (5105, 'w2', '{}', 0.0, 0.0, 0.0, 1, 14, 57, -73, 'waste', 1000.0, 20000, 0, '{''x'': -50, ''y'': -73, ''z_top'': -17.0, ''z_bottom'': -74}', '2024-09-23 14:56:41.230');
INSERT INTO vials (id, position, contents, viscosity_cp, concentration, density, category, radius, height, depth, name, volume, capacity, contamination, vial_coordinates, updated) VALUES (5106, 'w3', '{}', 0.0, 0.0, 0.0, 1, 14, 57, -73, 'waste', 1000.0, 20000, 0, '{''x'': -50, ''y'': -106, ''z_top'': -17.0, ''z_bottom'': -74}', '2024-09-23 14:56:41.242');
INSERT INTO vials (id, position, contents, viscosity_cp, concentration, density, category, radius, height, depth, name, volume, capacity, contamination, vial_coordinates, updated) VALUES (5107, 'w4', '{}', 0.0, 0.0, 0.0, 1, 14, 57, -73, 'waste', 1000.0, 20000, 0, '{''x'': -50, ''y'': -139, ''z_top'': -17.0, ''z_bottom'': -74}', '2024-09-23 14:56:41.255');
INSERT INTO vials (id, position, contents, viscosity_cp, concentration, density, category, radius, height, depth, name, volume, capacity, contamination, vial_coordinates, updated) VALUES (5108, 'w5', '{}', 0.0, 0.0, 0.0, 1, 14, 57, -73, 'waste', 1000.0, 20000, 0, '{''x'': -50, ''y'': -172, ''z_top'': -17.0, ''z_bottom'': -74}', '2024-09-23 14:56:41.268');
INSERT INTO vials (id, position, contents, viscosity_cp, concentration, density, category, radius, height, depth, name, volume, capacity, contamination, vial_coordinates, updated) VALUES (5109, 'w6', '{}', 0.0, 0.0, 0.0, 1, 14, 57, -73, 'waste', 1000.0, 20000, 0, '{''x'': -50, ''y'': -205, ''z_top'': -17.0, ''z_bottom'': -74}', '2024-09-23 14:56:41.282');
INSERT INTO vials (id, position, contents, viscosity_cp, concentration, density, category, radius, height, depth, name, volume, capacity, contamination, vial_coordinates, updated) VALUES (5110, 'w7', '{}', 0.0, 0.0, 0.0, 1, 14, 57, -73, 'waste', 1000.0, 20000, 0, '{''x'': -50, ''y'': -238, ''z_top'': -17.0, ''z_bottom'': -74}', '2024-09-23 14:56:41.294');

-- Table: well_hx
DROP TABLE IF EXISTS well_hx;

CREATE TABLE IF NOT EXISTS well_hx (
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

INSERT INTO well_hx (plate_id, well_id, experiment_id, project_id, status, status_date, contents, volume, coordinates, updated) VALUES (999, 'A1', NULL, NULL, 'new', '2024-09-23 15:01:15.365847', '"{}"', 0.0, '"{\"x\": -222.5, \"y\": -78, \"z_top\": -65, \"z_bottom\": -71}"', '2024-09-25 01:34:44');
INSERT INTO well_hx (plate_id, well_id, experiment_id, project_id, status, status_date, contents, volume, coordinates, updated) VALUES (999, 'A2', NULL, NULL, 'new', '2024-09-25 17:34:49', '"{}"', 0.0, '"{\"x\": -222.5, \"y\": -91.5, \"z_top\": -65, \"z_bottom\": -71}"', '2024-09-27 02:41:18');
INSERT INTO well_hx (plate_id, well_id, experiment_id, project_id, status, status_date, contents, volume, coordinates, updated) VALUES (999, 'A3', NULL, NULL, 'new', '2024-09-25 19:16:19', '"{}"', 0.0, '"{\"x\": -222.5, \"y\": -105.0, \"z_top\": -65, \"z_bottom\": -71}"', '2024-09-27 02:41:18');
INSERT INTO well_hx (plate_id, well_id, experiment_id, project_id, status, status_date, contents, volume, coordinates, updated) VALUES (999, 'A4', NULL, NULL, 'new', '2024-09-26 11:35:56', '"{}"', 0.0, '"{\"x\": -222.5, \"y\": -118.5, \"z_top\": -65, \"z_bottom\": -71}"', '2024-09-27 02:41:18');
INSERT INTO well_hx (plate_id, well_id, experiment_id, project_id, status, status_date, contents, volume, coordinates, updated) VALUES (999, 'A5', NULL, NULL, 'new', '2024-09-26 12:36:28', '"{}"', 0.0, '"{\"x\": -222.5, \"y\": -132.0, \"z_top\": -65, \"z_bottom\": -71}"', '2024-09-27 02:41:18');
INSERT INTO well_hx (plate_id, well_id, experiment_id, project_id, status, status_date, contents, volume, coordinates, updated) VALUES (999, 'A6', NULL, NULL, 'new', '2024-09-26 13:01:40', '"{}"', 0.0, '"{\"x\": -222.5, \"y\": -145.5, \"z_top\": -65, \"z_bottom\": -71}"', '2024-09-27 02:41:18');
INSERT INTO well_hx (plate_id, well_id, experiment_id, project_id, status, status_date, contents, volume, coordinates, updated) VALUES (999, 'A7', NULL, NULL, 'new', '2024-09-26 15:35:30', '"{}"', 0.0, '"{\"x\": -222.5, \"y\": -159.0, \"z_top\": -65, \"z_bottom\": -71}"', '2024-09-27 02:41:18');
INSERT INTO well_hx (plate_id, well_id, experiment_id, project_id, status, status_date, contents, volume, coordinates, updated) VALUES (999, 'A8', NULL, NULL, 'new', '2024-09-24 10:37:43', '"{}"', 0.0, '"{\"x\": -222.5, \"y\": -172.5, \"z_top\": -65, \"z_bottom\": -71}"', '2024-09-25 01:34:44');
INSERT INTO well_hx (plate_id, well_id, experiment_id, project_id, status, status_date, contents, volume, coordinates, updated) VALUES (999, 'B1', NULL, NULL, 'new', '2024-09-23 15:01:15.365847', '"{}"', 0.0, '"{\"x\": -236.5, \"y\": -78.0, \"z_top\": -65, \"z_bottom\": -71}"', '2024-09-25 01:34:44');
INSERT INTO well_hx (plate_id, well_id, experiment_id, project_id, status, status_date, contents, volume, coordinates, updated) VALUES (999, 'B2', NULL, NULL, 'new', '2024-09-24 10:37:43', '"{}"', 0.0, '"{\"x\": -236.5, \"y\": -91.5, \"z_top\": -65, \"z_bottom\": -71}"', '2024-09-25 01:34:44');
INSERT INTO well_hx (plate_id, well_id, experiment_id, project_id, status, status_date, contents, volume, coordinates, updated) VALUES (999, 'B3', NULL, NULL, 'new', '2024-09-24 10:37:43', '"{}"', 0.0, '"{\"x\": -236.5, \"y\": -105.0, \"z_top\": -65, \"z_bottom\": -71}"', '2024-09-25 01:34:44');
INSERT INTO well_hx (plate_id, well_id, experiment_id, project_id, status, status_date, contents, volume, coordinates, updated) VALUES (999, 'B4', NULL, NULL, 'new', '2024-09-24 10:37:43', '"{}"', 0.0, '"{\"x\": -236.5, \"y\": -118.5, \"z_top\": -65, \"z_bottom\": -71}"', '2024-09-25 01:34:44');
INSERT INTO well_hx (plate_id, well_id, experiment_id, project_id, status, status_date, contents, volume, coordinates, updated) VALUES (999, 'B5', NULL, NULL, 'new', '2024-09-24 10:37:43', '"{}"', 0.0, '"{\"x\": -236.5, \"y\": -132.0, \"z_top\": -65, \"z_bottom\": -71}"', '2024-09-25 01:34:44');
INSERT INTO well_hx (plate_id, well_id, experiment_id, project_id, status, status_date, contents, volume, coordinates, updated) VALUES (999, 'B6', NULL, NULL, 'new', '2024-09-24 10:37:43', '"{}"', 0.0, '"{\"x\": -236.5, \"y\": -145.5, \"z_top\": -65, \"z_bottom\": -71}"', '2024-09-25 01:34:44');
INSERT INTO well_hx (plate_id, well_id, experiment_id, project_id, status, status_date, contents, volume, coordinates, updated) VALUES (999, 'B7', NULL, NULL, 'new', '2024-09-24 11:32:09', '"{}"', 0.0, '"{\"x\": -236.5, \"y\": -159.0, \"z_top\": -65, \"z_bottom\": -71}"', '2024-09-25 19:31:34');
INSERT INTO well_hx (plate_id, well_id, experiment_id, project_id, status, status_date, contents, volume, coordinates, updated) VALUES (999, 'B8', NULL, NULL, 'new', '2024-09-23 15:01:15.365847', '"{}"', 0.0, '"{\"x\": -236.5, \"y\": -172.5, \"z_top\": -65, \"z_bottom\": -71}"', '2024-09-25 01:34:44');
INSERT INTO well_hx (plate_id, well_id, experiment_id, project_id, status, status_date, contents, volume, coordinates, updated) VALUES (999, 'C1', NULL, NULL, 'new', '2024-09-23 15:01:15.365847', '"{}"', 0.0, '"{\"x\": -250.5, \"y\": -78.0, \"z_top\": -65, \"z_bottom\": -71}"', '2024-09-25 01:34:44');
INSERT INTO well_hx (plate_id, well_id, experiment_id, project_id, status, status_date, contents, volume, coordinates, updated) VALUES (999, 'C2', NULL, NULL, 'new', '2024-09-23 15:01:15.365847', '"{}"', 0.0, '"{\"x\": -250.5, \"y\": -91.5, \"z_top\": -65, \"z_bottom\": -71}"', '2024-09-25 01:34:44');
INSERT INTO well_hx (plate_id, well_id, experiment_id, project_id, status, status_date, contents, volume, coordinates, updated) VALUES (999, 'C3', NULL, NULL, 'new', '2024-09-23 15:01:15.365847', '"{}"', 0.0, '"{\"x\": -250.5, \"y\": -105.0, \"z_top\": -65, \"z_bottom\": -71}"', '2024-09-25 01:34:44');
INSERT INTO well_hx (plate_id, well_id, experiment_id, project_id, status, status_date, contents, volume, coordinates, updated) VALUES (999, 'C4', NULL, NULL, 'new', '2024-09-23 15:01:15.365847', '"{}"', 0.0, '"{\"x\": -250.5, \"y\": -118.5, \"z_top\": -65, \"z_bottom\": -71}"', '2024-09-25 01:34:44');
INSERT INTO well_hx (plate_id, well_id, experiment_id, project_id, status, status_date, contents, volume, coordinates, updated) VALUES (999, 'C5', NULL, NULL, 'new', '2024-09-23 15:01:15.365847', '"{}"', 0.0, '"{\"x\": -250.5, \"y\": -132.0, \"z_top\": -65, \"z_bottom\": -71}"', '2024-09-25 01:34:44');
INSERT INTO well_hx (plate_id, well_id, experiment_id, project_id, status, status_date, contents, volume, coordinates, updated) VALUES (999, 'C6', NULL, NULL, 'new', '2024-09-23 15:01:15.365847', '"{}"', 0.0, '"{\"x\": -250.5, \"y\": -145.5, \"z_top\": -65, \"z_bottom\": -71}"', '2024-09-25 01:34:44');
INSERT INTO well_hx (plate_id, well_id, experiment_id, project_id, status, status_date, contents, volume, coordinates, updated) VALUES (999, 'C7', NULL, NULL, 'new', '2024-09-23 15:01:15.365847', '"{}"', 0.0, '"{\"x\": -250.5, \"y\": -159.0, \"z_top\": -65, \"z_bottom\": -71}"', '2024-09-25 01:34:44');
INSERT INTO well_hx (plate_id, well_id, experiment_id, project_id, status, status_date, contents, volume, coordinates, updated) VALUES (999, 'C8', NULL, NULL, 'new', '2024-09-23 15:01:15.365847', '"{}"', 0.0, '"{\"x\": -250.5, \"y\": -172.5, \"z_top\": -65, \"z_bottom\": -71}"', '2024-09-25 01:34:44');
INSERT INTO well_hx (plate_id, well_id, experiment_id, project_id, status, status_date, contents, volume, coordinates, updated) VALUES (999, 'D1', NULL, NULL, 'new', '2024-09-23 15:01:15.365847', '"{}"', 0.0, '"{\"x\": -264.5, \"y\": -78.0, \"z_top\": -65, \"z_bottom\": -71}"', '2024-09-25 01:34:44');
INSERT INTO well_hx (plate_id, well_id, experiment_id, project_id, status, status_date, contents, volume, coordinates, updated) VALUES (999, 'D2', NULL, NULL, 'new', '2024-09-23 15:01:15.365847', '"{}"', 0.0, '"{\"x\": -264.5, \"y\": -91.5, \"z_top\": -65, \"z_bottom\": -71}"', '2024-09-25 01:34:44');
INSERT INTO well_hx (plate_id, well_id, experiment_id, project_id, status, status_date, contents, volume, coordinates, updated) VALUES (999, 'D3', NULL, NULL, 'new', '2024-09-23 15:01:15.365847', '"{}"', 0.0, '"{\"x\": -264.5, \"y\": -105.0, \"z_top\": -65, \"z_bottom\": -71}"', '2024-09-25 01:34:44');
INSERT INTO well_hx (plate_id, well_id, experiment_id, project_id, status, status_date, contents, volume, coordinates, updated) VALUES (999, 'D4', NULL, NULL, 'new', '2024-09-23 15:01:15.365847', '"{}"', 0.0, '"{\"x\": -264.5, \"y\": -118.5, \"z_top\": -65, \"z_bottom\": -71}"', '2024-09-25 01:34:44');
INSERT INTO well_hx (plate_id, well_id, experiment_id, project_id, status, status_date, contents, volume, coordinates, updated) VALUES (999, 'D5', NULL, NULL, 'new', '2024-09-23 15:01:15.365847', '"{}"', 0.0, '"{\"x\": -264.5, \"y\": -132.0, \"z_top\": -65, \"z_bottom\": -71}"', '2024-09-25 01:34:44');
INSERT INTO well_hx (plate_id, well_id, experiment_id, project_id, status, status_date, contents, volume, coordinates, updated) VALUES (999, 'D6', NULL, NULL, 'new', '2024-09-23 15:01:15.365847', '"{}"', 0.0, '"{\"x\": -264.5, \"y\": -145.5, \"z_top\": -65, \"z_bottom\": -71}"', '2024-09-25 01:34:44');
INSERT INTO well_hx (plate_id, well_id, experiment_id, project_id, status, status_date, contents, volume, coordinates, updated) VALUES (999, 'D7', NULL, NULL, 'new', '2024-09-23 15:01:15.365847', '"{}"', 0.0, '"{\"x\": -264.5, \"y\": -159.0, \"z_top\": -65, \"z_bottom\": -71}"', '2024-09-25 01:34:44');
INSERT INTO well_hx (plate_id, well_id, experiment_id, project_id, status, status_date, contents, volume, coordinates, updated) VALUES (999, 'D8', NULL, NULL, 'new', '2024-09-23 15:01:15.365847', '"{}"', 0.0, '"{\"x\": -264.5, \"y\": -172.5, \"z_top\": -65, \"z_bottom\": -71}"', '2024-09-25 01:34:44');
INSERT INTO well_hx (plate_id, well_id, experiment_id, project_id, status, status_date, contents, volume, coordinates, updated) VALUES (999, 'E1', NULL, NULL, 'new', '2024-09-23 15:01:15.365847', '"{}"', 0.0, '"{\"x\": -278.5, \"y\": -78.0, \"z_top\": -65, \"z_bottom\": -71}"', '2024-09-25 01:34:44');
INSERT INTO well_hx (plate_id, well_id, experiment_id, project_id, status, status_date, contents, volume, coordinates, updated) VALUES (999, 'E2', NULL, NULL, 'new', '2024-09-23 15:01:15.365847', '"{}"', 0.0, '"{\"x\": -278.5, \"y\": -91.5, \"z_top\": -65, \"z_bottom\": -71}"', '2024-09-25 01:34:44');
INSERT INTO well_hx (plate_id, well_id, experiment_id, project_id, status, status_date, contents, volume, coordinates, updated) VALUES (999, 'E3', NULL, NULL, 'new', '2024-09-23 15:01:15.365847', '"{}"', 0.0, '"{\"x\": -278.5, \"y\": -105.0, \"z_top\": -65, \"z_bottom\": -71}"', '2024-09-25 01:34:44');
INSERT INTO well_hx (plate_id, well_id, experiment_id, project_id, status, status_date, contents, volume, coordinates, updated) VALUES (999, 'E4', NULL, NULL, 'new', '2024-09-23 15:01:15.365847', '"{}"', 0.0, '"{\"x\": -278.5, \"y\": -118.5, \"z_top\": -65, \"z_bottom\": -71}"', '2024-09-25 01:34:44');
INSERT INTO well_hx (plate_id, well_id, experiment_id, project_id, status, status_date, contents, volume, coordinates, updated) VALUES (999, 'E5', NULL, NULL, 'new', '2024-09-23 15:01:15.365847', '"{}"', 0.0, '"{\"x\": -278.5, \"y\": -132.0, \"z_top\": -65, \"z_bottom\": -71}"', '2024-09-25 01:34:44');
INSERT INTO well_hx (plate_id, well_id, experiment_id, project_id, status, status_date, contents, volume, coordinates, updated) VALUES (999, 'E6', NULL, NULL, 'new', '2024-09-23 15:01:15.365847', '"{}"', 0.0, '"{\"x\": -278.5, \"y\": -145.5, \"z_top\": -65, \"z_bottom\": -71}"', '2024-09-25 01:34:44');
INSERT INTO well_hx (plate_id, well_id, experiment_id, project_id, status, status_date, contents, volume, coordinates, updated) VALUES (999, 'E7', NULL, NULL, 'new', '2024-09-23 15:01:15.365847', '"{}"', 0.0, '"{\"x\": -278.5, \"y\": -159.0, \"z_top\": -65, \"z_bottom\": -71}"', '2024-09-25 01:34:44');
INSERT INTO well_hx (plate_id, well_id, experiment_id, project_id, status, status_date, contents, volume, coordinates, updated) VALUES (999, 'E8', NULL, NULL, 'new', '2024-09-23 15:01:15.365847', '"{}"', 0.0, '"{\"x\": -278.5, \"y\": -172.5, \"z_top\": -65, \"z_bottom\": -71}"', '2024-09-25 01:34:44');

-- Table: wellplates
DROP TABLE IF EXISTS wellplates;

CREATE TABLE IF NOT EXISTS wellplates (
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
    REFERENCES plate_types (id) 
);

INSERT INTO wellplates (id, type_id, current, a1_x, a1_y, orientation, rows, cols, z_bottom, z_top, echem_height, image_height) VALUES (112, 7, 1, -222.5, -78, 0, 'ABCDE', '8', -71, -65, -72.5, -50.0);
INSERT INTO wellplates (id, type_id, current, a1_x, a1_y, orientation, rows, cols, z_bottom, z_top, echem_height, image_height) VALUES (999, 4, 0, -222.5, -78, 0, 'ABCDEFGH', '12', -71, -65, -72.5, -50.0);

-- Index: idx_unique_active
DROP INDEX IF EXISTS idx_unique_active;

CREATE INDEX IF NOT EXISTS idx_unique_active ON pipette (
    active
)
WHERE active = 1;


-- Index: idx_unique_current
DROP INDEX IF EXISTS idx_unique_current;

CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_current ON wellplates (
    current
)
WHERE current = 1;


-- Index: idx_vials_position
DROP INDEX IF EXISTS idx_vials_position;

CREATE INDEX IF NOT EXISTS idx_vials_position ON vials (
    position
);


-- Index: idx_vials_updated
DROP INDEX IF EXISTS idx_vials_updated;

CREATE INDEX IF NOT EXISTS idx_vials_updated ON vials (
    updated
);


-- Index: msg_id_index
DROP INDEX IF EXISTS msg_id_index;

CREATE INDEX IF NOT EXISTS msg_id_index ON slack_tickets (
    msg_id,
    timestamp DESC
);


-- Trigger: on_insert_timestamp
DROP TRIGGER IF EXISTS on_insert_timestamp;
CREATE TRIGGER IF NOT EXISTS on_insert_timestamp
                       AFTER INSERT
                          ON vials
                    FOR EACH ROW
BEGIN
    UPDATE vials
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
                          ON pipette
                    FOR EACH ROW
BEGIN
    INSERT INTO pipette_log (
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
                          ON experiments
                    FOR EACH ROW
BEGIN
    UPDATE experiments
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
                          ON pipette
                    FOR EACH ROW
BEGIN
    UPDATE pipette
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
                          ON vials
                    FOR EACH ROW
BEGIN
    UPDATE vials
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
                          ON well_hx
                    FOR EACH ROW
BEGIN
    UPDATE well_hx
       SET updated = datetime('now', 'utc') 
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
                          ON experiment_parameters
                    FOR EACH ROW
BEGIN
    UPDATE experiment_parameters
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
                          ON experiment_results
                    FOR EACH ROW
BEGIN
    UPDATE experiment_results
       SET updated = datetime('now') 
     WHERE id = OLD.id;
END;


-- Trigger: update_when_used
DROP TRIGGER IF EXISTS update_when_used;
CREATE TRIGGER IF NOT EXISTS update_when_used
                       AFTER UPDATE OF volume_ul
                          ON pipette
                    FOR EACH ROW
BEGIN
    UPDATE pipette
       SET uses = uses + 1
     WHERE id = OLD.id;
END;


-- View: experiment_params
DROP VIEW IF EXISTS experiment_params;
CREATE VIEW IF NOT EXISTS experiment_params AS
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
      FROM experiment_parameters
     GROUP BY experiment_id
     ORDER BY experiment_id DESC;


-- View: experiment_status
DROP VIEW IF EXISTS experiment_status;
CREATE VIEW IF NOT EXISTS experiment_status AS
    SELECT experiment_id,
           status
      FROM well_hx
     WHERE experiment_id IS NOT NULL
     ORDER BY experiment_id ASC;


-- View: new_wellplates
DROP VIEW IF EXISTS new_wellplates;
CREATE VIEW IF NOT EXISTS new_wellplates AS
    SELECT wh.plate_id,
           wp.type_id
      FROM well_hx wh
           JOIN
           wellplates wp ON wh.plate_id = wp.id
     WHERE wh.status = 'new'
     GROUP BY wh.plate_id
    HAVING COUNT( * ) = 96;


-- View: pipette_status
DROP VIEW IF EXISTS pipette_status;
CREATE VIEW IF NOT EXISTS pipette_status AS
    SELECT *
      FROM pipette-- WHERE updated = (SELECT MAX(updated) FROM pipette)
     WHERE id = (
                    SELECT MAX(id) 
                      FROM pipette
                )
     LIMIT 1;


-- View: queue
DROP VIEW IF EXISTS queue;
CREATE VIEW IF NOT EXISTS queue AS
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
      FROM experiments AS a
           JOIN
           wellplates AS b ON a.well_type = b.type_id
           JOIN
           well_hx AS c ON a.experiment_id = c.experiment_id AND 
                           c.status IN ('queued', 'waiting') 
     WHERE b.current = 1
     ORDER BY a.priority ASC,
              a.experiment_id ASC;


-- View: vial_status
DROP VIEW IF EXISTS vial_status;
CREATE VIEW IF NOT EXISTS vial_status AS
    SELECT v1.*
      FROM vials v1
           LEFT JOIN
           vials v2 ON v1.position = v2.position AND 
                       (v1.updated < v2.updated OR 
                        (v1.updated = v2.updated AND 
                         v1.id < v2.id) ) 
     WHERE v2.id IS NULL
     ORDER BY v1.position ASC;


-- View: well_status
DROP VIEW IF EXISTS well_status;
CREATE VIEW IF NOT EXISTS well_status AS
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
      FROM well_hx AS a
           JOIN
           wellplates AS b ON a.plate_id = b.id
           JOIN
           plate_types AS c ON b.type_id = c.id
     WHERE b.current = 1
     ORDER BY SUBSTRING(a.well_id, 1, 1),
              CAST (SUBSTRING(a.well_id, 2) AS UNSIGNED);


COMMIT TRANSACTION;
PRAGMA foreign_keys = on;
