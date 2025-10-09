WITH RECURSIVE
params AS (
  SELECT
    1            AS rack_id,       -- fixed rack_id
    0            AS type_default,  -- 0=liquid, 1=solid
    200.0        AS capacity_default,
    'default'    AS name_default
),
rack AS (
  SELECT
    r.id                               AS rack_id,
    r.a1_x, r.a1_y,
    COALESCE(r.orientation, 0) % 4      AS orientation,
    r.rows, r.cols, r.pickup_height,
    r.drop_coordinates                  AS rack_drop_json,
    rt.x_spacing, rt.y_spacing, rt.x_offset, rt.y_offset,
    rt.radius_mm                        AS rack_radius_mm
  FROM panda_tipracks r
  JOIN panda_tiprack_types rt ON rt.id = r.type_id
  JOIN params p ON p.rack_id = r.id
),
nrows(n) AS (SELECT length(rows) FROM rack),
ncols(n) AS (SELECT cols FROM rack),
row_idx(i) AS (
  SELECT 1
  UNION ALL
  SELECT i+1 FROM row_idx, nrows WHERE i < nrows.n
),
col_idx(j) AS (
  SELECT 1
  UNION ALL
  SELECT j+1 FROM col_idx, ncols WHERE j < ncols.n
),
letters AS (
  SELECT substr(rack.rows, row_idx.i, 1) AS row_letter,
         row_idx.i AS row_i
  FROM rack, row_idx
),
cells AS (
  SELECT
    rack.*,
    letters.row_letter, letters.row_i,
    col_idx.j AS col_j,
    rack.a1_x AS base_x,                    -- anchor at A1
    rack.a1_y AS base_y,
    (col_idx.j - 1) * rack.x_spacing     AS dx,
    (letters.row_i - 1) * rack.y_spacing AS dy
  FROM rack, letters, col_idx
),
orient AS (
  SELECT
    rack_id,
    row_letter || CAST(col_j AS TEXT) AS tip_id,
    CASE orientation WHEN 0 THEN dx WHEN 1 THEN dy WHEN 2 THEN -dx WHEN 3 THEN -dy END AS ox,
    CASE orientation WHEN 0 THEN dy WHEN 1 THEN -dx WHEN 2 THEN -dy WHEN 3 THEN dx END AS oy,
    base_x, base_y,
    pickup_height AS z,
    rack_drop_json,
    rack_radius_mm
  FROM cells
),
coords AS (
  SELECT
    rack_id,
    tip_id,
    (base_x - oy) AS x,                     -- swap and trend negative
    (base_y - ox) AS y,
    z,
    rack_drop_json,
    rack_radius_mm
  FROM orient
)
INSERT INTO panda_tip_hx (
  rack_id,
  tip_id,
  experiment_id,
  project_id,
  status,
  status_date,
  updated,
  radius_mm,
  volume,
  capacity,
  contamination,
  dead_volume,
  pickup_height,
  drop_coordinates,
  coordinates,
  name,
  type
)
SELECT
  c.rack_id,
  c.tip_id,
  0 AS experiment_id,
  0 AS project_id,
  'new' AS status,
  CURRENT_TIMESTAMP AS status_date,
  CURRENT_TIMESTAMP AS updated,
  COALESCE(c.rack_radius_mm, 0.0) AS radius_mm,
  0.0 AS volume,
  (SELECT capacity_default FROM params),
  0 AS contamination,
  0 AS dead_volume,
  z AS pickup_height,
  COALESCE(c.rack_drop_json, json_object('x',0.0,'y',0.0,'z',0.0)) AS drop_coordinates,
  json_object('x', c.x, 'y', c.y, 'z', c.z) AS coordinates,
  (SELECT name_default FROM params),
  (SELECT type_default FROM params)
FROM coords c
WHERE NOT EXISTS (
  SELECT 1 FROM panda_tip_hx h
  WHERE h.rack_id = c.rack_id AND h.tip_id = c.tip_id
);
