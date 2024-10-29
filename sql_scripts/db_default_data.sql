--
-- File generated with SQLiteStudio v3.4.4 on Fri Jun 21 03:20:57 2024
--
-- Text encoding used: System
--
BEGIN TRANSACTION;
INSERT INTO system_versions (
        id,
        mill,
        pump,
        potentiostat,
        reference_electrode,
        working_electrode,
        wells,
        pipette_adapter,
        optics,
        scale,
        camera,
        lens
    )
VALUES (
        1,
        2,
        '01',
        '01',
        '01',
        '02',
        '04',
        '05',
        '00',
        '00',
        '01',
        '01'
    );
INSERT INTO well_types (
        id,
        substrate,
        gasket,
        count,
        shape,
        radius_mm,
        offset_mm,
        height_mm,
        max_liquid_height_mm,
        capacity_ul
    )
VALUES (
        1,
        'gold',
        'grace bio-labs',
        96,
        'square',
        4.0,
        9.0,
        7.0,
        6.0,
        300.0
    );
INSERT INTO well_types (
        id,
        substrate,
        gasket,
        count,
        shape,
        radius_mm,
        offset_mm,
        height_mm,
        max_liquid_height_mm,
        capacity_ul
    )
VALUES (
        2,
        'ito',
        'grace bio-labs',
        96,
        'square',
        4.0,
        9.0,
        7.0,
        6.0,
        300.0
    );
INSERT INTO well_types (
        id,
        substrate,
        gasket,
        count,
        shape,
        radius_mm,
        offset_mm,
        height_mm,
        max_liquid_height_mm,
        capacity_ul
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
        150.0
    );
INSERT INTO well_types (
        id,
        substrate,
        gasket,
        count,
        shape,
        radius_mm,
        offset_mm,
        height_mm,
        max_liquid_height_mm,
        capacity_ul
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
        4.5,
        150.0
    );
INSERT INTO pipette (
        id,
        capacity_ul,
        capacity_ml,
        volume_ul,
        volume_ml,
        contents,
        updated,
        active,
        uses
    )
VALUES (
        1,
        200,
        0.2,
        0,
        0,
        '',
        datetime('now', 'localtime'),
        1,
        0
    );

COMMIT;