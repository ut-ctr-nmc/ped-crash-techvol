# BCR Corridors

To perform an effective BCR analysis, a "corridor" representation of the worst segments and intersections is needed. The solution is to create groupings of combinations of intersections and 0.1-mile segments along individual high-ranking roadways, using the KABCO scores.

## Method

### Preparation

To prepare for this, the entire 2018 version of the TxDOT Roadway Inventory was resampled at 0.1-mile increments to assist in the process of building up corridors. This produced about 3.4 million segments available for analysis. Along with this, CRIS crash records were matched with each 0.1-mile incremental segment according to these criteria:

* The crash record has geographic coordinates. (About 83% of all crash records satisfy this criterion.)
* The record is *not* marked to have occurred at an intersection. (That's about 72% of all records.)
* The record is classified as a pedestrian-related crash. (About 1.4% of all crash records are determined to be predominantly pedestrian-related.)
* The record's geographic coordinates sit within 329 feet (100 meters) of a TxDOT Roadway Inventory segment.
* Once a crash is matched with the nearest segment, it is not eligible to be matched to any other segments.

The end result is that 41,131 crash records (0.7% of all of CRIS within the 2010-2019 analysis period) are matched to roadway segments for the purpose of finding and ranking crash-prone corridors for BCR analysis.

In a related effort, intersections were derived from OpenStreetMap and matched to corresponding locations within TxDOT Roadway Inventory. (TxDOT Roadway Inventory on its own does not explicitly represent intersections.) Similar to the process used on segments, CRIS crash records were matched to these intersections according to these criteria:

* The crash record has geographic coordinates, *is* marked to occur at an intersection, and is classified as a pedestrian-related crash.
* The record's geographic coordinates sit within 329 feet (100 meters) of a derived OpenStreetMap intersection.
* Once a crash is matched with the nearest intersection, it is not eligible to be matched to any other intersection.

This produces 16,502 crash records available for the purpose of finding and raking crash-prone corridors.

### Finding Corridors

These 0.1-mile segments, OpenStreetMap-derived intersections, and selected crash records are then used as inputs for a process of building up analysis corridors. The algorithm for performing this follows a "greedy" pattern of picking up the worst intersections first and building off of them:

* Pick the next worst intersection in terms of the number of pedestrian-related crashes that are matched with it
* For each cross street, "walk" down each direction of eligible 0.1-mile segments from the starting intersection until:
  * 3 successive segments and intersections that coincide with them each have fewer than 5 pedestrian-related crashes, or
  * The end of the street is reached.
* Record all of the segments and intersections traversed as a new corridor. Include the cumulative KABCO score for all of the ped crashes therein, and make those segments ineligible for inclusion in future corridors.
* Loop again until no more intersection/cross street combinations remain.
* Rank all of the corridors according to decreasing KABCO score.

At the completion of this algorithm, 7,945 corridors were discovered. However, corridors beyond the 100 highest-scoring are considered insignificant for this study, as most are comprised of a small handful of intersection. As a result, 1,274 intersections and 1,116 0.1-mile segments comprise the significant corridors, encompassing 4,295 crash records.

## Finding the AADT

The resulting spreadsheet had tabs for corridors, intersections, and segments. While identifiers are present, the AADT values are not. They need to be retrieved from the representative segments in the TxDOT Roadway Inventory. Fortunately, the AADT values are already isolated in easy-to-retrieve locations.

### Intersections

The AADT values for intersections on the representative major and minor approaches are found in the `ints_osm_appch_ri` view (`adt_adj` column).

#### Part 1: The "Corridors" Worksheet

On the "Corridors" worsheet, the AADT needs to be captured for the major approach on the corresponding seed intersection. This is a representative sampled measure for the corridor.

Isolate the `corr_id` and `int_id` fields on the "Corridors" worksheet. Then, import, query, export, and paste back in the AADT values.

```sql
CREATE TEMP TABLE bcr_seeds (
  corr_id integer PRIMARY KEY,
  int_id integer,
  aadt integer
);

\copy bcr_seeds (corr_id, int_id) FROM '~/pedcrash/bcr_seeds.csv' DELIMITER ',' CSV HEADER;

UPDATE bcr_seeds AS bs
  SET aadt = ioar.adt_adj
  FROM ints_osm_appch_ri AS ioar
  WHERE bs.int_id = ioar.int_id
    AND ioar.major;

\copy (SELECT corr_id, int_id, aadt FROM bcr_seeds ORDER BY corr_id) TO '~/pedcrash/bcr_seeds_o.csv' DELIMITER ',' CSV HEADER;
```

#### Part 2: The "Intersections" Worksheet

On the "Intersections" worksheet, isolate the `int_id`, `corr_id`, and `kabco_pts` fields. Then, import, query, export, and paste back in the AADT values.

```sql
CREATE TABLE bcr_ints (
  corr_id integer,
  int_id integer,
  kabco_pts real,
  aadt1 integer,
  aadt2 integer,
  PRIMARY KEY (corr_id, int_id)
);

\copy bcr_ints (corr_id, int_id, kabco_pts) FROM '~/pedcrash/bcr_ints.csv' DELIMITER ',' CSV HEADER;

-- Do two operations because there could be the oddball chance that some intersection
-- doesn't have a minor approach:
UPDATE bcr_ints AS bi
  SET aadt1 = ioar.adt_adj
  FROM ints_osm_appch_ri AS ioar
  WHERE bi.int_id = ioar.int_id
    AND ioar.major;
UPDATE bcr_ints AS bi
  SET aadt2 = ioar.adt_adj
  FROM ints_osm_appch_ri AS ioar
  WHERE bi.int_id = ioar.int_id
    AND NOT ioar.major;

\copy (SELECT corr_id, int_id, kabco_pts, aadt1, aadt2 FROM bcr_ints ORDER BY kabco_pts DESC NULLS LAST, corr_id, int_id) TO '~/pedcrash/bcr_ints_o.csv' DELIMITER ',' CSV HEADER;
```

### Segments

The representative AADT for the 0.1-mile segments can be found from the `crash_segs_01mi_peds` view.

On the "Segments" worksheet, isolate the `corr_id`, `roadway_gid`, `ref_begin`, and `kabco_pts` fields. As before, import, query, export, and paste back in the AADT values.

```sql
CREATE TABLE bcr_segs (
  corr_id integer,
  roadway_gid integer,
  ref_begin real,
  kabco_pts real,
  aadt integer,
  PRIMARY KEY (corr_id, roadway_gid, ref_begin)
);

\copy bcr_segs (corr_id, roadway_gid, ref_begin, kabco_pts) FROM '~/pedcrash/bcr_segs.csv' DELIMITER ',' CSV HEADER;

WITH q AS (
  SELECT roadway_gid, ref_begin, adt_adj
  FROM crash_segs_01mi_peds_geom
)
UPDATE bcr_segs AS bs
  SET aadt = q.adt_adj
  FROM q
  WHERE bs.roadway_gid = q.roadway_gid
    AND bs.ref_begin::numeric = q.ref_begin::numeric;

-- TODO: We need to store ref_begin, etc. as numeric so that we can perform
-- equality matches better.

\copy (SELECT corr_id, roadway_gid, ref_begin, kabco_pts, aadt FROM bcr_segs ORDER BY kabco_pts DESC NULLS LAST, corr_id) TO '~/pedcrash/bcr_segs_o.csv' DELIMITER ',' CSV HEADER;
```

## Finding Contributing Crashes

It is necessary to find all crashes that contribute to each cluster. This explores queries that can assemble together the necessary results, tying pedestrian crashes to each cluster ID.

```sql
CREATE TABLE bcr_crashes AS
WITH q AS (
    SELECT b.corr_id, c.crash_id, s.crash_date, s.crash_time
      FROM bcr_ints b, crash_int_osm_nearest c, share_crash s
      WHERE b.int_id = c.int_id
        AND c.crash_id = s.crash_id
        AND c.ped_crash AND c.at_intersct_fl
        AND b.corr_id <= 500
    UNION
    SELECT b.corr_id, c.crash_id, s.crash_date, s.crash_time
      FROM bcr_segs b, crash_buf_01mi c, share_crash s, ped_activity p
      WHERE b.roadway_gid = c.roadway_gid
        AND b.ref_begin::numeric = c.ref_begin::numeric
        AND c.crash_id = p.crash_id
        AND c.crash_id = s.crash_id
        AND p.ped_crash AND s.at_intrsct_fl <> 'Y'
        AND b.corr_id <= 500
)
SELECT DISTINCT * FROM q ORDER BY corr_id, crash_id;

\copy bcr_crashes TO '~/pedcrash/bcr_ped_crashes_o.csv' DELIMITER ',' CSV HEADER;
```

### Notating Requested Crash Records

Add date field to `bcr_crashes` to keep track of when a request is made for the CR-3 record:

```sql
ALTER TABLE bcr_crashes ADD COLUMN requested date;

CREATE TEMP TABLE req_recs (
  crash_id integer
);
\copy req_recs (crash_id) FROM '~/pedcrash/file_list.txt';

WITH q AS (
  SELECT crash_id, '2021-04-05'::date AS req_date FROM req_recs
)
UPDATE bcr_crashes bc
SET requested = req_date
FROM q
WHERE q.crash_id = bc.crash_id;
```

### Exporting Crashes for Analysis (TO REFINE)

```sql
CREATE TEMP VIEW ped_crash_data_simple_c AS
SELECT bc.corr_id, c.crash_id, c.crash_date, c.crash_time, c.crash_fatal_fl = 'Y' crash_fatal,
  c.at_intrsct_fl = 'Y' at_intersct, c.thousand_damage_fl = 'Y' thousand_damage,
  c.light_cond_id, c.wthr_cond_id, c.traffic_cntl_id, c.harm_evnt_id, c.intrsct_relat_id,
  c.crash_sev_id, c.crash_speed_limit, c.street_name, lc.city_name, c.crash_fatal_fl,
  c.day_of_week = 'SAT' OR c.day_of_week = 'SUN' OR c.day_of_week = 'FRI' AND c.crash_time >= '21:00:00' OR c.day_of_week = 'MON' AND c.crash_time < '03:00:00' AS weekend,
  requested, ST_Y(c.location::geometry) lat, ST_X(c.location::geometry) lon
FROM bcr_crashes bc, share_crash c
LEFT JOIN lkp_city lc USING (city_id)
WHERE c.crash_id = bc.crash_id
ORDER BY bc.corr_id, c.crash_id;

\copy (SELECT * FROM ped_crash_data_simple_c ORDER BY corr_id, crash_id) TO '~/pedcrash/ped_crash_data_simple_c.csv' DELIMITER ',' CSV HEADER;
```

### Crash Records with No Address

Part of the ongoing analysis is to better understand how many crashes involved pedestrians that have no home address. It could be surmised that many would be homeless, or be unwilling to divulge information because of undocumented status.


