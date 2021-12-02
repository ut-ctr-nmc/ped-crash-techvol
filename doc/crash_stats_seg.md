# Crash Stats Segments Breakdown

This document outlines the queries that are used to fill the `crash_stats_seg` table. Several queries are set up to be restricted to 2018; this was done as a diagnostic because 2018 was the first year's worth of CRIS Share data that was imported into the database. Other queries are set up to handle the entire 2010-2019 decade.

The first section has queries for the TxDOT Roadway Inventory segments as identified by the `gid` field. They can be long. It had been discovered that these segments are comprised of subsegments that all share the same `gid` field. Similar queries were run for these subsegments in attempts to identify localized statistics. These are covered in the next section below.

## Crash Stats for Segments

These are designed to fill in the `crash_stats_seg` table:
```sql
-- seg_len:
WITH q AS (
  SELECT gid roadway_gid, SUM(len_sec) seg_length
  FROM roadway_inv
  GROUP BY gid
)
UPDATE crash_stats_seg
SET seg_length = q.seg_length
FROM q
WHERE crash_stats_seg.roadway_gid = q.roadway_gid;

-- count_50_all_2018:
WITH r AS (
  SELECT roadway_gid, COUNT(1) crash_count
  FROM crash_buf_100 cb, share_crash c
  WHERE distance <= 50
    AND cb.crash_id = c.crash_id
	AND EXTRACT(YEAR FROM c.crash_date) = '2018'
  GROUP BY roadway_gid
)
UPDATE crash_stats_seg
SET count_50_all_2018 = r.crash_count
FROM r
WHERE crash_stats_seg.roadway_gid = r.roadway_gid;

-- count_50_ped_2018:
WITH r AS (
  SELECT roadway_gid, COUNT(1) crash_count
  FROM crash_buf_100 cb, ped_activity p, share_crash c
  WHERE distance <= 50
    AND cb.crash_id = p.crash_id
	AND cb.crash_id = c.crash_id
	AND p.ped_crash
	AND EXTRACT(YEAR FROM c.crash_date) = '2018'
  GROUP BY roadway_gid
)
UPDATE crash_stats_seg
SET count_50_ped_2018 = r.crash_count
FROM r
WHERE crash_stats_seg.roadway_gid = r.roadway_gid;

-- count_50_pedfatal_2018:
WITH r AS (
  SELECT roadway_gid, COUNT(1) crash_count
  FROM crash_buf_100 cb, ped_activity p, share_crash c
  WHERE distance <= 50
    AND cb.crash_id = p.crash_id
	AND cb.crash_id = c.crash_id
	AND p.ped_fatal > 0
	AND EXTRACT(YEAR FROM c.crash_date) = '2018'
  GROUP BY roadway_gid
)
UPDATE crash_stats_seg
SET count_50_pedfatal_2018 = r.crash_count
FROM r
WHERE crash_stats_seg.roadway_gid = r.roadway_gid;

-- count_50_all:
WITH r AS (
  SELECT roadway_gid, COUNT(1) crash_count
  FROM crash_buf_100 c
  WHERE distance <= 50
  GROUP BY roadway_gid
)
UPDATE crash_stats_seg
SET count_50_all = r.crash_count
FROM r
WHERE crash_stats_seg.roadway_gid = r.roadway_gid;

-- count_50_ped:
WITH r AS (
  SELECT roadway_gid, COUNT(1) crash_count
  FROM crash_buf_100 c, ped_activity p
  WHERE distance <= 50
    AND c.crash_id = p.crash_id AND p.ped_crash
  GROUP BY roadway_gid
)
UPDATE crash_stats_seg
SET count_50_ped = r.crash_count
FROM r
WHERE crash_stats_seg.roadway_gid = r.roadway_gid;

-- count_50_pedfatal:
WITH r AS (
  SELECT roadway_gid, COUNT(1) crash_count
  FROM crash_buf_100 c, ped_activity p
  WHERE distance <= 50
    AND c.crash_id = p.crash_id
	AND p.ped_fatal > 0
  GROUP BY roadway_gid
)
UPDATE crash_stats_seg
SET count_50_pedfatal = r.crash_count
FROM r
WHERE crash_stats_seg.roadway_gid = r.roadway_gid;

-- count_nearest_all_2018:
WITH r AS (
  SELECT roadway_gid, COUNT(1) crash_count
  FROM crash_buf_100 cb, share_crash c
  WHERE nearest
    AND cb.crash_id = c.crash_id
	AND EXTRACT(YEAR FROM c.crash_date) = '2018'
  GROUP BY roadway_gid
)
UPDATE crash_stats_seg
SET count_nearest_all_2018 = r.crash_count
FROM r
WHERE crash_stats_seg.roadway_gid = r.roadway_gid;

-- count_nearest_ped_2018:
WITH r AS (
  SELECT roadway_gid, COUNT(1) crash_count
  FROM crash_buf_100 cb, ped_activity p, share_crash c
  WHERE nearest
    AND cb.crash_id = p.crash_id
	AND cb.crash_id = c.crash_id
	AND p.ped_crash
	AND EXTRACT(YEAR FROM c.crash_date) = '2018'
  GROUP BY roadway_gid
)
UPDATE crash_stats_seg
SET count_nearest_ped_2018 = r.crash_count
FROM r
WHERE crash_stats_seg.roadway_gid = r.roadway_gid;

-- count_nearest_pedfatal_2018:
WITH r AS (
  SELECT roadway_gid, COUNT(1) crash_count
  FROM crash_buf_100 cb, ped_activity p, share_crash c
  WHERE nearest
    AND cb.crash_id = p.crash_id
	AND cb.crash_id = c.crash_id
	AND p.ped_fatal > 0
	AND EXTRACT(YEAR FROM c.crash_date) = '2018'
  GROUP BY roadway_gid
)
UPDATE crash_stats_seg
SET count_nearest_pedfatal_2018 = r.crash_count
FROM r
WHERE crash_stats_seg.roadway_gid = r.roadway_gid;

-- count_nearest_all:
WITH r AS (
  SELECT roadway_gid, COUNT(1) crash_count
  FROM crash_buf_100 c
  WHERE nearest
  GROUP BY roadway_gid
)
UPDATE crash_stats_seg
SET count_nearest_all = r.crash_count
FROM r
WHERE crash_stats_seg.roadway_gid = r.roadway_gid;

-- count_nearest_ped:
WITH r AS (
  SELECT roadway_gid, COUNT(1) crash_count
  FROM crash_buf_100 c, ped_activity p
  WHERE nearest
    AND c.crash_id = p.crash_id
	AND p.ped_crash
  GROUP BY roadway_gid
)
UPDATE crash_stats_seg
SET count_nearest_ped = r.crash_count
FROM r
WHERE crash_stats_seg.roadway_gid = r.roadway_gid;

-- count_nearest_pedfatal:
WITH r AS (
  SELECT roadway_gid, COUNT(1) crash_count
  FROM crash_buf_100 c, ped_activity p
  WHERE nearest
    AND c.crash_id = p.crash_id
	AND p.ped_fatal > 0
  GROUP BY roadway_gid
)
UPDATE crash_stats_seg
SET count_nearest_pedfatal = r.crash_count
FROM r
WHERE crash_stats_seg.roadway_gid = r.roadway_gid;
```

## Crash Stats for Subsegments

As described in the introduction, queries were formulated to collect statistics on subsegments. This section starts with the table definition for subsegments statistics:

```sql
CREATE TABLE crash_stats_subseg (
  roadway_gid integer,
  frm_dfo real,
  count_nearest_all integer NOT NULL DEFAULT 0,
  count_nearest_ped integer NOT NULL DEFAULT 0,
  count_nearest_pedfatal integer NOT NULL DEFAULT 0,
  PRIMARY KEY (roadway_gid, frm_dfo)
);
```

These are the definitions of the fields:
* **roadway_gid:** The `gid` value for the segment from the TxDOT Roadway Inventory
* **frm_dfo:** The linear reference that marks the start of the subsegment. The `roadway_gid`, `frm_dfo` combination make a primary key for the subsegment.
* **count_nearest_all:** This is the number of crashes that are noted as the nearest crashes for the corresponding subsegment.
* **count_nearest_ped:** This is the number of mearest ped crashes that correspond with the given subsegment.
* **count_nearest_pedfatal:** This is the number of nearest pedestrian fatalities that corresond with the given subsegment.

These queries populate the table:

```sql
-- count_nearest_all:
INSERT INTO crash_stats_subseg (roadway_gid, frm_dfo, count_nearest_all)
  SELECT roadway_gid, frm_dfo, COUNT(1) count_nearest_all
  FROM crash_buf_100 c
  WHERE nearest
  GROUP BY roadway_gid, frm_dfo;

-- count_nearest_ped:
WITH r AS (
  SELECT roadway_gid, frm_dfo, COUNT(1) crash_count
  FROM crash_buf_100 c, ped_activity p
  WHERE nearest
    AND c.crash_id = p.crash_id
	AND p.ped_crash
  GROUP BY roadway_gid, frm_dfo
)
UPDATE crash_stats_subseg
SET count_nearest_ped = r.crash_count
FROM r
WHERE crash_stats_subseg.roadway_gid = r.roadway_gid
  AND crash_stats_subseg.frm_dfo = r.frm_dfo;

-- count_nearest_pedfatal:
WITH r AS (
  SELECT roadway_gid, frm_dfo, COUNT(1) crash_count
  FROM crash_buf_100 c, ped_activity p
  WHERE nearest
    AND c.crash_id = p.crash_id
	AND p.ped_fatal > 0
  GROUP BY roadway_gid, frm_dfo
)
UPDATE crash_stats_subseg
SET count_nearest_pedfatal = r.crash_count
FROM r
WHERE crash_stats_subseg.roadway_gid = r.roadway_gid
  AND crash_stats_subseg.frm_dfo = r.frm_dfo;
```