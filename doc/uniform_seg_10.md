# <!-- omit in toc -->0.1-mile Uniform Segments

This document describes the methodology used to create 1/10-mile uniform segments.
- [Process](#process)
  - [Part 1: Proposing Segments](#part-1-proposing-segments)
    - [Case 1: Segment is < 0.125 miles](#case-1-segment-is--0125-miles)
    - [Case 2: Segment is < 0.25 miles](#case-2-segment-is--025-miles)
    - [Case 3: Segment is >= 0.25 miles](#case-3-segment-is--025-miles)
  - [Part 2: Extracting Relevant Data](#part-2-extracting-relevant-data)
    - [Detail 1: Fundamental parameters](#detail-1-fundamental-parameters)
  - [Part 2b: Extracting Geometry](#part-2b-extracting-geometry)
  - [Part 3: Mapping Crashes to Uniform Segments](#part-3-mapping-crashes-to-uniform-segments)
  - [Ranking the Crash Density](#ranking-the-crash-density)
  - [Visualizing the Crash Stats](#visualizing-the-crash-stats)
  - [Dumping out the Crash Matchup](#dumping-out-the-crash-matchup)
- [Revisiting Matchup and Intersections](#revisiting-matchup-and-intersections)

## Process
This process follows the [Uniform Segments documentation](uniform_seg.md), but for the purpose of creating uniform segments that are about 1/10 of a mile.

### Part 1: Proposing Segments
Here we propose the division of segments, keeping to 1/10-mile segments and allowing for some flexibility at the ends.

This is the table definition for the matchup:
```sql
CREATE TABLE uniform_segs_01mi (
  roadway_gid integer,
  ref_begin real,
  ref_end real,
  seg_count integer,
  seg_total integer,
  total_length real,
  closest_frm_dfo numeric,
  overlap real,
  on_system boolean,
  center_lat real,
  center_lon real,
  PRIMARY KEY (roadway_gid, ref_begin)
);
```

#### Case 1: Segment is < 0.125 miles
The segment shall be kept as-is.
```sql
WITH q AS (
  SELECT gid, SUM(len_sec) total_length, MIN(frm_dfo) ref_begin, MAX(to_dfo) ref_end FROM roadway_inv GROUP BY gid
), r AS (
  SELECT gid, total_length, ref_begin, ref_end FROM q WHERE total_length < 0.125
)
INSERT INTO uniform_segs_01mi
  (roadway_gid, ref_begin, ref_end, seg_count, seg_total, total_length)
SELECT gid, ref_begin, ref_end, 1, 1, total_length FROM r;
```

#### Case 2: Segment is < 0.25 miles
The segments will be split into two.
```sql
WITH q AS (
  SELECT gid, SUM(len_sec) total_length, MIN(frm_dfo) ref_begin, MAX(to_dfo) ref_end FROM roadway_inv GROUP BY gid
), r AS (
  SELECT gid, total_length, ref_begin, ref_end, GENERATE_SERIES(0, 1) g_id
    FROM q WHERE total_length >= 0.125 AND total_length < 0.25
)
INSERT INTO uniform_segs_01mi
  (roadway_gid, ref_begin, ref_end, seg_count, seg_total, total_length)
SELECT gid,
    ref_begin + (ref_end - ref_begin) * g_id / 2,
    ref_begin + (ref_end - ref_begin) * (g_id + 1) / 2,
    g_id + 1, 2, total_length FROM r;
```

#### Case 3: Segment is >= 0.25 miles
The segments will have 1/10-mile chunks in between, with ends that are no less than 0.075 miles and no more than 0.125 miles.
```sql
WITH q AS (
  SELECT gid, SUM(len_sec) total_length, MIN(frm_dfo) ref_begin, MAX(to_dfo) ref_end FROM roadway_inv GROUP BY gid
), r AS (
  SELECT gid, total_length, ref_begin, ref_end, GENERATE_SERIES(0, FLOOR((total_length - 0.15) / 0.1)::integer + 1) g_id
    FROM q WHERE total_length >= 0.25
)
INSERT INTO uniform_segs_01mi
  (roadway_gid, ref_begin, ref_end, seg_count, seg_total, total_length)
SELECT gid,
    CASE WHEN g_id = 0 THEN ref_begin ELSE ref_begin + (total_length - FLOOR((total_length - 0.15) / 0.1) * 0.1) / 2 + (g_id - 1) * 0.1 END,
    CASE WHEN g_id = FLOOR((total_length - 0.15) / 0.1) + 1 THEN ref_end ELSE ref_begin + (total_length - FLOOR((total_length - 0.15) / 0.1) * 0.1) / 2 + g_id * 0.1 END,
    g_id + 1,
    FLOOR((total_length - 0.15) / 0.1) + 2,
    total_length FROM r;
```

### Part 2: Extracting Relevant Data
This part involves keeping the variable values that are most represented between the extents of each new uniform segment.

#### Detail 1: Fundamental parameters
To find the majority `f_system`, `spd_max`, `hwy_des1`, and others, we need to first find the overlap and largest contributing segment from the TxDOT Roadway Inventory:
```sql
WITH q AS (
  SELECT DISTINCT ON (r.gid, ref_begin)
    r.gid, ref_begin, ref_end, frm_dfo, to_dfo,
      LEAST(to_dfo, ref_end) - GREATEST(frm_dfo, ref_begin) AS overlap
    FROM uniform_segs_01mi us1, roadway_inv r
    WHERE us1.roadway_gid = r.gid
      AND NOT (ref_begin > to_dfo OR ref_end < frm_dfo)
  ORDER BY r.gid ASC, ref_begin ASC, LEAST(to_dfo, ref_end) - GREATEST(frm_dfo, ref_begin) DESC
)
UPDATE uniform_segs_01mi us1
  SET closest_frm_dfo = q.frm_dfo, overlap = q.overlap
  FROM q
  WHERE us1.roadway_gid = q.gid
    AND us1.ref_begin = q.ref_begin;
```

### Part 2b: Extracting Geometry
This exercise assembles together geometry for each uniform segment so that visualization is easier to do.

```sql
CREATE TEMP TABLE seg_extracts1 AS
WITH q AS (
  SELECT roadway_gid, ref_begin, ref_end, frm_dfo, to_dfo, r.geog
  FROM uniform_segs_01mi, roadway_inv r
  WHERE roadway_gid = gid
    AND to_dfo >= ref_begin::numeric
    AND frm_dfo <= ref_end::numeric
  ORDER BY roadway_gid, ref_begin, frm_dfo
)
SELECT q.roadway_gid, q.ref_begin, q.ref_end, array_agg(q.geog) AS geog_array, min(frm_dfo::float) AS min_frm_dfo, max(to_dfo::float) AS max_to_dfo
FROM q
GROUP BY q.roadway_gid, q.ref_begin, q.ref_end;

-- Try to convert to LineString so that we can do linear referencing:
ALTER TABLE seg_extracts1 ADD COLUMN geog_multi geography(multilinestring);
ALTER TABLE seg_extracts1 ADD COLUMN geog_gen geography;
UPDATE seg_extracts1 SET geog_multi = ST_MakeValid(ST_Union(geog_array::geometry[]));
UPDATE seg_extracts1 SET geog_gen = ST_LineMerge(geog_multi::geometry);

-- There's 51 records that couldn't be LineStrings. See if we can coerce them:
UPDATE seg_extracts1 SET geog_gen = ST_LineMerge(ST_SnapToGrid(geog_gen::geometry, 0.001))
WHERE ST_GeometryType(geog_gen::geometry) <> 'ST_LineString';
-- That fixed 17 of them. 

-- For the rest, which roads do they correspond with?
SELECT roadway_gid, ref_begin, st_geometrytype(geog_gen::geometry), r.hwy, r.ste_nam
FROM seg_extracts1 se, roadway_inv r
WHERE se.roadway_gid::numeric = r.gid
  AND se.ref_begin::numeric = r.frm_dfo
  AND ST_GeometryType(geog_gen::geometry) <> 'ST_LineString';

-- Where we can, trim down the geometry to what's visible:
UPDATE seg_extracts1 SET geog_gen = ST_Line_Substring(geog_gen::geometry, GREATEST((ref_begin - min_frm_dfo) / (max_to_dfo - min_frm_dfo), 0), LEAST((ref_end - min_frm_dfo) / (max_to_dfo - min_frm_dfo), 1))
WHERE ST_GeometryType(geog_gen::geometry) = 'ST_LineString';

-- Persist the results:
ALTER TABLE uniform_segs_01mi ADD COLUMN geog geography;
UPDATE uniform_segs_01mi AS u
SET geog = s.geog_gen
FROM seg_extracts1 AS s
WHERE u.roadway_gid = s.roadway_gid
  AND u.ref_begin = s.ref_begin;
```

Then, create a view that links with those representative segments:
```sql
CREATE OR REPLACE VIEW uniform_segs_01mi_data AS
  SELECT f.gid, ref_begin, ref_end, seg_count, seg_total, total_length,
    closest_frm_dfo, overlap, frm_dfo, f_system, spd_max, hwy_des1,
    row_w_usl, num_lanes, med_wid, med_type, s_wid_i, s_wid_o, s_type_i,
    s_type_o, dvmt, adt_adj, trk_aadt_p, u.geog
  FROM uniform_segs_01mi u, roadway_inv f
  WHERE f.gid = roadway_gid::numeric
    AND closest_frm_dfo = frm_dfo;
```

### Part 3: Mapping Crashes to Uniform Segments
This part follows largely the uniform segments process, as well. We only look at nearest crashes because the segment size is fairly small, and to not have nearest creates a ton of extra matches.

To make the matchup table:
```sql
CREATE TABLE crash_buf_01mi (
  roadway_gid integer,
  frm_dfo numeric,
  ref_begin real,
  crash_id integer,
  distance real,
  lin_ref real,
  points_kabco integer,
  nearest boolean DEFAULT TRUE,
  PRIMARY KEY (crash_id, roadway_gid)
);

INSERT INTO crash_buf_01mi (roadway_gid, frm_dfo, ref_begin, crash_id, distance, lin_ref, points_kabco)
  SELECT cb.roadway_gid, cb.frm_dfo, u.ref_begin, cb.crash_id, cb.distance, cb.lin_ref,
    CASE WHEN c.crash_sev_id IN (1, 4) THEN 7
         WHEN c.crash_sev_id IN (0, 2, 3, 5) THEN 1
         ELSE 0 END AS points_kabco
    FROM crash_buf_100 cb, uniform_segs_01mi u, share_crash c
    WHERE cb.roadway_gid = u.roadway_gid
      AND (u.seg_count = 1 AND cb.lin_ref = u.ref_begin
        OR cb.lin_ref > u.ref_begin AND cb.lin_ref <= u.ref_end)
      AND cb.nearest AND cb.crash_id = c.crash_id;
```

This creates the statistics table:
```sql
CREATE TABLE crash_stats_seg_01mi (
  roadway_gid integer,
  ref_begin real,
  count_all_nearest integer NOT NULL DEFAULT 0,
  count_ped_nearest integer NOT NULL DEFAULT 0,
  count_pf_nearest integer NOT NULL DEFAULT 0,
  count_all_nonint integer NOT NULL DEFAULT 0,
  count_ped_nonint integer NOT NULL DEFAULT 0,
  count_pf_nonint integer NOT NULL DEFAULT 0,
  count_ints_crossed integer NOT NULL DEFAULT 0,
  dist_school real,
  dist_hospital real,
  dist_transit real,
  count_transit_025mi real,
  sidewalk_len_vis real NOT NULL DEFAULT 0,
  sidewalk_len_inv real NOT NULL DEFAULT 0,
  ped_density real,
  ped_ranking integer,
  pts_allni_kabco integer,
  pts_pedni_kabco integer,
  seg_length real,
  PRIMARY KEY (roadway_gid, ref_begin)
);

-- Initialization:
INSERT INTO crash_stats_seg_01mi (roadway_gid, ref_begin, seg_length)
  SELECT roadway_gid, ref_begin, ref_end - ref_begin
    FROM uniform_segs_01mi;

-- count_all_nearest:
WITH r AS (
  SELECT roadway_gid, ref_begin, COUNT(1) crash_count
  FROM crash_buf_01mi c, ped_activity p
  WHERE nearest
    AND c.crash_id = p.crash_id
  GROUP BY roadway_gid, ref_begin
)
UPDATE crash_stats_seg_01mi
SET count_all_nearest = r.crash_count
FROM r
WHERE crash_stats_seg_01mi.roadway_gid = r.roadway_gid
  AND crash_stats_seg_01mi.ref_begin = r.ref_begin;

-- count_ped_nearest:
WITH r AS (
  SELECT roadway_gid, ref_begin, COUNT(1) crash_count
  FROM crash_buf_01mi c, ped_activity p
  WHERE nearest
    AND c.crash_id = p.crash_id
	AND p.ped_crash
  GROUP BY roadway_gid, ref_begin
)
UPDATE crash_stats_seg_01mi
SET count_ped_nearest = r.crash_count
FROM r
WHERE crash_stats_seg_01mi.roadway_gid = r.roadway_gid
  AND crash_stats_seg_01mi.ref_begin = r.ref_begin;

-- count_pf_nearest:
WITH r AS (
  SELECT roadway_gid, ref_begin, COUNT(1) crash_count
  FROM crash_buf_01mi c, ped_activity p
  WHERE nearest
    AND c.crash_id = p.crash_id
	AND p.ped_fatal > 0
  GROUP BY roadway_gid, ref_begin
)
UPDATE crash_stats_seg_01mi
SET count_pf_nearest = r.crash_count
FROM r
WHERE crash_stats_seg_01mi.roadway_gid = r.roadway_gid
  AND crash_stats_seg_01mi.ref_begin = r.ref_begin;

-- count_all_nonint:
WITH r AS (
  SELECT roadway_gid, ref_begin, COUNT(1) crash_count, SUM(points_kabco) sum_kabco
  FROM crash_buf_01mi c, ped_activity p, share_crash cr
  WHERE nearest
    AND c.crash_id = p.crash_id
    AND cr.at_intrsct_fl <> 'Y'
    AND cr.crash_id = c.crash_id
  GROUP BY roadway_gid, ref_begin
)
UPDATE crash_stats_seg_01mi
SET count_all_nonint = r.crash_count, pts_allni_kabco = r.sum_kabco
FROM r
WHERE crash_stats_seg_01mi.roadway_gid = r.roadway_gid
  AND crash_stats_seg_01mi.ref_begin = r.ref_begin;

-- count_ped_nonint:
WITH r AS (
  SELECT roadway_gid, ref_begin, COUNT(1) crash_count, SUM(points_kabco) sum_kabco
  FROM crash_buf_01mi c, ped_activity p, share_crash cr
  WHERE nearest
    AND c.crash_id = p.crash_id
    AND p.ped_crash
    AND cr.at_intrsct_fl <> 'Y'
    AND cr.crash_id = c.crash_id
  GROUP BY roadway_gid, ref_begin
)
UPDATE crash_stats_seg_01mi
SET count_ped_nonint = r.crash_count, pts_pedni_kabco = r.sum_kabco
FROM r
WHERE crash_stats_seg_01mi.roadway_gid = r.roadway_gid
  AND crash_stats_seg_01mi.ref_begin = r.ref_begin;

-- count_pf_nonint:
WITH r AS (
  SELECT roadway_gid, ref_begin, COUNT(1) crash_count
  FROM crash_buf_01mi c, ped_activity p, share_crash cr
  WHERE nearest
    AND c.crash_id = p.crash_id
	AND p.ped_fatal > 0
    AND cr.at_intrsct_fl <> 'Y'
    AND cr.crash_id = c.crash_id
  GROUP BY roadway_gid, ref_begin
)
UPDATE crash_stats_seg_01mi
SET count_pf_nonint = r.crash_count
FROM r
WHERE crash_stats_seg_01mi.roadway_gid = r.roadway_gid
  AND crash_stats_seg_01mi.ref_begin = r.ref_begin;
```

### Ranking the Crash Density

We want to see which are the "worst corridors" for a certain crash type among all corridors. Make another table, get a new density measurement, and then rank:

```sql
-- Density calculation
UPDATE crash_stats_seg_01mi
  SET ped_density = count_ped_nearest / seg_length
  WHERE seg_length >= 0.05;

-- Ranking based on density
WITH q AS (
  SELECT roadway_gid, ref_begin, ped_density
  FROM crash_stats_seg_01mi
  WHERE ped_density IS NOT NULL
    AND ped_density > 0
), r AS (
  SELECT roadway_gid, ref_begin,
    row_number() OVER (ORDER BY ped_density DESC) AS ranking
  FROM q
)
UPDATE crash_stats_seg_01mi AS csp
  SET ped_ranking = r.ranking
  FROM r
  WHERE csp.roadway_gid = r.roadway_gid
    AND csp.ref_begin = r.ref_begin;

\copy crash_stats_seg_01mi TO '~/pedcrash/crash_stats_seg_01mi.csv' DELIMITER ',' CSV HEADER;
```

### Visualizing the Crash Stats

This view helps in visualizing the crash stats results along with roadway characteristics from the TxDOT Roadway Geometry:

```sql
CREATE VIEW crash_segs_01mi_peds_geom AS
  SELECT u.roadway_gid, u.ref_begin, u.ref_end, seg_count, seg_total, total_length,
    closest_frm_dfo, overlap,
    count_all_nearest, count_ped_nearest, count_pf_nearest, count_all_nonint, count_ped_nonint, count_pf_nonint,
    ped_density, ped_ranking, pts_allni_kabco, pts_pedni_kabco, csp.seg_length, frm_dfo, f_system, spd_max, hwy_des1,
    row_w_usl, num_lanes, med_wid,
    med_type, s_wid_i, s_wid_o, s_type_i, s_type_o, dvmt, adt_adj, trk_aadt_p, u.geog
  FROM uniform_segs_01mi u, roadway_inv f, crash_stats_seg_01mi csp
  WHERE f.gid = u.roadway_gid::numeric
    AND u.roadway_gid = csp.roadway_gid
    AND u.ref_begin = csp.ref_begin
    AND closest_frm_dfo = frm_dfo;

\copy (SELECT roadway_gid, ref_begin, ref_end, seg_count, seg_total, total_length, closest_frm_dfo, overlap, count_all_nearest, count_ped_nearest, count_pf_nearest, count_all_nonint, count_ped_nonint, count_pf_nonint, ped_density, ped_ranking, pts_allni_kabco, pts_pedni_kabco, seg_length, frm_dfo, f_system, spd_max, hwy_des1, row_w_usl, num_lanes, med_wid, med_type, s_wid_i, s_wid_o, s_type_i, s_type_o, dvmt, adt_adj, trk_aadt_p FROM crash_segs_01mi_peds_geom) TO '~/pedcrash/crash_segs_01mi_peds.csv' DELIMITER ',' CSV HEADER;
```

Extracting out a Shapefile of that stats table:

```bash
mkdir -p crash_segs_01mi_peds_geom
pgsql2shp -f ./crash_segs_01mi_peds_geom/crash_segs_01mi_peds_geom.shp -h localhost -p 5432 -u **** -P ***** pedcrash crash_segs_01mi_peds_geom
zip -r -p crash_segs_01mi_peds_geom.zip crash_segs_01mi_peds_geom
```

### Dumping out the Crash Matchup

This view creates an annotation of each crash that's matched up with the 0.1-mile segments. This is inspired by the intersections matchup.

> **NOTE:** Edit this view as necessary to add in extra data for convenience.

```sql
CREATE VIEW crash_matchup_01mi AS
  SELECT cb.*, c.crash_date, c.crash_fatal_fl = 'Y' AS crash_fatal_fl, c.at_intrsct_fl = 'Y' AS at_intersct_fl,
    c.thousand_damage_fl = 'Y' AS thousand_damage_fl, p.ped_crash, c.rpt_city_id, c.rpt_cris_cnty_id
  FROM crash_buf_01mi cb, share_crash c, ped_activity p
  WHERE cb.crash_id = c.crash_id
    AND cb.crash_id = p.crash_id;

-- It would be possible to include city and county names by making a join from c.rpt_city_id = lci.city_id
-- AND c.rpt_cris_cnty_id = lco.cnty_id using tables lkp_city AS lci, lkp_cnty AS lco.

\copy (SELECT * FROM crash_matchup_01mi) TO '~/pedcrash/crash_matchup_01mi.csv' DELIMITER ',' CSV HEADER;
```

## Revisiting Matchup and Intersections

> **TODO:** Is this needed any longer?

For performing analyses with midblock crossings and uniform segments, a derived matchup table is to be created that can be aggregated for analysis purposes. Only the nearest crashes will be represented here. This is the table definition:

```sql
CREATE TABLE crash_int_nearest_01mi (
  crash_id integer REFERENCES share_crash(crash_id),
  roadway_gid integer,
  ref_begin real,
  lin_ref real,
  seg_distance real,
  nearest_int integer,
  nearest_int_dist real,
  at_intrsct boolean,
  ped_crash boolean,
  ped_fatal integer,
  PRIMARY KEY (crash_id, roadway_gid)
);
```

To populate it, we'll need to draw from a variety of tables. We'll first not deal with nearest intersections. Only records that have segments that were matched within 100m will appear in this table.

```sql
INSERT INTO crash_int_nearest_01mi (crash_id, roadway_gid, ref_begin, lin_ref,
    seg_distance, at_intrsct, ped_crash, ped_fatal)
  SELECT sc.crash_id, cb1.roadway_gid, cb1.ref_begin, cb1.lin_ref,
      cb1.distance, sc.at_intrsct_fl = 'Y', pa.ped_crash, pa.ped_fatal
    FROM share_crash sc, crash_buf_01mi cb1, ped_activity pa
    WHERE sc.crash_id = cb1.crash_id
      AND sc.crash_id = pa.crash_id
      AND cb1.nearest;
```

Now, we'll go back and fill in for the nearest intersections where matches exist in "crash_int_matchup":

```sql
UPDATE crash_int_nearest_01mi AS cin1 
  SET nearest_int = cim.int_id,
      nearest_int_dist = cim.distance
  FROM crash_int_matchup AS cim
  WHERE cin1.crash_id = cim.crash_id;
```

Finally, to extract:

```sql
\copy crash_int_nearest_01mi TO '~/crash_int_nearest_01mi.csv' DELIMITER ',' CSV HEADER;
```
