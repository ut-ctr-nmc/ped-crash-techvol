# Intersection Matching

## Introduction

This document describes a method for matching crashes to intersections, in efforts to be able to classify "intersection crashes" with more detail than the `AT_INTRSCT_FL` field provided in the CRIS Share data. The process is tricky and time consuming because TxDOT Roadway Inventory does not contain a set of nodes that mark intersections. The best we can do is to identify where TxDOT Roadway Inventory geometry criss-crosses (while filtering out conditions where we don't want to assume the presence of an intersection, such as places that are likely to be grade-separated), and then do a proximity match with crash records.

In preparation, we assume that the database already has TxDOT Roadway Inventory imported and CRIS records available.

> **NOTE:** Attempt #3 below is what was used ultimately for the core project analysis and representation in the [peds-midblocks-intersections](https://github.com/ut-ctr-nmc/peds-midblocks-intersections) repository.

## Attempt #1: All Crashes

This attempt ties crashes to intersections regardless of the `AT_INTRSCT_FL` field. This did work somewhat, but left a lot of crashes tied with locations that may not have been true because of ambiguities around divided highway direction and grade separation.

### Geometry Preparation

Here, we find intersecting geometry or near-intersecting geometry. Then, we filter out cases that we do not want to mark as an intersection-- specifically, Functional Class 1 roads that intersect. These are more likely to be grade-separated crossings. However, there is additional filtering that includes places that are likely to be on- or off-ramps on freeways, which we *do* want to treat as intersections.

```sql
-- Find all intersections. This query takes about 3 hours.
-- TODO: Need special treatment for wide freeways. May want to do nearby searches and then branch
-- out to directionals? Do we want to project crashes to the directionals?
CREATE TABLE crash_int_work AS
  SELECT cb1.crash_id, r1.gid gid1, r1.frm_dfo frm_dfo1, r2.gid gid2, r2.frm_dfo frm_dfo2, FALSE as ramp 
  FROM crash_buf_100 cb1, crash_buf_100 cb2, roadway_inv r1, roadway_inv r2
  WHERE cb1.crash_id = cb2.crash_id
    AND cb1.distance <= 50
	  AND cb2.distance <= 50
    AND cb1.roadway_gid = r1.gid
    AND cb1.frm_dfo::numeric = r1.frm_dfo
    AND cb2.roadway_gid = r2.gid
    AND cb2.frm_dfo::numeric = r2.frm_dfo
    AND (r1.gid <> r2.gid OR r1.frm_dfo <> r2.frm_dfo)
    AND ST_DWithin(r1.geog, r2.geog, 5, FALSE);
	
-- Filter out Functional Class 1 that criss-crosses, except for places that look like on- or off-ramps.
-- TODO: We may want to snip out a radius before doing ST_LineMerge to increase likelihood that the operation
-- will be successful.
UPDATE crash_int_work ciw
  SET ramp = TRUE
  FROM roadway_inv r1, roadway_inv r2
  WHERE ciw.gid1 = r1.gid
    AND ciw.frm_dfo1 = r1.frm_dfo
    AND ciw.gid2 = r2.gid
    AND ciw.frm_dfo2 = r2.frm_dfo
	AND r1.f_system = 1 AND r2.f_system = 1
	AND (ST_DWithin(ST_StartPoint(ST_LineMerge(r1.geog::geometry))::geography, r2.geog, 5)
	  AND NOT EXISTS(SELECT 1 FROM roadway_inv r3 WHERE r1.gid = r3.gid AND r3.frm_dfo < r1.frm_dfo)
	OR ST_DWithin(ST_EndPoint(ST_LineMerge(r1.geog::geometry))::geography, r2.geog, 5)
	  AND NOT EXISTS(SELECT 1 FROM roadway_inv r3 WHERE r1.gid = r3.gid AND r3.frm_dfo > r1.frm_dfo));

DELETE FROM crash_int_work ciw
  USING roadway_inv r1, roadway_inv r2
  WHERE ciw.gid1 = r1.gid
    AND ciw.frm_dfo1 = r1.frm_dfo
    AND ciw.gid2 = r2.gid
    AND ciw.frm_dfo2 = r2.frm_dfo
	AND r1.f_system = 1 AND r2.f_system = 1
	AND NOT ciw.ramp;

-- Debug view. This is a table that can be visualized to see a first cut at intersection crashes.
CREATE TABLE ciw_test AS
  SELECT crash_id, gid1, frm_dfo1, gid2, frm_dfo2, ramp,
    ST_ClosestPoint(r1.geog::geometry, r2.geog::geometry)::geography point,
	COALESCE(r1.ste_nam, r1.ria_rte_id) || ' & ' || COALESCE(r2.ste_nam, r2.ria_rte_id) AS names
  FROM crash_int_work ciw, roadway_inv r1, roadway_inv r2
  WHERE ciw.gid1 = r1.gid
    AND ciw.frm_dfo1 = r1.frm_dfo
    AND ciw.gid2 = r2.gid
    AND ciw.frm_dfo2 = r2.frm_dfo;
CREATE INDEX idx_ciw_test_point ON ciw_test USING GIST(point);

-- Take out matches to centerlines where directional exists. This happens in cases
-- where TxDOT Roadway Inventory has a "KG-" centerline on divided roadways. We'd
-- rather the crashes are tied with the directions on divided highways.
DELETE FROM crash_int_work ciw
  USING crash_buf_100 cb1, crash_buf_100 cb2
  WHERE ciw.crash_id = cb1.crash_id
    AND (ciw.gid1 = cb1.roadway_gid
      AND ciw.frm_dfo1 = cb1.frm_dfo::numeric
	OR ciw.gid2 = cb1.roadway_gid
      AND ciw.frm_dfo2 = cb1.frm_dfo::numeric)
	AND ciw.crash_id = cb2.crash_id
	AND cb1.roadway_gid = cb2.primary_gid;

-- Get intersection centers and distances from crash points.
ALTER TABLE crash_int_work ADD COLUMN geog GEOGRAPHY(Point);
ALTER TABLE crash_int_work ADD COLUMN dist real;
UPDATE crash_int_work ciw
  SET geog = ST_ClosestPoint(r1.geog::geometry, r2.geog::geometry)::geography
  FROM roadway_inv r1, roadway_inv r2
  WHERE ciw.gid1 = r1.gid
    AND ciw.frm_dfo1 = r1.frm_dfo
    AND ciw.gid2 = r2.gid
    AND ciw.frm_dfo2 = r2.frm_dfo;
UPDATE crash_int_work ciw
  SET dist = ST_Distance(geog, c.location)
  FROM share_crash c
  WHERE ciw.crash_id = c.crash_id;

-- Pick intersections that are closest to the crashes:
CREATE TABLE crash_int_work2 AS
  WITH q AS (
    SELECT crash_id, MIN(dist) AS min_dist
      FROM crash_int_work
	  GROUP BY crash_id
  )
  SELECT q.crash_id, ciw.gid1, ciw.frm_dfo1, ciw.gid2, ciw.frm_dfo2, ciw.ramp, ciw.geog, ciw.dist
  FROM crash_int_work ciw, q
  WHERE ciw.crash_id = q.crash_id
    AND ciw.dist = q.min_dist;

-- Filter out translational duplicates. That is, if an intersection is defined as "A crosses B",
-- then remove the intersection that is defined as "B crosses A".
ALTER TABLE crash_int_work2 ADD COLUMN id SERIAL PRIMARY KEY;
DELETE FROM crash_int_work2 ciw1
  USING crash_int_work2 ciw2
  WHERE ciw1.id <> ciw2.id
    AND ciw1.gid1 = ciw2.gid2
    AND ciw1.frm_dfo1 = ciw2.frm_dfo2
	AND (ciw1.gid1 > ciw2.gid1
	  OR ciw1.gid1 = ciw2.gid1
	  AND ciw1.frm_dfo1 = ciw2.frm_dfo1
	  AND ciw1.id > ciw2.id);

-- Identify intersection centers. This takes all intersection centers in close proximity
-- and finds a common center for all of them. This is needed for intersections where
-- approaches are slightly offset, certain cases for divided highways, and intersections that
-- have more than 4 approaches.
-- TODO: Newer versions of PostGIS have a clustering function that would make this much easier.
ALTER TABLE crash_int_work2 ADD COLUMN center GEOGRAPHY(Point);
CREATE INDEX ciw2_idx ON crash_int_work2 USING GIST(geog);
WITH q AS (
  SELECT ciw2a.id id1, ciw2b.id id2 
    FROM crash_int_work2 ciw2a, crash_int_work2 ciw2b
    WHERE ST_DWithin(ciw2a.geog, ciw2b.geog, 15)
), r AS (
  SELECT ciw2a.id, ST_Centroid(ST_Union(ciw2b.geog::geometry))::geography centroid
    FROM crash_int_work2 ciw2a, crash_int_work2 ciw2b, q
	WHERE ciw2a.id = q.id1
	  AND ciw2b.id = q.id2
	GROUP BY ciw2a.id
)
UPDATE crash_int_work2 SET center = r.centroid FROM r WHERE r.id = crash_int_work2.id;
CREATE INDEX ciw2_cent_idx ON crash_int_work2 USING GIST(center);

-- Isolate unique intersections. The theory is that combinations of nearby intersections
-- will have resulted in the same centers. So, we can filter out the duplicates.
-- Note that "ST_AsBinary()" is needed to make distinct comparisons with geometry.
CREATE TABLE intersections (
  int_id SERIAL PRIMARY KEY,
  center GEOGRAPHY(Point)
);
CREATE INDEX intersections_cent_idx ON intersections USING GIST(center);
INSERT INTO intersections (center)
  SELECT DISTINCT ON (ST_AsBinary(center)) center FROM crash_int_work2;

-- Annotate intersections. We try to get street names or route IDs from the Roadway Inventory.
CREATE TEMP TABLE int_mem_work (
  int_id integer,
  roadway_gid integer,
  frm_dfo numeric,
  name varchar
);
INSERT INTO int_mem_work (int_id, roadway_gid, frm_dfo, name)
  SELECT DISTINCT ON (ci.int_id, r.gid)
    ci.int_id, ciw2.gid1, ciw2.frm_dfo1, COALESCE(r.ste_nam, r.ria_rte_id)
  FROM crash_intersections ci, crash_int_work2 ciw2, roadway_inv r
  WHERE ci.crash_id = ciw2.crash_id
    AND ciw2.gid1 = r.gid
	AND ciw2.frm_dfo1 = r.frm_dfo;
INSERT INTO int_mem_work (int_id, roadway_gid, frm_dfo, name)
  SELECT DISTINCT ON (ci.int_id, r.gid)
    ci.int_id, ciw2.gid2, ciw2.frm_dfo2, COALESCE(r.ste_nam, r.ria_rte_id)
  FROM crash_intersections ci, crash_int_work2 ciw2, roadway_inv r
  WHERE ci.crash_id = ciw2.crash_id
    AND ciw2.gid2 = r.gid
	AND ciw2.frm_dfo2 = r.frm_dfo;

-- The intersection_members table then lists out each and every link that approaches or
-- departs from an intersection site.
CREATE TABLE intersection_members (
  int_id integer REFERENCES intersections(int_id) ON DELETE CASCADE,
  roadway_gid integer,
  frm_dfo numeric,
  name varchar,
  PRIMARY KEY (int_id, roadway_gid)
);
INSERT INTO intersection_members
  SELECT DISTINCT ON (int_id, roadway_gid)
    int_id, roadway_gid, frm_dfo, name
  FROM int_mem_work
  ORDER BY int_id, roadway_gid, frm_dfo;

-- More help with intersections:
ALTER TABLE intersections ADD COLUMN descr varchar;
UPDATE intersections i
  SET descr = (SELECT string_agg(im.name, ' & ')
    FROM intersection_members im
    WHERE i.int_id = im.int_id
    GROUP BY int_id);

-- Cleanup:
DROP TABLE crash_int_work;
DROP TABLE crash_int_work2;
INSERT INTO intersections (int_id, center, descr) VALUES (0, 'POINT EMPTY', '(Undefined)');
```

### Crash Matchup
At this point, we can tie crashes to intersections found on the TxDOT Roadway Inventory using a proximity search of 100 meters. For each crash, a match is made with the nearest intersection center so long as the distance is 100 meters or less.
```sql
CREATE TABLE crash_int_matchup (
  int_id integer REFERENCES intersections(int_id) ON DELETE CASCADE,
  crash_id integer REFERENCES share_crash(crash_id),
  distance real,
  PRIMARY KEY (int_id, crash_id)  
);

INSERT INTO crash_int_matchup (int_id, crash_id, distance)
  SELECT DISTINCT ON (i.int_id, c.crash_id) 
    i.int_id, c.crash_id, ST_Distance(c.location, i.center, FALSE) distance
  FROM intersections i, share_crash c
  WHERE ST_DWithin(c.location, i.center, 100, FALSE)
  ORDER BY i.int_id, c.crash_id, ST_Distance(c.location, i.center, FALSE);
```

This is the definition for the table `crash_int_matchup`:
* **int_id:** The identifier into the `intersections` table, which identifies the center geometry and also ties with the `intersection_members` table for refereces to individual intersection members
* **crash_id:** The identifier into the `share_crash` table, which identifies a crash that is geographically tied with the crash
* **distance:** Distance of the crash to the geometric center in meters

### Additional Help in Visualizing
The following view definition is designed to assist in easing the analysis of crashes tied with intersections.

```sql
CREATE VIEW crash_int_all AS
  SELECT c.crash_id, c.crash_date, c.crash_fatal_fl = 'Y' AS crash_fatal_fl,
    c.at_intrsct_fl = 'Y' AS at_intersct_fl, p.ped_crash,
    cim.int_id, cim.distance, i.descr, i.center, c.location
  FROM share_crash c, intersections i, crash_int_matchup cim, ped_activity p
  WHERE c.crash_id = cim.crash_id
    AND c.crash_id = p.crash_id
    AND cim.int_id = i.int_id;

CREATE VIEW crash_int_nearest AS
  SELECT DISTINCT ON (crash_id)
    crash_id, crash_date, crash_fatal_fl, at_intersct_fl, ped_crash, int_id, distance,
      descr, center, location
  FROM crash_int_all
  ORDER BY crash_id, distance;

-- Further insight that captures intersection centers and counts:
CREATE TABLE t AS
WITH q AS (
  SELECT int_id, count(1) cnt
    FROM crash_int_all
    GROUP BY int_id
)
SELECT DISTINCT ON(c.int_id) c.int_id, descr, q.cnt, center
  FROM crash_int_all c, q
  WHERE q.int_id = c.int_id;
```

Then, to visualize, the view can be exported to shapefiles, one to view the intersection centers, and one to view the crash locations:
```bash
pgsql2shp -f ./crash_int_all/crash_int_all_center.shp -u **** -P **** -g center pedcrash t
pgsql2shp -f ./crash_int_all/crash_int_all_location.shp -u **** -P **** -g location pedcrash crash_int_all

pgsql2shp -f ./crash_int_nearest/crash_int_nearest.shp -u **** -P **** -g location pedcrash crash_int_nearest
```

> **TODO:** The `crash_int_nearest` view takes a while to run. We may want to create a shadow table of it.

Additional output:
```sql
\copy crash_int_matchup(int_id, crash_id, distance) TO './crash_int_all/crash_int_matchup.csv' DELIMITER ',' CSV HEADER;
\copy intersection_members (int_id, roadway_gid, frm_dfo, name) TO './crash_int_all/intersection_members.csv' DELIMITER ',' CSV HEADER;
DROP TABLE t;
```

### Caveats and Future Work
This scheme does not look carefully at at directions on divided highways. I did not yet find a good indicator within the CRIS data on the direction of travel at the time of crash. The `Veh_Trvl_Dir_ID` field may be helpful. Also `Rpt_Ref_Mark_Dir`. 

It will be necessary to look at the QGIS visualization again and determine what else might need addressing. Because it hasn't been explicitly addressed, it will be well, too, to find an area where a road continues after changing functional class. For example, find a place where a limited access highway changes to an urban street.

## Attempt #1.1: Filter Prior Results to Intersection Crashes

Because of the sheer number of crashes that had been matched, it may make sense to filter the view created at the end of Attempt #1 to just "intersection matches". About a quarter of all crashes have `AT_INTRSCT_FL` set to "Yes".

> **TODO:** These are duplicates of the views above except for the one `AT_INTRSCT_FL` restricton. Clean up.

```sql
CREATE VIEW crash_int AS
  SELECT c.crash_id, c.crash_date, c.crash_fatal_fl = 'Y' AS crash_fatal_fl, p.ped_crash,
    cim.int_id, cim.distance, i.descr, i.center, c.location
  FROM share_crash c, intersections i, crash_int_matchup cim, ped_activity p
  WHERE c.at_intrsct_fl = 'Y'
    AND c.crash_id = cim.crash_id
    AND c.crash_id = p.crash_id
    AND cim.int_id = i.int_id;

CREATE VIEW crash_int_nearest AS
  SELECT DISTINCT ON (crash_id)
    crash_id, crash_date, crash_fatal_fl, ped_crash, int_id, distance,
      descr, center, location
  FROM crash_int
  ORDER BY crash_id, distance;

-- Further insight that captures intersection centers and counts:
CREATE TABLE t AS
WITH q AS (
  SELECT int_id, count(1) cnt
    FROM crash_int
    GROUP BY int_id
)
SELECT DISTINCT ON(c.int_id) c.int_id, descr, q.cnt, center
  FROM crash_int c, q
  WHERE q.int_id = c.int_id;

CREATE TABLE cim2 AS
  SELECT cim.int_id, cim.crash_id, cim.distance
    FROM crash_int_matchup cim, share_crash c
    WHERE cim.crash_id = c.crash_id
      AND c.at_intrsct_fl = 'Y';
CREATE TABLE im2 AS
  SELECT im.int_id, im.roadway_gid, im.frm_dfo, im.name
    FROM intersection_members im
    WHERE EXISTS (SELECT 1 FROM cim2 WHERE im.int_id = cim2.int_id);
```

Then, to visualize:
```bash
pgsql2shp -f ./crash_int/crash_int_center.shp -u **** -P **** -g center pedcrash t
pgsql2shp -f ./crash_int/crash_int_location.shp -u **** -P **** -g location pedcrash crash_int
pgsql2shp -f ./crash_int/crash_int_loc_nearest.shp -u **** -P **** -g location pedcrash crash_int_nearest
```

Additional output:
```sql
\copy cim2(int_id, crash_id, distance) TO './crash_int/crash_int_matchup.csv' DELIMITER ',' CSV HEADER;
\copy im2(int_id, roadway_gid, frm_dfo, name) TO './crash_int/intersection_members.csv' DELIMITER ',' CSV HEADER;
DROP TABLE t;
DROP TABLE cim2;
DROP TABLE im2;
```

### Implementation Notes from Dec. 2, 2020

From "Intersection Matching Notes" Box Note (accessible to Performing Agency researchers):

This Box folder contains the results of the first rendition of intersection matching. The PDF file contains the technical notes on how I did the matching.

There are two .ZIP files
* **crash_int_all_1.zip:** Results of intersection matching on all crashes that have geographic coordinates in the CRIS Share, so long as the crash is within 100 meters of criss-crossing road segments in the TxDOT Roadway Inventory (2018 version).
* **crash_int_1_1.zip:** Subset of matching on crashes that have AT_INTRSCT_FL set to "Y", which are those records in CRIS that are marked as occurring at intersections

Inside each of the .ZIP files:
* **crash_int_center (Shapefile):** This identifies the intersections that had been discovered. Fields include intersection ID, derived descriptive name from contributing roadway segments, number of crashes that had been matched to that intersection, and geographic center.
* **crash_int_location (Shapefile):** This identifies each crash that had been matched to an intersection. Fields include:
  * **crash_id:** For referencing to share_crash
  * **crash_date:** The date of the crash (from share_crash)
  * **crash_fatal_fl:** True if the crash was marked as fatal in share_crash
  * **at_intrsct_fl:** True if the crash was marked as occurring at an intersection. This field is omitted in "crash_int_1_1" because it is always True
  * **ped_crash:** True if the ped_crash field is set in the ped_activity table based on the 4 criteria that I used to determine if the crash involves pedestrians.
  * **int_id:** The intersection ID for the contents of crash_int_center, crash_int_matchup.csv, and intersection_members.csv
  * **distance:** The distance of the crash from the intersection center in meters
  * **descr:** A name for the intersection concatenated from the names of the segments that comprise the intersection (same as in crash_int_center)
  * **center:** The geographic center of the intersection (same as what's in crash_int_center)
  * **location:** The location of the crash from share_crash
* **crash_int_matchup.csv:** The contents of the table; see the PDF for further notes. (All content is effectively represented in the shapefiles)
* **intersection_members.csv:** This identifies the TxDOT Roadway Inventory segments that comprise each intersection. See the PDF for further information.

It is probably best to start with the "non-all" version since the set is smaller and the results may make more sense. However, it seems as though there are a number of crashes that have been marked as happening at an intersection (AT_INTRSCT_FL = "Y") but they curiously don't seem to. The examples I see are those that show up at major freeway interchanges.

A number of caveats are listed elsewhere in this file. One of the caveats is that the method used to determine an intersection doesn't have a good way of understanding grade separation (e.g. at major freeway interchanges)-- the result is that intersections are marked in many areas around freeways where there aren't intersections, even though I have done some filtering. Obviously I need to study further on how to filter more.

Let's see how well these results can be used, and come up with ideas on how to better filter and process intersection matches for the next go-round. We can consider, too, whether it may be well to cluster intersections.

## Attempt #2: Intersection Crashes to Geometry

This attempt is intended to simplify Attempt #1 by looking only at crashes that have been flagged with `AT_INTRSCT_FL` and to take a different approach to identifying intersections. Some of the ambiguities around grade separations and divided roadway direction may be clearer. Further, this can be run on a later version of PostgreSQL and PostGIS that offer better functions for clustering, further simplifying the process.

> **TODO:** TBD



Looking at naming patterns for service roads:
```sql
SELECT crash_id, rpt_road_part_id, rpt_street_pfx, rpt_street_name, rpt_sec_road_part_id, rpt_sec_street_pfx, rpt_sec_street_name FROM share_crash WHERE at_intrsct_fl = 'Y' AND (rpt_road_part_id = 2 OR rpt_sec_road_part_id = 2);
```

## Attempt #3: Using OpenStreetMap

Natalia Z's analysis requires all intersections to be identified, and an indication of which intersections have signals. She suggested using OpenStreetMap. This also has the benefit where we can understand better which roads connect to intersections, especially in areas that are close to grade separations.

**This strategy worked far better than earlier**, and is what's represented in the [peds-midblocks-intersections](https://github.com/ut-ctr-nmc/peds-midblocks-intersections) repository.

### System Setup

To access OpenStreetMap, I am going creating a local Overpass API instance using the [wiktorn overpass-api Docker container](https://hub.docker.com/r/wiktorn/overpass-api) and to grab the Texas output from [Geofabrik](https://download.geofabrik.de/north-america/us/texas.html). To do this, I am running the following on HOST-MACHINE:

```bash
mkdir -p ~/overpass_DB
chmod a+rw ~/overpass_DB
docker run \
  -e OVERPASS_META=yes \
  -e OVERPASS_MODE=init \
  -e OVERPASS_PLANET_URL=https://download.geofabrik.de/north-america/us/texas-latest.osm.bz2 \
  -e OVERPASS_DIFF_URL=http://download.openstreetmap.fr/replication/north-america/minute/ \
  -e OVERPASS_RULES_LOAD=10 \
  -e OVERPASS_UPDATE_SLEEP=86400 \
  -v ~/overpass_DB:/db \
  -p 8090:80 \
  -i -t \
  --name overpass_texas wiktorn/overpass-api
docker start <container_id>
```

The Overpass API for Texas would be hosted at: http://HOST-MACHINE:8090/api/interpreter

### Approach 1: Use Intersections as Seed Points

Similar to how an earlier process uses crash locations as potential seeds for intersections, this just grabs nodes from OpenStreetMap that potentially represent intersections and uses those locations as places to search for intersecting street geometry. This has the advantage of preventing some false intersections at grade separations and also allows for understanding where signals are. While this is fairly straightforward, it comes with these potential caveats:

* No smarts are in place for preventing nearby street geometry to be considered crossing the intersection. This can affect some grade separations.
* OpenStreetMap may have several nodes around places where divided roads intersect. These need to be collapsed down to one node for better results.
* With the way I'm counting, multiple unnamed streets coming together of the same highway type won't be counted as an intersection.

Regardless of these, there should be enough good matches relatively quickly to make it worthwhile.

The query necessary to get the intersections can look like this:

```
[out:json][bbox:30.3189,-97.7114,30.3223,-97.7056];
way[highway~"^(motorway|trunk|primary|secondary|tertiary|motorway_link|trunk_link|primary_link|secondary_link|tertiary_link)$"];
(._;>;);
out;
```

Equivalent hyperlink:
`http://HOST-MACHINE:8090/api/interpreter?data=[out:json][bbox:30.3189,-97.7114,30.3223,-97.7056];way[highway~"^(motorway|trunk|primary|secondary|tertiary|motorway_link|trunk_link|primary_link|secondary_link|tertiary_link)$"];(._;>;);out;`

> **CAVEAT:** While this hyperlink works if copied and pasted into a web browser, it is proper to escape out a number of the more sensitive characters using something like `urllib.parse.quote()`.

I tried to do a fancier query to isolate intersections modeled off of [examples](https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_API_by_Example) and also [this](https://forum.openstreetmap.org/viewtopic.php?id=60776), but they didn't work. I either got nothing or I got all nodes. So, I'm going to need to do post-processing in Python.

Also, I want to grab tiles of geometry at a time to not process too much in one go. To iterate through Texas, I'd want to process from 25.5136,-107.0439 to 36.6501,-93.3778 with some small degree of overlap in each tile.

Rules for saying that a node is an intersection:
* It has a signal (tag "highway": "traffic_signals"). This will also catch signals for mid-block crossings.
* It is met by more than one way that has a different type and name combination (tag "highway", tag "name" that can be None)
* Nodes serviced by only motorways and motorway links are labeled "junction".
* Don't count nodes that are joined by the ends of just 2 OpenStreetMap ways.
* (There also is the node tag "highway": "motorway_junction", but for the time being I may ignore it.)

After, we'll need to collapse nearby intersections down to one in order to deal with divided roadways.

This is implemented in `GetOSMInts1.py`. It produces `osm_ints.csv`. To import it, the following is done:

```sql
CREATE TABLE intersections_osm1 (
  int_id SERIAL PRIMARY KEY,
  signal BOOLEAN NOT NULL,
  junction BOOLEAN NOT NULL,
  midblock_sig BOOLEAN NOT NULL,
  lat FLOAT,
  lon FLOAT,
  cluster_num INTEGER,
  center GEOGRAPHY(Point)
);
CREATE INDEX intersections_osm1_cent_idx ON intersections_osm1 USING GIST(center);

-- Import the data: (First ensure that the line endings are correct)
\copy intersections_osm1(lat, lon, signal, junction, midblock_sig) FROM '~/pedcrash/osm_ints.csv' DELIMITER ',' CSV HEADER;

-- Prepare the geography:
UPDATE intersections_osm1 SET center = ST_Point(lon, lat);
ALTER TABLE intersections_osm1 DROP lat;
ALTER TABLE intersections_osm1 DROP lon;
```

To do clustering, we need to get the table over to the PostgreSQL 10 database:

```bash
pg_dump -U **** -Fc -f intersections_osm1.sqlbin -t intersections_osm1 pedcrash
pg_restore -Fc -C intersections_osm1.sqlbin | psql -h HOST-MACHINE -U nmc -p 5434 -d pedcrash
```

Now, do clustering on the PostgreSQL 10 database. Clustering will be set to group together intersections 75m apart, allowing for singletons.

```sql
WITH q AS (
  SELECT int_id, ST_ClusterDBSCAN(ST_Transform(center::geometry, 2278), eps := 75, minPoints := 1) OVER (ORDER BY int_id) AS cluster_num
  FROM intersections_osm1
)
UPDATE intersections_osm1 AS io1
  SET cluster_num = q.cluster_num
  FROM q
  WHERE q.int_id = io1.int_id;
```

Write back to PostgreSQL 9 database:

```bash
docker exec -it pg-docker /bin/bash -c "pg_dump -U nmc -t intersections_osm1 pedcrash" > intersections_osm1c.sql
psql -U **** -d pedcrash -c "DROP TABLE intersections_osm1;"
cat intersections_osm1c.sql | psql -U **** -d pedcrash
```

Now, we want to consolidate down the clusters (e.g. close nodes created because of divided roadways) and create a new table, intersections_osm. For that, if a cluster member has a signal, is at a junction, or has midblock signal, "OR" that to the top.

```sql
CREATE TABLE ints_osm (
  int_id SERIAL PRIMARY KEY,
  signal boolean NOT NULL,
  junction boolean NOT NULL,
  midblock_sig boolean NOT NULL,
  descr varchar,
  center GEOGRAPHY(Point)
);
CREATE INDEX ints_osm_cent_idx ON ints_osm USING GIST(center);

INSERT INTO ints_osm (signal, junction, midblock_sig, center)
SELECT bool_or(io1.signal), bool_or(io1.junction), bool_or(io1.midblock_sig),
  ST_Centroid(ST_Union(io1.center::geometry))::geography
  FROM intersections_osm1 AS io1
  GROUP BY cluster_num;
```

This can then be visualized in GIS software as a sanity check.

### Matching Up TxDOT Roadway Inventory

This process, similar to earlier processes around crash clusters, associates nearby TxDOT Roadway Inventory geometry with the proposed intersection sites.

```sql
CREATE TABLE ints_osm_members (
  int_id integer REFERENCES ints_osm(int_id) ON DELETE CASCADE,
  roadway_gid integer,
  ref_begin real, -- Maps to the closest 1-mile uniform segment
  ref_begin_01 real, -- Maps to the closest 0.1-mile uniform segment
  closest_dfo numeric, -- Maps to the closest TxDOT Roadway Inventory segment
  lin_ref real,
  descr varchar,
  PRIMARY KEY (int_id, roadway_gid)
);

-- Find closest uniform geometry, filter for nearby segments:
INSERT INTO ints_osm_members (int_id, roadway_gid, ref_begin, lin_ref)
  SELECT DISTINCT ON (i.int_id, u.roadway_gid)
    i.int_id, u.roadway_gid, u.ref_begin,
    CASE WHEN ST_GeometryType(u.geog::geometry) = 'ST_LineString'
      THEN ST_Line_Locate_Point(u.geog::geometry, i.center::geometry) * (u.ref_end - u.ref_begin) + u.ref_begin
      ELSE NULL
    END AS lin_ref
  FROM ints_osm i, uniform_segs_1mi u
  WHERE ST_DWithin(i.center, u.geog, 40, FALSE)
  ORDER BY i.int_id, u.roadway_gid, ST_Distance(i.center, u.geog, FALSE);

-- TODO: There are 78 entries that have NULL for lin_ref.
-- Go and figure out another way to approximate.

-- Trim away matches that don't match multiple roadways:
-- TODO: Instead of deleting, do we want to mark as invalid?
WITH q AS (
  SELECT i.int_id, count(m.int_id) AS num
  FROM ints_osm AS i
  LEFT JOIN ints_osm_members AS m ON i.int_id = m.int_id
  GROUP BY i.int_id
)
DELETE FROM ints_osm i
  USING q
  WHERE q.int_id = i.int_id
    AND (num < 2
    AND NOT i.signal
    OR num = 0);

-- Figure out the TxDOT Roadway Inventory segment that best represents the member:
WITH q AS (
  SELECT DISTINCT ON (iom.int_id, iom.roadway_gid)
    iom.int_id, iom.roadway_gid, r.frm_dfo
  FROM ints_osm_members iom, roadway_inv r
  WHERE iom.roadway_gid = r.gid
    AND iom.lin_ref::numeric >= r.frm_dfo - 0.001
    AND iom.lin_ref::numeric <= r.to_dfo + 0.001
    ORDER BY iom.int_id, iom.roadway_gid, r.adt_adj DESC
)
UPDATE ints_osm_members iom
  SET closest_dfo = q.frm_dfo
  FROM q
  WHERE q.int_id = iom.int_id
    AND q.roadway_gid = iom.roadway_gid;

-- Figure out the 0.1-mile closest matching segment:
UPDATE ints_osm_members iom
  SET ref_begin_01 = u01.ref_begin
  FROM uniform_segs_01mi u01
  WHERE iom.roadway_gid = u01.roadway_gid
    AND iom.lin_ref >= u01.ref_begin
    AND iom.lin_ref <= u01.ref_end;

-- Build up street names:
UPDATE ints_osm_members iom
  SET descr = COALESCE(r.ste_nam, r.ria_rte_id)
  FROM roadway_inv r
  WHERE iom.roadway_gid = r.gid
    AND iom.closest_dfo = r.frm_dfo;

-- Add street names to the intersections:
-- TODO: Will need to rerun this after Natalia finishes current stage of analysis.
WITH q AS (
  SELECT i.int_id, string_agg(iom.descr, ' & ' ORDER BY r.adt_adj DESC, iom.descr) AS descr
    FROM ints_osm i, ints_osm_members iom, roadway_inv r
    WHERE i.int_id = iom.int_id
      AND iom.roadway_gid = r.gid
      AND iom.closest_dfo = r.frm_dfo
    GROUP BY i.int_id
)
UPDATE ints_osm i
  SET descr = q.descr
  FROM q
  WHERE q.int_id = i.int_id;
```

### Matching Up Crashes

It isn't anticipated that anything other than nearest crashes are needed at the time, so the query will deal with nearest crashes only, within 100m.

```sql
-- Create the table that contains the basic information:
CREATE TABLE crash_int_osm_nearest_base (
  int_id integer REFERENCES ints_osm(int_id) ON DELETE CASCADE,
  crash_id integer REFERENCES share_crash(crash_id),
  distance real,
  PRIMARY KEY (crash_id)
);

-- Find the nearest crashes within 100m:
INSERT INTO crash_int_osm_nearest_base (int_id, crash_id, distance)
  SELECT DISTINCT ON (c.crash_id) 
    i.int_id, c.crash_id, ST_Distance(c.location, i.center, FALSE) distance
  FROM ints_osm i, share_crash c
  WHERE ST_DWithin(c.location, i.center, 100, FALSE)
  ORDER BY c.crash_id, ST_Distance(c.location, i.center, FALSE);

-- Join together geometry and key crash stats into a convenience view:
CREATE VIEW crash_int_osm_nearest AS
  SELECT c.crash_id, c.crash_date, c.crash_fatal_fl = 'Y' AS crash_fatal_fl,
    c.at_intrsct_fl = 'Y' AS at_intersct_fl, c.crash_sev_id, p.ped_crash, p.ped_fatal,
    b.int_id, b.distance, i.center, c.location, i.signal, i.junction, i.midblock_sig,
    CASE WHEN c.crash_sev_id IN (1, 4) THEN 7
         WHEN c.crash_sev_id IN (0, 2, 3, 5) THEN 1
         ELSE 0 END AS points_kabco
  FROM share_crash c, ints_osm i, crash_int_osm_nearest_base b, ped_activity p
  WHERE c.crash_id = b.crash_id
    AND c.crash_id = p.crash_id
    AND b.int_id = i.int_id;
```

This produces rankings on all intersection-related crashes around the OpenStreetMap-derived intersections:

```sql
CREATE TABLE crash_int_osm_rankings (
  int_id integer REFERENCES ints_osm(int_id) ON DELETE CASCADE,
  count_all integer NOT NULL DEFAULT 0,
  count_ped integer NOT NULL DEFAULT 0,
  count_pedfatal integer NOT NULL DEFAULT 0,
  ranking_all integer,
  ranking_ped integer,
  ranking_pedfatal integer,
  pts_all_kabco integer,
  pts_ped_kabco integer,
  on_system_count integer NOT NULL DEFAULT 0,
  dist_school real,
  dist_hospital real,
  dist_transit real,
  count_transit_025mi integer NOT NULL DEFAULT 0,
  sidewalk_len_vis real NOT NULL DEFAULT 0,
  sidewalk_len_inv real NOT NULL DEFAULT 0,
  PRIMARY KEY (int_id)
);

-- All:
WITH q AS (
  SELECT int_id, COUNT(1) crash_count, SUM(points_kabco) sum_kabco
    FROM crash_int_osm_nearest
    WHERE at_intersct_fl
    GROUP BY int_id
), r AS (
  SELECT q.int_id, q.crash_count, sum_kabco
    row_number() OVER (ORDER BY q.crash_count DESC) AS ranking
  FROM q
  WHERE q.crash_count > 0
)
INSERT INTO crash_int_osm_rankings (int_id, ranking_all, count_all, pts_all_kabco)
  SELECT r.int_id, r.ranking, r.crash_count, r.sum_kabco
  FROM r;

-- Peds:
WITH q AS (
  SELECT int_id, COUNT(1) crash_count, SUM(points_kabco) sum_kabco
    FROM crash_int_osm_nearest
    WHERE at_intersct_fl AND ped_crash
    GROUP BY int_id
), r AS (
  SELECT q.int_id, q.crash_count, sub_kabco
    row_number() OVER (ORDER BY q.crash_count DESC) AS ranking
  FROM q
  WHERE q.crash_count > 0
)
UPDATE crash_int_osm_rankings cr
  SET ranking_ped = r.ranking, count_ped = r.crash_count, pts_ped_kabco = r.sum_kabco
  FROM r
  WHERE r.int_id = cr.int_id;

-- Ped/fatal:
WITH q AS (
  SELECT int_id, COUNT(1) crash_count
    FROM crash_int_osm_nearest
    WHERE at_intersct_fl AND ped_crash AND ped_fatal > 0
    GROUP BY int_id
), r AS (
  SELECT q.int_id, q.crash_count,
    row_number() OVER (ORDER BY q.crash_count DESC) AS ranking
  FROM q
  WHERE q.crash_count > 0
)
UPDATE crash_int_osm_rankings cr
  SET ranking_pedfatal = r.ranking, count_pedfatal = r.crash_count
  FROM r
  WHERE r.int_id = cr.int_id;

-- To export:
\copy crash_int_osm_rankings TO '~/pedcrash/crash_int_osm_rankings.csv' DELIMITER ',' CSV HEADER;
```

### Intersection Approach Annotation

For further analysis, we want to collect together some key attributes about the approaches to the intersections. For simplicity, we'll only look at "the major street" and "the minor street". For each, we'll select the Roadway Inventory segment that's the closest to the intersection. We'll try to select the minor approach that's closest to 90 degrees off of the major approach.

```sql
CREATE TABLE ints_osm_approaches (
  int_id integer REFERENCES ints_osm(int_id) ON DELETE CASCADE,
  roadway_gid integer,
  major boolean, -- TRUE if the approach is a major approach
  PRIMARY KEY (int_id, major)
);

-- Find the major street for each intersection by max AADT:
INSERT INTO ints_osm_approaches (int_id, roadway_gid, major)
  SELECT DISTINCT ON (i.int_id)
    i.int_id, i.roadway_gid, TRUE major
  FROM ints_osm_members i, roadway_inv r
  WHERE i.roadway_gid = r.gid
    AND i.closest_dfo = r.frm_dfo
  ORDER BY i.int_id, r.adt_adj DESC;

-- From: https://gis.stackexchange.com/questions/78665/calculating-the-difference-between-2-angles-using-st-azimuth-and-dot-product):
CREATE OR REPLACE FUNCTION angleDiff (l1 geometry, l2 geometry)
RETURNS FLOAT AS $$
DECLARE angle1 FLOAT;
DECLARE angle2 FLOAT;
DECLARE diff FLOAT;
BEGIN
    SELECT ST_Azimuth (ST_StartPoint(l1), ST_EndPoint(l1)) INTO angle1;
    SELECT ST_Azimuth (ST_StartPoint(l2), ST_EndPoint(l2)) INTO angle2;
    SELECT degrees (angle2 - angle1) INTO diff;
    CASE
        WHEN diff > 180 THEN RETURN diff - 360;
        WHEN diff <= -180 THEN RETURN diff + 360;
        ELSE RETURN diff;
    END CASE;
END;
$$ LANGUAGE plpgsql;

CREATE TEMP TABLE ioa_work AS
  SELECT a.int_id, m2.roadway_gid, m2.ref_begin, r.adt_adj,
    abs(angleDiff(ST_Intersection(u1.geog::geometry, ST_Buffer(i.center::geography, 75)::geometry),
        ST_Intersection(u2.geog::geometry, ST_Buffer(i.center::geography, 75)::geometry))) angle
  FROM ints_osm_approaches a, ints_osm_members m1, ints_osm_members m2, ints_osm i, uniform_segs_1mi u1, uniform_segs_1mi u2, roadway_inv r
  WHERE a.int_id = m1.int_id
    AND a.roadway_gid = m1.roadway_gid
    AND a.major
    AND a.int_id = m2.int_id
    AND a.roadway_gid <> m2.roadway_gid
    AND a.int_id = i.int_id
    AND m1.roadway_gid = u1.roadway_gid
    AND m1.ref_begin = u1.ref_begin
    AND m2.roadway_gid = u2.roadway_gid
    AND m2.ref_begin = u2.ref_begin
    AND m2.roadway_gid = r.gid
    AND m2.closest_dfo = r.frm_dfo;

-- Further purge out entries that don't seem to have intersection per se (no road joining at an
-- angle greater than 5 degrees):
WITH q AS (
  SELECT int_id FROM ints_osm AS i
    WHERE NOT EXISTS(
      SELECT 1 FROM ioa_work AS w
        WHERE i.int_id = w.int_id
          AND ABS(angle - 90) <= 85
    )
    AND NOT i.midblock_sig
)
DELETE FROM ints_osm AS i
  USING q
  WHERE q.int_id = i.int_id;
-- TODO: Move this and angle queries earlier so that we don't have slow performance here.

-- Add in the minor approaches (highest AADT, plus angle must be joining greater than 5 degrees):
INSERT INTO ints_osm_approaches (int_id, roadway_gid, major)
  SELECT DISTINCT ON (int_id)
    int_id, roadway_gid, FALSE AS major
  FROM ioa_work
  WHERE ABS(angle - 90) <= 85
  ORDER BY int_id, adt_adj * (1 - (ABS(angle - 90) / 90.0)) DESC;

-- Convenience view for approaches that ties in data:
CREATE VIEW ints_osm_appch_ri AS
  SELECT a.*, m.ref_begin, m.ref_begin_01, m.closest_dfo, r.ria_rte_id, r.adt_adj, r.f_system, r.sec_bic, r.spd_max,
    r.school_zn, r.hwy_des1, r.aces_ctrl, r.med_type, r.med_wid, r.num_lanes, r.clmb_ps_la,
    r.accel_dece, r.k_fac, r.trk_aadt_p, r.desgn_yr, r.rt_turn_la, r.lt_turn_la, r.lane_width,
    r.peak_prkg, r.s_use_i
  FROM ints_osm_approaches a, ints_osm_members m, roadway_inv r
  WHERE a.int_id = m.int_id
    AND a.roadway_gid = m.roadway_gid
    AND a.roadway_gid = r.gid
    AND m.closest_dfo = r.frm_dfo;
```

If trying to match back to TxDOT Roadway Inventory, for `ints_osm_appch_ri.major` and `NOT ints_osm_appch_ri.major`, match `ints_osm_appch_ri.roadway_gid` to `roadway_inv.gid` and `ints_osm_appch_ri.closest_dfo` to `roadway_inv.frm_dfo`.

To extract materials from above and use as a shapefile:

```bash
mkdir -p ./ints_osm
pgsql2shp -f ./ints_osm/ints_osm.shp -h localhost -p 5432 -u **** -P ***** pedcrash ints_osm
zip -r -p ints_osm.zip ints_osm
mkdir -p ./crash_int_osm_nearest
pgsql2shp -f ./crash_int_osm_nearest/crash_int_osm_nearest.shp -h localhost -p 5432 -u **** -P ***** pedcrash crash_int_osm_nearest
zip -r -p crash_int_osm_nearest.zip crash_int_osm_nearest
```

Also, a CSV version of ints_osm:

```sql
\copy (SELECT int_id, signal, junction, midblock_sig, ST_Y(center::geometry) lat, ST_X(center::geometry) lon, descr FROM ints_osm) TO '~/pedcrash/ints_osm.csv' DELIMITER ',' CSV HEADER;
\copy (SELECT crash_id, crash_date, crash_fatal_fl, at_intersct_fl, crash_sev_id, ped_crash, int_id, distance, signal, junction, midblock_sig, points_kabco FROM crash_int_osm_nearest) TO '~/pedcrash/crash_int_osm_nearest.csv' DELIMITER ',' CSV HEADER;
```

To use the approach table, we'll extract out a CSV file:

```sql
\copy ints_osm_members TO '~/pedcrash/ints_osm_members.csv' DELIMITER ',' CSV HEADER;
\copy (SELECT * FROM ints_osm_appch_ri) TO '~/pedcrash/ints_osm_appch_ri.csv' DELIMITER ',' CSV HEADER;
```

#### Estimating Number of Approaches

Another analysis exercise involves incorporating the number of approaches to the intersection. Inaccuracies may be caused by nearby roads that don't actually cross the intersection, ambiguity around one-way streets, and ambiguity around divided roadways. Regardless, here's a first shot at counting approaches. We'll see for each member how many approaches we should count:

```sql
CREATE TEMP TABLE x_members AS
  WITH q AS (
    SELECT gid, MIN(frm_dfo) beginning, MAX(to_dfo) ending
    FROM roadway_inv
    GROUP BY gid
  )
  SELECT int_id, roadway_gid, lin_ref, descr,
    CASE WHEN lin_ref - beginning > 0.04 THEN 1 ELSE 0 END +
    CASE WHEN ending - lin_ref > 0.04 THEN 1 ELSE 0 END approaches
  FROM ints_osm_members, q
  WHERE roadway_gid = gid;

CREATE TEMP TABLE appch_cnt_osm AS
  SELECT int_id, SUM(approaches) approaches
  FROM x_members
  GROUP BY int_id;
\copy (SELECT i.int_id, i.signal, i.junction, i.midblock_sig, i.descr, x.approaches FROM ints_osm i, appch_cnt_osm x WHERE i.int_id = x.int_id) TO '~/pedcrash/appch_cnt_osm.csv' DELIMITER ',' CSV HEADER;
```

#### Counting Severities

To count the different crash severities for each intersection:

```sql
CREATE TEMP TABLE cs_t AS
  SELECT i.int_id, r.ranking_all, i.crash_sev_id, COUNT(1)
    FROM crash_int_osm_nearest i, crash_int_osm_rankings r
    WHERE i.int_id = r.int_id
      AND r.ranking_all IS NOT NULL
    GROUP BY r.ranking_all, i.int_id, i.crash_sev_id
    ORDER BY r.ranking_all, i.crash_sev_id;
\copy cs_t TO '~/pedcrash/severity_int_cnts.csv' DELIMITER ',' CSV HEADER;
```

For more of a cross-tabular format of this:

```sql
CREATE TEMP TABLE severities AS
SELECT 
  cionb.int_id,
  SUM(CASE WHEN sc.crash_sev_id = 0 THEN 1 ELSE 0 END) AS sev_unknown,
  SUM(CASE WHEN sc.crash_sev_id = 1 THEN 1 ELSE 0 END) AS sev_incapac,
  SUM(CASE WHEN sc.crash_sev_id = 2 THEN 1 ELSE 0 END) AS sev_nonincapac,
  SUM(CASE WHEN sc.crash_sev_id = 3 THEN 1 ELSE 0 END) AS sev_possible,
  SUM(CASE WHEN sc.crash_sev_id = 4 THEN 1 ELSE 0 END) AS sev_killed,
  SUM(CASE WHEN sc.crash_sev_id = 5 THEN 1 ELSE 0 END) AS sev_notinjured
FROM crash_int_osm_nearest_base cionb, share_crash sc
WHERE cionb.crash_id = sc.crash_id
GROUP BY cionb.int_id
ORDER BY cionb.int_id;
```

### Approach 2: Map Matching Roadways

With further coding and processing, it is possible to prevent false-positives from appearing around grade separations (e.g. busy multi-level freeway interchanges). While retrieving potential intersections and participating roadway geometry from Overpass API, it is possible to positively match up TxDOT Roadway Inventory geometry with OpenStreetMap geometry, and therefore only allow those roads to be included in the respective intersections. This invovles more coding with map-matching.

In early attempts to become familiar with solutions, the [OSMnx library](https://github.com/gboeing/osmnx) was proving extremely difficult to get up and running on my UT Windows 10 laptop. Plus, the shortest pathfinding capability in OSMnx doesn't allow for waypoints, which could potentially result in mismatches. If I revert back to the [NMC Map Matcher](https://github.com/ut-ctr-nmc/nmc-map-matcher), I may get what I want, but it would involve some more coding and debugging.
