# <!-- omit in toc -->Analysis that Includes Sidewalks

This document addresses data needs that were idenfified by Natalia Z. concering 1-mile segments (or 0.1-mile segmenets) and sidewalks.

- [Inquiries](#inquiries)
  - [How do I filter around divided highway centerlines?](#how-do-i-filter-around-divided-highway-centerlines)
  - [How do I filter to on-system segments?](#how-do-i-filter-to-on-system-segments)
  - [How many intersections does 1-mile segment cross?](#how-many-intersections-does-1-mile-segment-cross)
  - [What's a convenient table that has lat, lon with intersections?](#whats-a-convenient-table-that-has-lat-lon-with-intersections)
  - [How to get segment centers?](#how-to-get-segment-centers)
  - [Getting distance to nearest school, hospital, and transit stop?](#getting-distance-to-nearest-school-hospital-and-transit-stop)
  - [How to get ped crash counts per segment for midblock?](#how-to-get-ped-crash-counts-per-segment-for-midblock)
  - [What's the difference between "at_intrsct_fl" and "intrsct_relat_id"?](#whats-the-difference-between-at_intrsct_fl-and-intrsct_relat_id)
  - [Finally, where's the sidewalks?](#finally-wheres-the-sidewalks)
- [Other Statistics for the Paper](#other-statistics-for-the-paper)
  - [Yearly/Total number of crashes at intersections?](#yearlytotal-number-of-crashes-at-intersections)
  - [Yearly/Total number of crashes at midblock segments](#yearlytotal-number-of-crashes-at-midblock-segments)
  - [Crashes by severity level intersections vs. midblock segments](#crashes-by-severity-level-intersections-vs-midblock-segments)

## Inquiries

This section addresses some questions that were brought up.

### How do I filter around divided highway centerlines?

By default, the TxDOT Roadway Inventory has the center of a divided highway labeled in `rdbd_id` of `roadway_inv`, also the first 2 characters of `ria_rte_id`. Where there is a pair of `LG` and `RG`, there is also the centerline, `KG`. Crash GPS coordinates that come with the CRIS records appear to mostly be visually snapped to the cetnerline. In [database.md](database.md), the query that fills out table `crash_buf_100` was already designed to *not* match crashes to `KG` if `LG` or `RG` exist. So, that should prevent double-counting on divided highways.

As an example, here's the count of all ped crashes that are matched to the left carriageway on divided highways:

```sql
SELECT COUNT(1)
FROM crash_buf_100 cb, roadway_inv ri, ped_activity p
WHERE cb.nearest AND cb.crash_id = p.crash_id AND p.ped_crash AND cb.roadway_gid = ri.gid
  AND cb.frm_dfo::numeric = ri.frm_dfo AND rdbd_id = 'LG';
-- Result: 293 records.
```

**NOTE:** Remember to cast any comparison between a `real` and `numeric` type, or `real` and `real` type, to `numeric` using the `::numeric` clause. Otherwise, PostgreSQL is bound to have a precision error and real types won't compare. Check types before running a query.

### How do I filter to on-system segments?

To query on 0.1-mile segments that are "on-system", do this, using the Roadway Inventory `rec` field:

```sql
SELECT u.roadway_gid, u.ref_begin, u.closest_frm_dfo
FROM uniform_segs_01mi u, roadway_inv ri
WHERE u.roadway_gid = ri.gid AND u.closest_frm_dfo = ri.frm_dfo
  AND ri.rec <= 3; 
```

Example: Counting the number of "on-system" and "off-system" 1-mile segments:

```sql
-- On-system:
SELECT COUNT(1), AVG(ref_end - ref_begin) FROM uniform_segs_1mi u, roadway_inv ri
WHERE u.roadway_gid = ri.gid AND u.closest_frm_dfo = ri.frm_dfo
  AND ri.rec <= 3;
-- That's 105,023 uniform segments, averaging 0.967 miles long per segment.

-- Off-system:
SELECT COUNT(1), AVG(ref_end - ref_begin) FROM uniform_segs_1mi u, roadway_inv ri
WHERE u.roadway_gid = ri.gid AND u.closest_frm_dfo = ri.frm_dfo
  AND ri.rec > 3; 
-- That's 554,060 uniform segments, averaging 0.425 miles long. That must be because the total length
-- for these is oftern less than a mile.
```

To set these in the uniform segment definitions `uniform_segs_1mi` and `uniform_segs_01mi`:

```sql
UPDATE uniform_segs_1mi u
  SET on_system = ri.rec <= 3
  FROM roadway_inv ri
  WHERE u.roadway_gid = ri.gid AND u.closest_frm_dfo = ri.frm_dfo;

UPDATE uniform_segs_01mi u
  SET on_system = ri.rec <= 3
  FROM roadway_inv ri
  WHERE u.roadway_gid = ri.gid AND u.closest_frm_dfo = ri.frm_dfo;
```

And, to count the number of on-system segments nearby `ints_osm` intersections and store in `crash_int_osm_rankings` column `on_system_count`. Note that this will only count a maximum of 2.

```sql
-- Prepare crash_int_osm_rankings to represent all intersections, not just
-- those that had crash activity.
INSERT INTO crash_int_osm_rankings (int_id)
  SELECT int_id FROM ints_osm i WHERE NOT EXISTS (SELECT 1 FROM crash_int_osm_rankings r WHERE i.int_id = r.int_id); 

-- Do the on-system segment count:
WITH q AS (
  SELECT a.int_id, COUNT(1) num_onsys
  FROM crash_int_osm_rankings r, ints_osm_members m, ints_osm_approaches a, roadway_inv i
  WHERE r.int_id = m.int_id
    AND m.int_id = a.int_id
    AND m.roadway_gid = a.roadway_gid
    AND m.roadway_gid = i.gid
    AND m.closest_dfo = i.frm_dfo
    AND i.rec <= 3
  GROUP BY a.int_id
)
UPDATE crash_int_osm_rankings r
  SET on_system_count = q.num_onsys
  FROM q
  WHERE q.int_id = r.int_id;
```

### How many intersections does 1-mile segment cross?

According to the OSM intersection matching scheme, an intersection is matched once if it is less than 40m from roadway geometry. (Once matched to the closest segment, the intersection is not matched again.) Until a better approach is used that involves map-matching, this may have some arbitrary intersections, especially around frontage roads and expressways. Nonetheless, if we want to get counts of all of the non-expressway intersections for all 1-mile segments:

```sql
SELECT u.roadway_gid, u.ref_begin, COUNT(1) num_ints
FROM uniform_segs_1mi u, ints_osm_members iom, ints_osm i
WHERE u.roadway_gid = iom.roadway_gid
  AND u.ref_begin::numeric = iom.ref_begin::numeric
  AND iom.int_id = i.int_id
  AND NOT i.junction
GROUP BY u.roadway_gid, u.ref_begin;
```

We add this statistic to `crash_stats_seg_1mi` and `crash_stats_seg_01mi` like this in the `count_ints_crossed` column:

```sql
-- For 1-mile segments:
WITH q AS (
  SELECT u.roadway_gid, u.ref_begin, COUNT(1) num_ints
  FROM uniform_segs_1mi u, ints_osm_members iom, ints_osm i
  WHERE u.roadway_gid = iom.roadway_gid
    AND u.ref_begin::numeric = iom.ref_begin::numeric
    AND iom.int_id = i.int_id
    AND NOT i.junction
  GROUP BY u.roadway_gid, u.ref_begin
)
UPDATE crash_stats_seg_1mi s
  SET count_ints_crossed = q.num_ints
  FROM q
  WHERE q.roadway_gid = s.roadway_gid
    AND q.ref_begin::numeric = s.ref_begin::numeric;

-- For 0.1-mile segments:
WITH q AS (
  SELECT u.roadway_gid, u.ref_begin, COUNT(1) num_ints
  FROM uniform_segs_01mi u, ints_osm_members iom, ints_osm i
  WHERE u.roadway_gid = iom.roadway_gid
    AND u.ref_begin::numeric = iom.ref_begin::numeric
    AND iom.int_id = i.int_id
    AND NOT i.junction
  GROUP BY u.roadway_gid, u.ref_begin
)
UPDATE crash_stats_seg_01mi s
  SET count_ints_crossed = q.num_ints
  FROM q
  WHERE q.roadway_gid = s.roadway_gid
    AND q.ref_begin::numeric = s.ref_begin::numeric;
```

### What's a convenient table that has lat, lon with intersections?

For a table that has crash matchups to intersections with lat, lon (using information from "Attempt #3" in [intersections.md](intersections.md)), take a look at `crash_int_osm_nearest` and `crash_int_osm_rankings`. In the `crash_int_osm_nearest` view, there's `crash_id`, `ped_crash` flag, and intersection centroid in `center`, with the crash geographic location in `location`.

### How to get segment centers?

This query will calculate the centroid of 1-mile segments and give out individual lat, lon values:

```sql
SELECT roadway_gid, ref_begin, ST_Y(ST_Centroid(geog::geometry)) center_lat, ST_X(ST_Centroid(geog::geometry)) center_lon FROM uniform_segs_1mi;
```

To add this to `uniform_segs_1mi` and `uniform_segs_01mi` tables:

```sql
UPDATE uniform_segs_1mi
  SET center_lat = ST_Y(ST_Centroid(geog::geometry)),
      center_lon = ST_X(ST_Centroid(geog::geometry))
  WHERE geog IS NOT NULL
    AND ST_IsValid(geog::geometry);

UPDATE uniform_segs_01mi
  SET center_lat = ST_Y(ST_Centroid(geog::geometry)),
      center_lon = ST_X(ST_Centroid(geog::geometry))
  WHERE geog IS NOT NULL
    AND ST_IsValid(geog::geometry);
```

### Getting distance to nearest school, hospital, and transit stop?

We need to have the distance to the nearest school, hospital, and transit stop for each intersection and each segment. I propose adding the segment distances to the `crash_stats_seg_1mi` and `crash_stats_seg_01mi` tables. As for the intersection distances, these can be added to the `crash_int_osm_rankings` table, as that's kind of a stats table for intersections.

To unpack and ingest shapefiles to the database:

```bash
# Schools:
shp2pgsql -D ~/pedcrash/Shapefiles/school.shp schools | psql -U **** -d pedcrash
# The geometry is bad in there for some reason, so we need to recreate it.
psql -U **** -d pedcrash -c "ALTER TABLE schools DROP COLUMN geom;"
psql -U **** -d pedcrash -c "ALTER TABLE schools ADD COLUMN geog geography(point);"
psql -U **** -d pedcrash -c "CREATE INDEX idx_schools_geog ON schools USING GIST(geog);"
psql -U **** -d pedcrash -c "UPDATE schools SET geog = ST_SetSRID(ST_Point(x, y), 4326)::geography;"

# Hospitals:
shp2pgsql -D ~/pedcrash/Shapefiles/hospital.shp hospitals | psql -U **** -d pedcrash
# Geometry is bad in there, too...
psql -U **** -d pedcrash -c "ALTER TABLE hospitals DROP COLUMN geom;"
psql -U **** -d pedcrash -c "ALTER TABLE hospitals ADD COLUMN geog geography(point);"
psql -U **** -d pedcrash -c "CREATE INDEX idx_hospitals_geog ON hospitals USING GIST(geog);"
psql -U **** -d pedcrash -c "UPDATE hospitals SET geog = ST_SetSRID(ST_Point(longitude, latitude), 4326)::geography;"

# Transit stops:
# I transformed the coordinate system to CRS 4326 in QGIS, so I can directly import:
shp2pgsql -D -I -G ~/pedcrash/Shapefiles/transit_stop_fixed.shp transit_stops | psql -U **** -d pedcrash
```

To get closest distances (in meters), the query would go something like this. Everything in excess of 5 km is not dealt with.

```sql
SELECT DISTINCT ON (u.roadway_gid, u.ref_begin)
  u.roadway_gid, u.ref_begin, ST_Distance(ST_Centroid(u.geog::geometry)::geography, h.geog) dist
FROM uniform_segs_1mi u, hospitals h
WHERE ST_DWithin(u.geog, h.geog, 5000)
ORDER BY u.roadway_gid, u.ref_begin, ST_Distance(ST_Centroid(u.geog::geometry)::geography, h.geog);
```

The queries to get this into `crash_stats_seg_1mi`, `crash_stats_seg_01mi` and `crash_int_osm_rankings` tables. Remember to cast `ref_begin` to `numeric` in case there are precision errors.

```sql
-- Schools on 1-mile segments:
WITH q AS (
  SELECT DISTINCT ON (u.roadway_gid, u.ref_begin)
      u.roadway_gid, u.ref_begin, ST_Distance(ST_Centroid(u.geog::geometry)::geography, s.geog) dist
    FROM uniform_segs_1mi u, schools s
    WHERE ST_DWithin(u.geog, s.geog, 5000)
    ORDER BY u.roadway_gid, u.ref_begin, ST_Distance(ST_Centroid(u.geog::geometry)::geography, s.geog)
)
UPDATE crash_stats_seg_1mi s
  SET dist_school = q.dist -- in meters
  FROM q
  WHERE s.roadway_gid = q.roadway_gid AND s.ref_begin::numeric = q.ref_begin::numeric;

-- Schools on 0.1-mile segments:
WITH q AS (
  SELECT DISTINCT ON (u.roadway_gid, u.ref_begin)
      u.roadway_gid, u.ref_begin, ST_Distance(ST_Centroid(u.geog::geometry)::geography, s.geog) dist
    FROM uniform_segs_01mi u, schools s
    WHERE ST_DWithin(u.geog, s.geog, 5000)
    ORDER BY u.roadway_gid, u.ref_begin, ST_Distance(ST_Centroid(u.geog::geometry)::geography, s.geog)
)
UPDATE crash_stats_seg_01mi s
  SET dist_school = q.dist
  FROM q
  WHERE s.roadway_gid = q.roadway_gid AND s.ref_begin::numeric = q.ref_begin::numeric;

-- Schools on intersections:
WITH q AS (
  SELECT DISTINCT ON (i.int_id)
      i.int_id, ST_Distance(i.center, s.geog) dist
    FROM ints_osm i, schools s
    WHERE ST_DWithin(i.center, s.geog, 5000)
    ORDER BY i.int_id, ST_Distance(i.center, s.geog)
)
UPDATE crash_int_osm_rankings i
  SET dist_school = q.dist
  FROM q
  WHERE i.int_id = q.int_id;

-- Hospitals on 1-mile segments:
WITH q AS (
  SELECT DISTINCT ON (u.roadway_gid, u.ref_begin)
      u.roadway_gid, u.ref_begin, ST_Distance(ST_Centroid(u.geog::geometry)::geography, h.geog) dist
    FROM uniform_segs_1mi u, hospitals h
    WHERE ST_DWithin(u.geog, h.geog, 5000)
    ORDER BY u.roadway_gid, u.ref_begin, ST_Distance(ST_Centroid(u.geog::geometry)::geography, h.geog)
)
UPDATE crash_stats_seg_1mi s
  SET dist_hospital = q.dist
  FROM q
  WHERE s.roadway_gid = q.roadway_gid AND s.ref_begin::numeric = q.ref_begin::numeric;

-- Hospitals on 0.1-mile segments:
WITH q AS (
  SELECT DISTINCT ON (u.roadway_gid, u.ref_begin)
      u.roadway_gid, u.ref_begin, ST_Distance(ST_Centroid(u.geog::geometry)::geography, h.geog) dist
    FROM uniform_segs_01mi u, hospitals h
    WHERE ST_DWithin(u.geog, h.geog, 5000)
    ORDER BY u.roadway_gid, u.ref_begin, ST_Distance(ST_Centroid(u.geog::geometry)::geography, h.geog)
)
UPDATE crash_stats_seg_01mi s
  SET dist_hospital = q.dist
  FROM q
  WHERE s.roadway_gid = q.roadway_gid AND s.ref_begin::numeric = q.ref_begin::numeric;

-- Hospitals on intersections:
WITH q AS (
  SELECT DISTINCT ON (i.int_id)
      i.int_id, ST_Distance(i.center, h.geog) dist
    FROM ints_osm i, hospitals h
    WHERE ST_DWithin(i.center, h.geog, 5000)
    ORDER BY i.int_id, ST_Distance(i.center, h.geog)
)
UPDATE crash_int_osm_rankings i
  SET dist_hospital = q.dist
  FROM q
  WHERE i.int_id = q.int_id;

-- Transit stops on 1-mile segments:
WITH q AS (
  SELECT DISTINCT ON (u.roadway_gid, u.ref_begin)
      u.roadway_gid, u.ref_begin, ST_Distance(ST_Centroid(u.geog::geometry)::geography, s.geog) dist
    FROM uniform_segs_1mi u, transit_stops s
    WHERE ST_DWithin(u.geog, s.geog, 5000)
    ORDER BY u.roadway_gid, u.ref_begin, ST_Distance(ST_Centroid(u.geog::geometry)::geography, s.geog)
)
UPDATE crash_stats_seg_1mi s
  SET dist_transit = q.dist
  FROM q
  WHERE s.roadway_gid = q.roadway_gid AND s.ref_begin::numeric = q.ref_begin::numeric;

-- Transit stops on 0.1-mile segments:
WITH q AS (
  SELECT DISTINCT ON (u.roadway_gid, u.ref_begin)
      u.roadway_gid, u.ref_begin, ST_Distance(ST_Centroid(u.geog::geometry)::geography, s.geog) dist
    FROM uniform_segs_01mi u, transit_stops s
    WHERE ST_DWithin(u.geog, s.geog, 5000)
    ORDER BY u.roadway_gid, u.ref_begin, ST_Distance(ST_Centroid(u.geog::geometry)::geography, s.geog)
)
UPDATE crash_stats_seg_01mi s
  SET dist_transit = q.dist
  FROM q
  WHERE s.roadway_gid = q.roadway_gid AND s.ref_begin::numeric = q.ref_begin::numeric;

-- Transit stops on intersections:
WITH q AS (
  SELECT DISTINCT ON (i.int_id)
      i.int_id, ST_Distance(i.center, s.geog) dist
    FROM ints_osm i, transit_stops s
    WHERE ST_DWithin(i.center, s.geog, 5000)
    ORDER BY i.int_id, ST_Distance(i.center, s.geog)
)
UPDATE crash_int_osm_rankings i
  SET dist_transit = q.dist
  FROM q
  WHERE i.int_id = q.int_id;
```

For count of transit stops within a quarter-mile radius from intersections and segments:

```sql
-- Segments:
SELECT u.roadway_gid, u.ref_begin, COUNT(1) transit_stops
FROM uniform_segs_1mi u, transit_stops ts
WHERE ST_DWithin(u.geog, ts.geog, 0.25 * 1609.34)
GROUP BY u.roadway_gid, u.ref_begin;

-- Intersections:
SELECT i.int_id, COUNT(1) transit_stops
FROM ints_osm i, transit_stops ts
WHERE ST_DWithin(i.center, ts.geog, 0.25 * 1609.34)
GROUP BY i.int_id;
```

Getting this into the `crash_stats_seg_1mi`, `crash_stats_seg_01mi` and `crash_int_osm_rankings` tables:

```sql
-- 1-mile segments:
WITH q AS (
  SELECT u.roadway_gid, u.ref_begin, COUNT(1) transit_stops
    FROM uniform_segs_1mi u, transit_stops ts
    WHERE ST_DWithin(u.geog, ts.geog, 0.25 * 1609.34)
    GROUP BY u.roadway_gid, u.ref_begin
)
UPDATE crash_stats_seg_1mi s
  SET count_transit_025mi = q.transit_stops
  FROM q
  WHERE s.roadway_gid = q.roadway_gid AND s.ref_begin::numeric = q.ref_begin::numeric;

-- 0.1-mile segments:
WITH q AS (
  SELECT u.roadway_gid, u.ref_begin, COUNT(1) transit_stops
    FROM uniform_segs_01mi u, transit_stops ts
    WHERE ST_DWithin(u.geog, ts.geog, 0.25 * 1609.34)
    GROUP BY u.roadway_gid, u.ref_begin
)
UPDATE crash_stats_seg_01mi s
  SET count_transit_025mi = q.transit_stops
  FROM q
  WHERE s.roadway_gid = q.roadway_gid AND s.ref_begin::numeric = q.ref_begin::numeric;

-- Intersections:
WITH q AS (
  SELECT i.int_id, COUNT(1) transit_stops
    FROM ints_osm i, transit_stops ts
    WHERE ST_DWithin(i.center, ts.geog, 0.25 * 1609.34)
    GROUP BY i.int_id
)
UPDATE crash_int_osm_rankings i
  SET count_transit_025mi = q.transit_stops
  FROM q
  WHERE i.int_id = q.int_id;
```

### How to get ped crash counts per segment for midblock?

That would include fatal, too. We can be inspired by the stats that went into the `crash_stats_seg_1mi` table and have queries like this. The queries that fill out the `count_all_nonint`, etc. fields are described in [uniform_seg.md](uniform_seg.md) and [uniform_seg_10.md](uniform_seg_10.md), and look similar to these:

```sql
-- Count of nearest midblock ped crashes for each 1-mile uniform segment:
SELECT roadway_gid, ref_begin, COUNT(1) crash_count
FROM crash_buf_1mi c, ped_activity p, share_crash sc
WHERE nearest
  AND c.crash_id = p.crash_id
  AND p.ped_crash
  AND c.crash_id = sc.crash_id
  AND sc.at_intrsct_fl <> 'Y'
GROUP BY roadway_gid, ref_begin;

-- Count of nearest fatal intersection ped crashes for each 1-mile uniform segment:
SELECT roadway_gid, ref_begin, COUNT(1) crash_count
FROM crash_buf_1mi c, ped_activity p, share_crash sc
WHERE nearest
  AND c.crash_id = p.crash_id
  AND p.ped_crash
  AND c.crash_id = sc.crash_id
  AND sc.at_intrsct_fl = 'Y'
  AND p.ped_fatal > 0
GROUP BY roadway_gid, ref_begin;
```

The fields `count_nearest_all`, `count_nearest_ped`, and `count_nearest_pedfatal` in table `crash_stats_seg_1mi` count all nearest crashes, nearest ped-related crashes, and nearest ped-fatal crashes, whereas `count_all_nonint`, `count_ped_nonint`, and `count_pf_nonint` count those that `at_intrsct_fl <> 'Y'`. To get number of intersection crashes, calculate the difference of these.

**NOTE** in table `crash_stats_seg_1mi` that the first three equivalent fields are labeled as `count_all_nearest`, `count_ped_nearest`, and `count_pf_nearest`.

**NOTE**: Nearest counts for these for intersections as defined in `ints_osm` is found in the `crash_int_osm_rankings` table, columns `count_all`, `count_ped` and `count_pedfatal`, also for nearest crashes.

### What's the difference between "at_intrsct_fl" and "intrsct_relat_id"?

My impression is that the `at_intrsct_fl` is transcribed from the police report, where the `intrsct_relat_id` is noted as an "interpreted field". I'm e-mailing `TRF_TECrashDataRequest@txdot.gov` to ask about it. Meanwhile, remember that `intrsct_relat_id` has a number of possibilities:

| INTRSCT RELAT ID | INTRSCT RELAT TXT
|---|---
| 1 | INTERSECTION
| 2 | INTERSECTION RELATED
| 3 | DRIVEWAY ACCESS
| 4	| NON INTERSECTION

### Finally, where's the sidewalks?

I find the total length of sidewalks around an intersection center within a 45m radius that could be used that as sort of a ranking.

> **QUESTION:** Store just total length or some kind of normalized value?

I also look at total sidewalk length along a 1-mile segment (and 0.1-mile segment), within a 30m distance. If there are two sidewalks, then there's more total.

There are two sidewalk totals. One is the "visual" set, and one is the "inventoried" set. Upon inspection, they appear to be spatially mutually exclusive. TxDOT's goal is to carefully inventory all sidewalks on the system. But, until then, there are quick "visual" drive-by inspections that appear in the "visual" set. Because there are two sets, there are two totals. Because it appears that the two sets are mutually exclusive, it is probably safe to add the two totals together to get a sense of how much sidewalk there is around each segment or intersection.

To upload the sidewalk data:

```bash
shp2pgsql -D -I -G ~/pedcrash/TxDOT\ Visual\ Sidewalk\ Paths/Visual_Sidewalk_Paths.shp sidewalks_visual | psql -U **** -d pedcrash
shp2pgsql -D -I -G ~/pedcrash/TxDOT-OnSystem_Sidwalks/TxDOT_On_System_Sidwalk_Inventory.shp sidewalks_inv | psql -U **** -d pedcrash
```

Then, to get visual sidewalk length (in meters) in proximity of intersection, with a 45m radius:

```sql
SELECT i.int_id, ST_Length(ST_Intersection(ST_Union(s.geog::geometry)::geography, ST_Buffer(i.center, 45))) distance
FROM ints_osm i, sidewalks_visual s
WHERE ST_DWithin(i.center, s.geog, 45)
GROUP BY i.int_id;
```

To get sidewalk length (in meters) in proximity of 1-mile segments, with a 30m buffer:

```sql
SELECT u.roadway_gid, u.ref_begin, ST_Length(ST_Intersection(ST_Union(s.geog::geometry)::geography, ST_Buffer(u.geog::geometry, 30, 'endcap=flat join=round'))) distance
FROM uniform_segs_1mi u, sidewalks_visual s
WHERE ST_DWithin(u.geog, s.geog, 30)
GROUP BY u.roadway_gid, u.ref_begin;
```

Loading these into the `crash_stats_seg_1mi`, `crash_stats_seg_01mi` and `crash_int_osm_rankings` tables (`sidewalk_len_vis` and `sidewalk_len_inv` columns):

```sql
-- 1-mile segments:
WITH q AS (
  SELECT u.roadway_gid, u.ref_begin, ST_Length(ST_Intersection(ST_MakeValid(ST_Union(s.geog::geometry)), ST_Buffer(u.geog::geometry, 30, 'endcap=flat join=round'))::geography) dist
    FROM uniform_segs_1mi u, sidewalks_visual s
    WHERE ST_DWithin(u.geog, s.geog, 30)
    GROUP BY u.roadway_gid, u.ref_begin
)
UPDATE crash_stats_seg_1mi s
  SET sidewalk_len_vis = q.dist
  FROM q
  WHERE s.roadway_gid = q.roadway_gid AND s.ref_begin::numeric = q.ref_begin::numeric;

WITH q AS (
  SELECT u.roadway_gid, u.ref_begin, ST_Length(ST_Intersection(ST_MakeValid(ST_Union(s.geog::geometry)), ST_Buffer(u.geog::geometry, 30, 'endcap=flat join=round'))::geography) dist
    FROM uniform_segs_1mi u, sidewalks_inv s
    WHERE ST_DWithin(u.geog, s.geog, 30)
    GROUP BY u.roadway_gid, u.ref_begin
)
UPDATE crash_stats_seg_1mi s
  SET sidewalk_len_inv = q.dist
  FROM q
  WHERE s.roadway_gid = q.roadway_gid AND s.ref_begin::numeric = q.ref_begin::numeric;

-- 0.1-mile segments:
WITH q AS (
  SELECT u.roadway_gid, u.ref_begin, ST_Length(ST_Intersection(ST_MakeValid(ST_Union(s.geog::geometry)), ST_Buffer(u.geog::geometry, 30, 'endcap=flat join=round'))::geography) dist
    FROM uniform_segs_01mi u, sidewalks_visual s
    WHERE ST_DWithin(u.geog, s.geog, 30)
    GROUP BY u.roadway_gid, u.ref_begin
)
UPDATE crash_stats_seg_01mi s
  SET sidewalk_len_vis = q.dist
  FROM q
  WHERE s.roadway_gid = q.roadway_gid AND s.ref_begin::numeric = q.ref_begin::numeric;

WITH q AS (
  SELECT u.roadway_gid, u.ref_begin, ST_Length(ST_Intersection(ST_MakeValid(ST_Union(s.geog::geometry)), ST_Buffer(u.geog::geometry, 30, 'endcap=flat join=round'))::geography) dist
    FROM uniform_segs_01mi u, sidewalks_inv s
    WHERE ST_DWithin(u.geog, s.geog, 30)
    GROUP BY u.roadway_gid, u.ref_begin
)
UPDATE crash_stats_seg_01mi s
  SET sidewalk_len_inv = q.dist
  FROM q
  WHERE s.roadway_gid = q.roadway_gid AND s.ref_begin::numeric = q.ref_begin::numeric;

-- Intersections:
WITH q AS (
  SELECT i.int_id, ST_Length(ST_Intersection(ST_MakeValid(ST_Union(s.geog::geometry)), ST_Buffer(i.center, 45))::geography) dist
    FROM ints_osm i, sidewalks_visual s
    WHERE ST_DWithin(i.center, s.geog, 45)
    GROUP BY i.int_id
)
UPDATE crash_int_osm_rankings i
  SET sidewalk_len_vis = q.dist
  FROM q
  WHERE i.int_id = q.int_id;

WITH q AS (
  SELECT i.int_id, ST_Length(ST_Intersection(ST_MakeValid(ST_Union(s.geog::geometry)), ST_Buffer(i.center, 45))::geography) dist
    FROM ints_osm i, sidewalks_inv s
    WHERE ST_DWithin(i.center, s.geog, 45)
    GROUP BY i.int_id
)
UPDATE crash_int_osm_rankings i
  SET sidewalk_len_inv = q.dist
  FROM q
  WHERE i.int_id = q.int_id;
```

## Other Statistics for the Paper

These are other statistics that were requested. All of these would be for both Texas and just the City of Austin. In preparation, `study_area` Shapefile was given to isolate to City of Austin by geographic region. (It would have been possible to key off of other fields that help to indicate Austin, but this will probably be more reliable.)

```bash
shp2pgsql -D -I -G ~/pedcrash/study_area/study_area.shp study_area | psql -U **** -d pedcrash
```

There's just one record in there where `gid = 1`, and presumably in that `geog` represents Austin city limits.

### Yearly/Total number of crashes at intersections?

```sql
-- Ped crashes at intersections for Texas:
WITH q AS (
  SELECT EXTRACT(year FROM c.crash_date) AS crash_year, COUNT(1) AS num_crash
    FROM share_crash c, ped_activity p
    WHERE c.crash_id = p.crash_id
      AND p.ped_crash
      AND c.at_intrsct_fl = 'Y'
    GROUP BY EXTRACT(year FROM c.crash_date)
    ORDER BY EXTRACT(year FROM c.crash_date)
)
SELECT crash_year::varchar, num_crash FROM q
UNION
SELECT 'Total' crash_year, SUM(num_crash) num_crash FROM q
ORDER BY crash_year;

-- For Austin:
WITH q AS (
  SELECT EXTRACT(year FROM c.crash_date) AS crash_year, COUNT(1) AS num_crash
    FROM share_crash c, ped_activity p, study_area s
    WHERE c.crash_id = p.crash_id
      AND p.ped_crash
      AND c.at_intrsct_fl = 'Y'
      AND s.gid = 1
      AND ST_Within(c.location::geometry, s.geog::geometry)
    GROUP BY EXTRACT(year FROM c.crash_date)
    ORDER BY EXTRACT(year FROM c.crash_date)
)
SELECT crash_year::varchar, num_crash FROM q
UNION
SELECT 'Total' crash_year, SUM(num_crash) num_crash FROM q
ORDER BY crash_year;
```

### Yearly/Total number of crashes at midblock segments

```sql
-- Ped crashes at midblock for Texas:
WITH q AS (
  SELECT EXTRACT(year FROM c.crash_date) AS crash_year, COUNT(1) AS num_crash
    FROM share_crash c, ped_activity p
    WHERE c.crash_id = p.crash_id
      AND p.ped_crash
      AND c.at_intrsct_fl <> 'Y'
    GROUP BY EXTRACT(year FROM c.crash_date)
    ORDER BY EXTRACT(year FROM c.crash_date)
)
SELECT crash_year::varchar, num_crash FROM q
UNION
SELECT 'Total' crash_year, SUM(num_crash) num_crash FROM q
ORDER BY crash_year;

-- For Austin:
WITH q AS (
  SELECT EXTRACT(year FROM c.crash_date) AS crash_year, COUNT(1) AS num_crash
    FROM share_crash c, ped_activity p, study_area s
    WHERE c.crash_id = p.crash_id
      AND p.ped_crash
      AND c.at_intrsct_fl <> 'Y'
      AND s.gid = 1
      AND ST_Within(c.location::geometry, s.geog::geometry)
    GROUP BY EXTRACT(year FROM c.crash_date)
    ORDER BY EXTRACT(year FROM c.crash_date)
)
SELECT crash_year::varchar, num_crash FROM q
UNION
SELECT 'Total' crash_year, SUM(num_crash) num_crash FROM q
ORDER BY crash_year;
```

### Crashes by severity level intersections vs. midblock segments

The key for crash severity is from the CRIS data dictionary:

| ID | Type
|-|-
| 0 |	UNKNOWN
| 1	| SUSPECTED SERIOUS INJURY
| 2	| NON-INCAPACITATING INJURY
| 3	| POSSIBLE INJURY
| 4	| KILLED
| 5	| NOT INJURED

```sql
-- Ped crashes for Texas, with severity, for intersections and midblock:
SELECT crash_sev_id, at_intrsct_fl = 'Y' AS at_intrsct, COUNT(1) AS num_crash
    FROM share_crash c, ped_activity p
    WHERE c.crash_id = p.crash_id
      AND p.ped_crash
    GROUP BY crash_sev_id, at_intrsct_fl = 'Y'
    ORDER BY crash_sev_id, at_intrsct_fl = 'Y';

-- Ped crashes for Austin, with severity, for intersections and midblock:
SELECT crash_sev_id, at_intrsct_fl = 'Y' AS at_intrsct, COUNT(1) AS num_crash
    FROM share_crash c, ped_activity p, study_area s
    WHERE c.crash_id = p.crash_id
      AND p.ped_crash
      AND s.gid = 1
      AND ST_Within(c.location::geometry, s.geog::geometry)
    GROUP BY crash_sev_id, at_intrsct_fl = 'Y'
    ORDER BY crash_sev_id, at_intrsct_fl = 'Y';
```
