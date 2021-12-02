# <!-- omit in toc -->Uniform Segmentation of Roadway Geometry

This document describes the methodology used to create fairly uniform segments.
- [First Attempt](#first-attempt)
  - [Part 1: Proposing Segments](#part-1-proposing-segments)
    - [Case 1: Segment is < 1.25 miles](#case-1-segment-is--125-miles)
    - [Case 2: Segment is < 2.5 miles](#case-2-segment-is--25-miles)
    - [Case 3: Segment is >= 2.5 miles](#case-3-segment-is--25-miles)
  - [Part 2: Extracting Relevant Data](#part-2-extracting-relevant-data)
    - [Detail 1: Fundamental parameters](#detail-1-fundamental-parameters)
  - [Part 2b: Extracting Geometry](#part-2b-extracting-geometry)
  - [Part 3: Mapping Crashes to Uniform Segments](#part-3-mapping-crashes-to-uniform-segments)
  - [Ranking the Crash Density](#ranking-the-crash-density)
  - [Visualizing the Crash Stats](#visualizing-the-crash-stats)
- [Visualizing the crash_seg_1mi_peds Ranking](#visualizing-the-crash_seg_1mi_peds-ranking)
- [Revisiting Matchup and Intersections](#revisiting-matchup-and-intersections)
- [Midblock Crashes and Street Characteristics](#midblock-crashes-and-street-characteristics)
  - [Approach #1: Mile-Long Uniform Segments](#approach-1-mile-long-uniform-segments)
  - [Approach #2: 1/10-Mile Long Uniform Segments](#approach-2-110-mile-long-uniform-segments)

## First Attempt
In this first attempt, the following objectives will be considered:

* Chunk up TxDOT Roadway Inventory segments (total geometry representing each GID) into 1-mile long segments. Allow for at least half a mile on the ends.
* Shorter segments remain the same length
* Maintain linear references only
* Maintain Roadway Inventory metrics for each segment by weight of values in underlying segments that overlap

### Part 1: Proposing Segments
Here we propose the division of segments, keeping to 1-mile segments and allowing for some flexibility at the ends. Divisions will be established centered along the entire segment length that leaves no segment more than 1.25 miles long.

First, check for discontinuities:
```sql
-- This currently returns zero results, which means there aren't any discontinuities.
WITH q AS (
  SELECT gid, frm_dfo, to_dfo, ROW_NUMBER() OVER (ORDER BY gid, frm_dfo) id
  FROM roadway_inv
)
SELECT r1.gid, r1.frm_dfo, r1.to_dfo, r2.frm_dfo
  FROM q r1, q r2
  WHERE r1.gid = r2.gid
    AND r1.to_dfo < r2.frm_dfo
    AND r2.id = r1.id + 1;
```

This is the table definition for the matchup:
```sql
CREATE TABLE uniform_segs_1mi (
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

#### Case 1: Segment is < 1.25 miles
The segment shall be kept as-is.
```sql
WITH q AS (
  SELECT gid, SUM(len_sec) total_length, MIN(frm_dfo) ref_begin, MAX(to_dfo) ref_end FROM roadway_inv GROUP BY gid
), r AS (
  SELECT gid, total_length, ref_begin, ref_end FROM q WHERE total_length < 1.25
)
INSERT INTO uniform_segs_1mi
  (roadway_gid, ref_begin, ref_end, seg_count, seg_total, total_length)
SELECT gid, ref_begin, ref_end, 1, 1, total_length FROM r;
```

#### Case 2: Segment is < 2.5 miles
The segments will be split into two.
```sql
WITH q AS (
  SELECT gid, SUM(len_sec) total_length, MIN(frm_dfo) ref_begin, MAX(to_dfo) ref_end FROM roadway_inv GROUP BY gid
), r AS (
  SELECT gid, total_length, ref_begin, ref_end, GENERATE_SERIES(0, 1) g_id
    FROM q WHERE total_length >= 1.25 AND total_length < 2.5
)
INSERT INTO uniform_segs_1mi
  (roadway_gid, ref_begin, ref_end, seg_count, seg_total, total_length)
SELECT gid,
    ref_begin + (ref_end - ref_begin) * g_id / 2,
    ref_begin + (ref_end - ref_begin) * (g_id + 1) / 2,
    g_id + 1, 2, total_length FROM r;
```

#### Case 3: Segment is >= 2.5 miles
The segments will have 1-mile chunks in between, with ends that are no less than 0.75 miles and no more than 1.25 miles.
```sql
WITH q AS (
  SELECT gid, SUM(len_sec) total_length, MIN(frm_dfo) ref_begin, MAX(to_dfo) ref_end FROM roadway_inv GROUP BY gid
), r AS (
  SELECT gid, total_length, ref_begin, ref_end, GENERATE_SERIES(0, FLOOR(total_length - 1.5)::integer + 1) g_id
    FROM q WHERE total_length >= 2.5
)
INSERT INTO uniform_segs_1mi
  (roadway_gid, ref_begin, ref_end, seg_count, seg_total, total_length)
SELECT gid,
    CASE WHEN g_id = 0 THEN ref_begin ELSE ref_begin + (total_length - FLOOR(total_length - 1.5)) / 2 + g_id - 1 END,
    CASE WHEN g_id = FLOOR(total_length - 1.5) + 1 THEN ref_end ELSE ref_begin + (total_length - FLOOR(total_length - 1.5)) / 2 + g_id END,
    g_id + 1,
    FLOOR(total_length - 1.5) + 2,
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
    FROM uniform_segs_1mi us1, roadway_inv r
    WHERE us1.roadway_gid = r.gid
      AND NOT (ref_begin > to_dfo OR ref_end < frm_dfo)
  ORDER BY r.gid ASC, ref_begin ASC, LEAST(to_dfo, ref_end) - GREATEST(frm_dfo, ref_begin) DESC
)
UPDATE uniform_segs_1mi us1
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
  SELECT roadway_gid, ref_begin, ref_end, frm_dfo, to_dfo, geog
  FROM uniform_segs_1mi, roadway_inv
  WHERE roadway_gid = gid
    AND to_dfo >= ref_begin::numeric
    AND frm_dfo <= ref_end::numeric
  ORDER BY roadway_gid, ref_begin, frm_dfo
)
SELECT q.roadway_gid, q.ref_begin, q.ref_end, array_agg(q.geog) AS geog_array, min(frm_dfo::float) AS min_frm_dfo, max(to_dfo::float) AS max_to_dfo
FROM q
GROUP BY q.roadway_gid, q.ref_begin;

-- Try to convert to LineString so that we can do linear referencing:
ALTER TABLE seg_extracts1 ADD COLUMN geog_multi geography(multilinestring);
ALTER TABLE seg_extracts1 ADD COLUMN geog_gen geography;
UPDATE seg_extracts1 SET geog_multi = ST_MakeValid(ST_Union(geog_array::geometry[]));
UPDATE seg_extracts1 SET geog_gen = ST_LineMerge(geog_multi::geometry);

-- There's 50 records that couldn't be LineStrings. See if we can coerce them:
UPDATE seg_extracts1 SET geog_gen = ST_LineMerge(ST_SnapToGrid(geog_gen::geometry, 0.001))
WHERE ST_GeometryType(geog_gen::geometry) <> 'ST_LineString';
-- That fixed 14 of them. 

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
ALTER TABLE uniform_segs_1mi ADD COLUMN geog geography;
UPDATE uniform_segs_1mi AS u
SET geog = s.geog_gen
FROM seg_extracts1 AS s
WHERE u.roadway_gid = s.roadway_gid
  AND u.ref_begin = s.ref_begin;
```

Then, create a view that links with those representative segments:
```sql
CREATE OR REPLACE VIEW uniform_segs_1mi_data AS
  SELECT f.gid, ref_begin, ref_end, seg_count, seg_total, total_length, closest_frm_dfo,
    overlap, frm_dfo, f_system, spd_max, hwy_des1, row_w_usl, num_lanes, med_wid, med_type,
    s_wid_i, s_wid_o, s_type_i, s_type_o, dvmt, adt_adj, trk_aadt_p, sec_bic, school_zn,
    aces_ctrl, clmb_ps_la, accel_dece, k_fac, s_use_i, desgn_yr, rt_turn_la,
    lt_turn_la, lane_width, peak_prkg, u.geog
  FROM uniform_segs_1mi u, roadway_inv f
  WHERE f.gid = roadway_gid::numeric
    AND closest_frm_dfo = frm_dfo;
```

### Part 3: Mapping Crashes to Uniform Segments
Here we look at the linear references of crashes that were matched to the Roadway Inventory, and identify which uniform segments they map to. Then, we count the number of crashes there are for each segment.

To make the matchup table:
```sql
CREATE TABLE crash_buf_1mi (
  roadway_gid integer,
  frm_dfo numeric,
  ref_begin real,
  crash_id integer,
  distance real,
  lin_ref real,
  points_kabco integer,
  nearest boolean DEFAULT FALSE,
  PRIMARY KEY (crash_id, roadway_gid)
);

INSERT INTO crash_buf_1mi
  SELECT cb.roadway_gid, cb.frm_dfo, u.ref_begin, cb.crash_id, cb.distance, cb.lin_ref, cb.nearest
    FROM crash_buf_100 cb, uniform_segs_1mi u
    WHERE cb.roadway_gid = u.roadway_gid
      AND (u.seg_count = 1 AND cb.lin_ref = u.ref_begin
        OR cb.lin_ref > u.ref_begin AND cb.lin_ref <= u.ref_end);

UPDATE crash_buf_1mi a
  SET points_kabco = CASE WHEN c.crash_sev_id IN (1, 4) THEN 7
                          WHEN c.crash_sev_id IN (0, 2, 3, 5) THEN 1
                          ELSE 0 END
  FROM share_crash c
  WHERE a.crash_id = c.crash_id;
```

This creates the statistics table:
```sql
CREATE TABLE crash_stats_seg_1mi (
  roadway_gid integer,
  ref_begin real,
  count_50_all integer NOT NULL DEFAULT 0,
  count_50_ped integer NOT NULL DEFAULT 0,
  count_50_pedfatal integer NOT NULL DEFAULT 0,
  count_nearest_all integer NOT NULL DEFAULT 0,
  count_nearest_ped integer NOT NULL DEFAULT 0,
  count_nearest_pedfatal integer NOT NULL DEFAULT 0,
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
  pts_allni_kabco integer,
  pts_pedni_kabco integer,
  seg_length real,
  PRIMARY KEY (roadway_gid, ref_begin)
);

-- count_50_all:
INSERT INTO crash_stats_seg_1mi (roadway_gid, ref_begin, count_50_all, seg_length)
  SELECT cb.roadway_gid, cb.ref_begin, COUNT(1) count_50_all, MIN(u.ref_end - cb.ref_begin) seg_length
    FROM crash_buf_1mi cb, uniform_segs_1mi u
    WHERE distance <= 50
      AND cb.roadway_gid = u.roadway_gid
      AND cb.ref_begin = u.ref_begin
    GROUP BY cb.roadway_gid, cb.ref_begin;

-- count_50_ped:
WITH r AS (
  SELECT roadway_gid, ref_begin, COUNT(1) crash_count
  FROM crash_buf_1mi c, ped_activity p
  WHERE distance <= 50
    AND c.crash_id = p.crash_id AND p.ped_crash
  GROUP BY roadway_gid, ref_begin
)
UPDATE crash_stats_seg_1mi
SET count_50_ped = r.crash_count
FROM r
WHERE crash_stats_seg_1mi.roadway_gid = r.roadway_gid
  AND crash_stats_seg_1mi.ref_begin = r.ref_begin;

-- count_50_pedfatal:
WITH r AS (
  SELECT roadway_gid, ref_begin, COUNT(1) crash_count
  FROM crash_buf_1mi c, ped_activity p
  WHERE distance <= 50
    AND c.crash_id = p.crash_id
	AND p.ped_fatal > 0
  GROUP BY roadway_gid, ref_begin
)
UPDATE crash_stats_seg_1mi
SET count_50_pedfatal = r.crash_count
FROM r
WHERE crash_stats_seg_1mi.roadway_gid = r.roadway_gid
  AND crash_stats_seg_1mi.ref_begin = r.ref_begin;

-- count_nearest_all:
WITH r AS (
  SELECT roadway_gid, ref_begin, COUNT(1) crash_count
  FROM crash_buf_1mi c
  WHERE nearest
  GROUP BY roadway_gid, ref_begin
)
UPDATE crash_stats_seg_1mi
SET count_nearest_all = r.crash_count
FROM r
WHERE crash_stats_seg_1mi.roadway_gid = r.roadway_gid
  AND crash_stats_seg_1mi.ref_begin = r.ref_begin;

-- count_nearest_ped:
WITH r AS (
  SELECT roadway_gid, ref_begin, COUNT(1) crash_count
  FROM crash_buf_1mi c, ped_activity p
  WHERE nearest
    AND c.crash_id = p.crash_id
	AND p.ped_crash
  GROUP BY roadway_gid, ref_begin
)
UPDATE crash_stats_seg_1mi
SET count_nearest_ped = r.crash_count
FROM r
WHERE crash_stats_seg_1mi.roadway_gid = r.roadway_gid
  AND crash_stats_seg_1mi.ref_begin = r.ref_begin;

-- count_nearest_pedfatal:
WITH r AS (
  SELECT roadway_gid, ref_begin, COUNT(1) crash_count
  FROM crash_buf_1mi c, ped_activity p
  WHERE nearest
    AND c.crash_id = p.crash_id
	AND p.ped_fatal > 0
  GROUP BY roadway_gid, ref_begin
)
UPDATE crash_stats_seg_1mi
SET count_nearest_pedfatal = r.crash_count
FROM r
WHERE crash_stats_seg_1mi.roadway_gid = r.roadway_gid
  AND crash_stats_seg_1mi.ref_begin = r.ref_begin;

-- count_all_nonint:
WITH r AS (
  SELECT roadway_gid, ref_begin, COUNT(1) crash_count, SUM(points_kabco) sum_kabco
  FROM crash_buf_1mi c, ped_activity p, share_crash cr
  WHERE nearest
    AND c.crash_id = p.crash_id
    AND cr.at_intrsct_fl <> 'Y'
    AND cr.crash_id = c.crash_id
  GROUP BY roadway_gid, ref_begin
)
UPDATE crash_stats_seg_1mi
SET count_all_nonint = r.crash_count, pts_allni_kabco = r.sum_kabco
FROM r
WHERE crash_stats_seg_1mi.roadway_gid = r.roadway_gid
  AND crash_stats_seg_1mi.ref_begin = r.ref_begin;

-- count_ped_nonint:
WITH r AS (
  SELECT roadway_gid, ref_begin, COUNT(1) crash_count, SUM(points_kabco) sum_kabco
  FROM crash_buf_1mi c, ped_activity p, share_crash cr
  WHERE nearest
    AND c.crash_id = p.crash_id
    AND p.ped_crash
    AND cr.at_intrsct_fl <> 'Y'
    AND cr.crash_id = c.crash_id
  GROUP BY roadway_gid, ref_begin
)
UPDATE crash_stats_seg_1mi
SET count_ped_nonint = r.crash_count, pts_pedni_kabco = r.sum_kabco
FROM r
WHERE crash_stats_seg_1mi.roadway_gid = r.roadway_gid
  AND crash_stats_seg_1mi.ref_begin = r.ref_begin;

-- count_pf_nonint:
WITH r AS (
  SELECT roadway_gid, ref_begin, COUNT(1) crash_count
  FROM crash_buf_1mi c, ped_activity p, share_crash cr
  WHERE nearest
    AND c.crash_id = p.crash_id
	AND p.ped_fatal > 0
    AND cr.at_intrsct_fl <> 'Y'
    AND cr.crash_id = c.crash_id
  GROUP BY roadway_gid, ref_begin
)
UPDATE crash_stats_seg_1mi
SET count_pf_nonint = r.crash_count
FROM r
WHERE crash_stats_seg_1mi.roadway_gid = r.roadway_gid
  AND crash_stats_seg_1mi.ref_begin = r.ref_begin;
```

### Ranking the Crash Density

We want to see which are the "worst corridors" for a certain crash type among all corridors. Make another table, get a new density measurement, and then rank:

```sql
CREATE TABLE crash_seg_1mi_peds (
  roadway_gid integer,
  ref_begin real,
  count_50_all integer NOT NULL DEFAULT 0,
  count_50_ped integer NOT NULL DEFAULT 0,
  count_50_pedfatal integer NOT NULL DEFAULT 0,
  ped_density real,
  ped_ranking integer DEFAULT 0,
  seg_length real,
  PRIMARY KEY (roadway_gid, ref_begin));

INSERT INTO crash_seg_1mi_peds (roadway_gid, ref_begin, count_50_all, count_50_ped, count_50_pedfatal, seg_length)
  SELECT roadway_gid, ref_begin, count_50_all, count_50_ped, count_50_pedfatal, seg_length
    FROM crash_stats_seg_1mi;

-- Density calculation
UPDATE crash_seg_1mi_peds
  SET ped_density = count_50_ped / seg_length
  WHERE seg_length >= 0.2;

-- Ranking based on density
WITH q AS (
  SELECT roadway_gid, ref_begin,
    row_number() OVER (ORDER BY ped_density DESC NULLS LAST) AS ranking
  FROM crash_seg_1mi_peds
)
UPDATE crash_seg_1mi_peds AS csp
  SET ped_ranking = q.ranking
  FROM q
  WHERE csp.roadway_gid = q.roadway_gid
    AND csp.ref_begin = q.ref_begin;
```

### Visualizing the Crash Stats

This view helps in visualizing the crash stats results:

```sql
CREATE OR REPLACE VIEW crash_stats_1mi_geom AS
  SELECT f.gid, u.ref_begin, u.ref_end, seg_count, seg_total, total_length,
    closest_frm_dfo, overlap,
    count_50_all, count_50_ped, count_50_pedfatal, count_nearest_all, count_nearest_ped, count_nearest_pedfatal, cs.seg_length,
    frm_dfo, f_system, spd_max, hwy_des1,
    row_w_usl, num_lanes, med_wid, med_type, s_wid_i, s_wid_o, s_type_i,
    s_type_o, dvmt, adt_adj, trk_aadt_p, u.geog
  FROM uniform_segs_1mi u, roadway_inv f, crash_stats_seg_1mi cs
  WHERE f.gid = u.roadway_gid::numeric
    AND u.roadway_gid = cs.roadway_gid
    AND u.ref_begin = cs.ref_begin
    AND closest_frm_dfo = frm_dfo;
```

Extracting out a Shapefile of that stats table:

```bash
mkdir -p crash_stats_1mi_geom
pgsql2shp -f ./crash_stats_1mi_geom/crash_stats_1mi_geom.shp -h localhost -p 5432 -u **** -P ***** pedcrash crash_stats_1mi_geom
zip -r -p crash_stats_1mi_geom.zip crash_stats_1mi_geom
```

## Visualizing the crash_seg_1mi_peds Ranking

```sql
CREATE OR REPLACE VIEW crash_segs_1mi_peds_geom AS
  SELECT f.gid, u.ref_begin, u.ref_end, seg_count, seg_total, total_length,
    closest_frm_dfo, overlap,
    count_50_all, count_50_ped, count_50_pedfatal, ped_density, ped_ranking, csp.seg_length,
    frm_dfo, f_system, spd_max, hwy_des1,
    row_w_usl, num_lanes, med_wid, med_type, s_wid_i, s_wid_o, s_type_i,
    s_type_o, dvmt, adt_adj, trk_aadt_p, u.geog
  FROM uniform_segs_1mi u, roadway_inv f, crash_seg_1mi_peds csp
  WHERE f.gid = u.roadway_gid::numeric
    AND u.roadway_gid = csp.roadway_gid
    AND u.ref_begin = csp.ref_begin
    AND closest_frm_dfo = frm_dfo;
```

Extracting out a Shapefile of that stats table:

```bash
mkdir -p crash_segs_1mi_peds_geom
pgsql2shp -f ./crash_segs_1mi_peds_geom/crash_segs_1mi_peds_geom.shp -h localhost -p 5432 -u **** -P ***** pedcrash crash_segs_1mi_peds_geom
zip -r -p crash_segs_1mi_peds_geom.zip crash_segs_1mi_peds_geom
```

## Revisiting Matchup and Intersections

Natalia Z. is needing to perform analyses with midblock crossings and uniform segments. A derived matchup table is to be created that can be aggregated for analysis purposes. Only the nearest crashes will be represented here. This is the table definition:

```sql
CREATE TABLE crash_int_nearest_1mi (
  crash_id integer REFERENCES share_crash(crash_id) PRIMARY KEY,
  roadway_gid integer,
  ref_begin real,
  lin_ref real,
  seg_distance real,
  nearest_int_osm integer,
  nearest_int_osm_dist real,
  at_intrsct boolean,
  ped_crash boolean,
  ped_fatal integer
);
```

To populate it, we'll need to draw from a variety of tables. We'll first not deal with nearest intersections. Only records that have segments that were matched within 100m will appear in this table.

```sql
INSERT INTO crash_int_nearest_1mi (crash_id, roadway_gid, ref_begin, lin_ref,
    seg_distance, at_intrsct, ped_crash, ped_fatal)
  SELECT sc.crash_id, cb1.roadway_gid, cb1.ref_begin, cb1.lin_ref,
      cb1.distance, sc.at_intrsct_fl = 'Y', pa.ped_crash, pa.ped_fatal
    FROM share_crash sc, crash_buf_1mi cb1, ped_activity pa
    WHERE sc.crash_id = cb1.crash_id
      AND sc.crash_id = pa.crash_id
      AND cb1.nearest;
```

Now, we'll go back and fill in for the nearest intersections where matches exist in "crash_int_matchup"; crashes not close to any intersections will remain "nearest_int = NULL":

```sql
UPDATE crash_int_nearest_1mi AS cin1 
  SET nearest_int_osm = cim.int_id,
      nearest_int_osm_dist = cim.distance
  FROM crash_int_osm_nearest AS cim
  WHERE cin1.crash_id = cim.crash_id;
```

Finally, to extract:

```sql
\copy crash_int_nearest_1mi TO '~/pedcrash/crash_int_nearest_1mi.csv' DELIMITER ',' CSV HEADER;
```

## Midblock Crashes and Street Characteristics

For Natalia Z.'s analysis, she needs to be able to understand what street characteristics are like in the general vicinity of midblock locations. One approach is to create shorter uniform segments and then return representative street characteristics. These would then be used with crashes that are reported to not be at an intersection. It had been discussed that quarter-mile uniform segments may work alright with it. Before generating the quarter-mile segments, an attempt is made to get stats from around the midpoints of the existing ~mile-long segments:

### Approach #1: Mile-Long Uniform Segments

While it may be possible to leverage some of the code used in the "ints_osm_approaches" and "ints_osm_appch_ri" tables for OpenStreetMap-inspired intersections, it is probably easier at this moment to just export out the "uniform_segs_1mi_data" table from above (doesn't include geometry):

```sql
\copy (SELECT gid, ref_begin, ref_end, seg_count, seg_total, total_length, closest_frm_dfo, overlap, frm_dfo, f_system, spd_max, hwy_des1, row_w_usl, num_lanes, med_wid, med_type, s_wid_i, s_wid_o, s_type_i, s_type_o, dvmt, adt_adj, trk_aadt_p, sec_bic, school_zn, aces_ctrl, clmb_ps_la, accel_dece, k_fac, s_use_i, desgn_yr, rt_turn_la, lt_turn_la, lane_width, peak_prkg FROM uniform_segs_1mi_data) TO '~/pedcrash/uniform_segs_1mi_data.csv' DELIMITER ',' CSV HEADER;
```

Or, if a shapefile is helpful:

```bash
mkdir -p ./uniform_segs_1mi_data
pgsql2shp -f ./uniform_segs_1mi_data/uniform_segs_1mi_data.shp -h localhost -p 5432 -u **** -P ***** pedcrash uniform_segs_1mi_data
zip -r -p uniform_segs_1mi_data.zip uniform_segs_1mi_data
```

### Approach #2: 1/10-Mile Long Uniform Segments

See the [uniform_seg_10.md](uniform_seg_10.md) document for the process to create 1/10-mile long segments.
