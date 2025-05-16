--
-- File generated with SQLiteStudio v3.4.17 on Tue Apr 22 21:32:12 2025
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
    context       TEXT,
    created       TEXT    DEFAULT (CURRENT_TIMESTAMP),
    updated       TEXT    DEFAULT (CURRENT_TIMESTAMP) 
);


-- Table: panda_experiments
DROP TABLE IF EXISTS panda_experiments;

CREATE TABLE IF NOT EXISTS panda_experiments (
    experiment_id       BIGINT  PRIMARY KEY,
    project_id          INTEGER,
    project_campaign_id INTEGER,
    well_type           INTEGER,
    protocol_id         TEXT,
    priority            INTEGER DEFAULT 0,
    filename            TEXT    DEFAULT NULL,
    created             TEXT    DEFAULT (CURRENT_TIMESTAMP),
    updated             TEXT    DEFAULT (CURRENT_TIMESTAMP),
    needs_analysis      INTEGER DEFAULT (0),
    analysis_id         INTEGER,
    panda_version       NUMERIC DEFAULT (1.0),
    panda_unit_id       INTEGER REFERENCES panda_units (id) ON DELETE SET NULL
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


-- Table: panda_mill_tools
DROP TABLE IF EXISTS panda_mill_tools;

CREATE TABLE IF NOT EXISTS panda_mill_tools (
    id      INTEGER   PRIMARY KEY AUTOINCREMENT,
    name    TEXT      NOT NULL,
    offset  TEXT      NOT NULL,
    updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    capacity_ul   REAL    NOT NULL,
    capacity_ml   REAL    NOT NULL,
    volume_ul     REAL    NOT NULL,
    volume_ml     REAL    NOT NULL,
    contents      TEXT,
    updated       TEXT    DEFAULT (CURRENT_TIMESTAMP),
    active        INTEGER,
    uses          INTEGER DEFAULT (0),
    panda_unit_id INTEGER REFERENCES panda_units (id) ON DELETE SET NULL
);


-- Table: panda_pipette_log
DROP TABLE IF EXISTS panda_pipette_log;

CREATE TABLE IF NOT EXISTS panda_pipette_log (
    id            INTEGER PRIMARY KEY,
    pipette_id    INTEGER,
    volume_ul     REAL    NOT NULL,
    volume_ml     REAL    NOT NULL,
    updated       TEXT    DEFAULT CURRENT_TIMESTAMP,
    panda_unit_id INTEGER REFERENCES panda_units (id) ON DELETE SET NULL,
    FOREIGN KEY (
        pipette_id
    )
    REFERENCES panda_pipette (id) 
);


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


-- Table: panda_protocols
DROP TABLE IF EXISTS panda_protocols;

CREATE TABLE IF NOT EXISTS panda_protocols (
    id       INTEGER PRIMARY KEY,
    project  INTEGER,
    name     TEXT,
    filepath TEXT
);


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
    id            INTEGER   PRIMARY KEY AUTOINCREMENT,
    status        TEXT      NOT NULL,
    comment       TEXT,
    status_time   TIMESTAMP DEFAULT (CURRENT_TIMESTAMP),
    test_mode     BOOLEAN,
    panda_unit_id INTEGER   REFERENCES panda_units (id) ON DELETE SET NULL
);


-- Table: panda_units
DROP TABLE IF EXISTS panda_units;

CREATE TABLE IF NOT EXISTS panda_units (
    id      INTEGER PRIMARY KEY ASC ON CONFLICT ROLLBACK AUTOINCREMENT,
    version REAL    NOT NULL
                    DEFAULT (1.0),
    name    TEXT    CONSTRAINT [Units must have unique names] UNIQUE ON CONFLICT ROLLBACK
);


-- Table: panda_user_projects
DROP TABLE IF EXISTS panda_user_projects;

CREATE TABLE IF NOT EXISTS panda_user_projects (
    user_id    INTEGER CONSTRAINT [User ID Constraint] REFERENCES panda_users (id) ON DELETE CASCADE,
    project_id INTEGER CONSTRAINT [Project ID Constraint] REFERENCES panda_projects (id),
    current    BOOLEAN DEFAULT 1 
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


-- Table: panda_vials
DROP TABLE IF EXISTS panda_vials;

CREATE TABLE IF NOT EXISTS panda_vials (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    position       TEXT,
    category       INTEGER,
    name           TEXT,
    contents       TEXT,
    viscosity_cp   REAL,
    concentration  REAL,
    density        REAL,
    height         REAL    DEFAULT (57.0),
    radius         REAL    DEFAULT (14.0),
    volume         REAL    DEFAULT (20000.0),
    capacity       REAL    DEFAULT (20000.0),
    contamination  INTEGER DEFAULT (0),
    coordinates    TEXT,
    base_thickness REAL    DEFAULT (1.0),
    dead_volume    REAL    DEFAULT (1000.0),
    volume_height  REAL    GENERATED ALWAYS AS (round(coalesce(json_extract(coordinates, '$.z'), 0) + base_thickness + (volume / (pi() * power(radius, 2) ) ), 2) ) STORED,
    bottom         REAL    GENERATED ALWAYS AS (round(coalesce(json_extract(coordinates, '$.z'), 0) + base_thickness + (dead_volume / (pi() * power(radius, 2) ) ), 2) ) STORED,
    top            REAL    GENERATED ALWAYS AS (round(coalesce(json_extract(coordinates, '$.z'), 0) + base_thickness + height, 2) ) STORED,
    updated        TEXT    DEFAULT (CURRENT_TIMESTAMP),
    active         INTEGER DEFAULT (1),
    panda_unit_id  INTEGER REFERENCES panda_units (id) ON DELETE SET NULL
);


-- Table: panda_vials_log
DROP TABLE IF EXISTS panda_vials_log;

CREATE TABLE IF NOT EXISTS panda_vials_log (
    id             INTEGER PRIMARY KEY ASC AUTOINCREMENT,
    old_id         INTEGER,
    position       TEXT,
    category       INTEGER,
    name           TEXT,
    contents       TEXT,
    viscosity_cp   REAL,
    concentration  REAL,
    density        REAL,
    height         REAL    DEFAULT (57.0),
    radius         REAL    DEFAULT (14.0),
    volume         REAL    DEFAULT (20000.0),
    capacity       REAL    DEFAULT (20000.0),
    contamination  INTEGER DEFAULT (0),
    coordinates    TEXT,
    base_thickness REAL    DEFAULT (1.0),
    dead_volume    REAL    DEFAULT (1000.0),
    volume_height  REAL,
    bottom         REAL,
    top            REAL,
    updated        TEXT    DEFAULT (CURRENT_TIMESTAMP),
    active         INTEGER DEFAULT (1),
    panda_unit_id  INTEGER
);


-- Table: panda_well_hx
DROP TABLE IF EXISTS panda_well_hx;

CREATE TABLE IF NOT EXISTS panda_well_hx (
    plate_id       INTEGER,
    well_id        TEXT,
    experiment_id  INTEGER,
    project_id     INTEGER,
    status         TEXT,
    contents       TEXT,
    volume         REAL,
    coordinates    TEXT,
    base_thickness REAL    DEFAULT (1),
    height         REAL    DEFAULT (6),
    radius         REAL    DEFAULT (3.25),
    capacity       REAL    DEFAULT (150),
    contamination  INTEGER DEFAULT (0),
    dead_volume    REAL    DEFAULT (0.01),
    name           TEXT,
    top            REAL    GENERATED ALWAYS AS (round(json_extract(coordinates, '$.z') + base_thickness + height, 2) ) STORED,
    bottom         REAL    GENERATED ALWAYS AS (round(json_extract(coordinates, '$.z') + base_thickness, 2) ) STORED,
    volume_height  REAL    GENERATED ALWAYS AS (round(json_extract(coordinates, '$.z') + base_thickness + round(dead_volume / (pi() * radius * radius), 3), 2) ) STORED,
    status_date    TEXT    DEFAULT (CURRENT_TIMESTAMP) 
                           NOT NULL ON CONFLICT REPLACE,
    updated        TEXT    DEFAULT (CURRENT_TIMESTAMP) 
                           NOT NULL ON CONFLICT REPLACE,
    PRIMARY KEY (
        plate_id,
        well_id
    )
);


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


-- Table: panda_wellplates
DROP TABLE IF EXISTS panda_wellplates;

CREATE TABLE IF NOT EXISTS panda_wellplates (
    id             INTEGER NOT NULL
                           PRIMARY KEY AUTOINCREMENT,
    type_id        INTEGER REFERENCES panda_wellplate_types (id),
    current        BOOLEAN DEFAULT 0,
    a1_x           NUMERIC CONSTRAINT [Defualt A1_X] DEFAULT ( -221.75),
    a1_y           NUMERIC CONSTRAINT [Defualt A1_Y] DEFAULT ( -78.5),
    orientation    INTEGER CONSTRAINT [DEFAULT ORIENTATION] DEFAULT (0),
    rows           INTEGER CONSTRAINT [DEFUALT ROWS] DEFAULT (13),
    cols           TEXT    CONSTRAINT [DEFAULT COLUMNS] DEFAULT ABCDEFGH,
    bottom         NUMERIC GENERATED ALWAYS AS ( (round(coalesce(json_extract(coordinates, '$.z'), 0) + base_thickness, 2) ) ) STORED,
    top            NUMERIC GENERATED ALWAYS AS ( (round(coalesce(json_extract(coordinates, '$.z'), 0) + base_thickness + height, 2) ) ) STORED,
    echem_height   NUMERIC CONSTRAINT [DEFAULT ECHEM HEIGHT] DEFAULT ( -70),
    image_height   REAL    DEFAULT (0),
    coordinates    TEXT,
    base_thickness REAL,
    height,
    name,
    panda_unit_id  INTEGER REFERENCES panda_units (id) ON DELETE SET NULL,
    FOREIGN KEY (
        type_id
    )
    REFERENCES panda_wellplate_types (id) 
);


-- Index: idx_unique_active
DROP INDEX IF EXISTS idx_unique_active;

CREATE INDEX IF NOT EXISTS idx_unique_active ON panda_pipette (
    active
)
WHERE active = 1;


-- Index: idx_unique_current
DROP INDEX IF EXISTS idx_unique_current;

CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_current ON panda_wellplates (
    current,
    panda_unit_id
)
WHERE current = 1;


-- Index: msg_id_index
DROP INDEX IF EXISTS msg_id_index;

CREATE INDEX IF NOT EXISTS msg_id_index ON panda_slack_tickets (
    msg_id,
    timestamp DESC
);


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
           a.filename,
           a.well_type AS [well type],
           c.well_id,
           c.status,
           c.status_date,
           a.panda_unit_id
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
WITH RankedVials AS (
        SELECT v.*,
               ROW_NUMBER() OVER (PARTITION BY v.position ORDER BY v.updated DESC,
               v.id DESC) AS rn
          FROM panda_vials v
         WHERE v.active = 1
    )
    SELECT rv.*
      FROM RankedVials rv
     WHERE rv.rn = 1
     ORDER BY rv.position ASC;


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
           c.gasket_height_mm AS height,
           b.panda_unit_id
      FROM panda_well_hx AS a
           JOIN
           panda_wellplates AS b ON a.plate_id = b.id
           JOIN
           panda_wellplate_types AS c ON b.type_id = c.id
     WHERE b.current = 1
     ORDER BY SUBSTRING(a.well_id, 1, 1),
              CAST (SUBSTRING(a.well_id, 2) AS UNSIGNED);


-- Trigger: log
DROP TRIGGER IF EXISTS log;
CREATE TRIGGER IF NOT EXISTS log
                       AFTER UPDATE OF position,
                                       category,
                                       name,
                                       contents,
                                       viscosity_cp,
                                       concentration,
                                       density,
                                       height,
                                       radius,
                                       volume,
                                       capacity,
                                       coordinates,
                                       base_thickness,
                                       dead_volume,
                                       active
                          ON panda_vials
                    FOR EACH ROW
BEGIN
    INSERT INTO panda_vials_log (
                                    old_id,
                                    position,
                                    category,
                                    name,
                                    contents,
                                    viscosity_cp,
                                    concentration,
                                    density,
                                    height,
                                    radius,
                                    volume,
                                    capacity,
                                    contamination,
                                    coordinates,
                                    base_thickness,
                                    dead_volume,
                                    volume_height,
                                    bottom,
                                    top,
                                    updated,
                                    active,
                                    panda_unit_id
                                )
                                VALUES (
                                    OLD.id,
                                    OLD.position,
                                    OLD.category,
                                    OLD.name,
                                    OLD.contents,
                                    OLD.viscosity_cp,
                                    OLD.concentration,
                                    OLD.density,
                                    OLD.height,
                                    OLD.radius,
                                    OLD.volume,
                                    OLD.capacity,
                                    OLD.contamination,
                                    OLD.coordinates,
                                    OLD.base_thickness,
                                    OLD.dead_volume,
                                    OLD.volume_height,
                                    OLD.bottom,
                                    OLD.top,
                                    CURRENT_TIMESTAMP,
                                    OLD.active,
                                    OLD.panda_unit_id
                                );
END;


-- Trigger: update_log
DROP TRIGGER IF EXISTS update_log;
CREATE TRIGGER IF NOT EXISTS update_log
                       AFTER UPDATE OF id,
                                       capacity_ul,
                                       capacity_ml,
                                       volume_ul,
                                       volume_ml,
                                       contents,
                                       active
                          ON panda_pipette
                    FOR EACH ROW
BEGIN
    INSERT INTO panda_pipette_log (
                                      pipette_id,
                                      volume_ul,
                                      volume_ml,
                                      updated,
                                      panda_unit_id
                                  )
                                  VALUES (
                                      NEW.id,
                                      NEW.volume_ul,
                                      NEW.volume_ml,
                                      strftime('%Y-%m-%d %H:%M:%f', 'now'),
                                      NEW.panda_unit_id
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
                                       priority,
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


-- Trigger: updated
DROP TRIGGER IF EXISTS updated;
CREATE TRIGGER IF NOT EXISTS updated
                       AFTER UPDATE OF position,
                                       category,
                                       name,
                                       contents,
                                       viscosity_cp,
                                       concentration,
                                       density,
                                       height,
                                       radius,
                                       volume,
                                       capacity,
                                       coordinates,
                                       base_thickness,
                                       dead_volume,
                                       active
                          ON panda_vials
                    FOR EACH ROW
BEGIN
    UPDATE panda_vials
       SET updated = CURRENT_TIMESTAMP
     WHERE id = OLD.id;
END;


-- Trigger: vial_contamination
DROP TRIGGER IF EXISTS vial_contamination;
CREATE TRIGGER IF NOT EXISTS vial_contamination
                       AFTER UPDATE OF volume
                          ON panda_vials
                    FOR EACH ROW
BEGIN
    UPDATE panda_vials
       SET contamination = contamination + 1
     WHERE id = NEW.id;
END;

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
