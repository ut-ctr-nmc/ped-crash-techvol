# Crash Statistics for 2010-2019

These are a collection of queries and resulting findings on crash data. Several queries are run on specific years in order to look at rough trends across the 2010-2019 decade. Other queries are run for the entire decade.

Besides the intersection-related queries below for the decade, most of these queries are intended to help in determining the number of records that have valid geometry to get an idea of feasible sample sizes for future analysis.

## Entire Decade
```sql
-- Total number of crash records:
SELECT COUNT(1) FROM share_crash;
-- That's 5,631,223 records.

-- Number of crash records with geometry:
SELECT COUNT(1) FROM share_crash WHERE location IS NOT NULL;
-- That's 4,756,671, about 84.5% of all crash records

-- Number of geolocated crashes that match to TxDOT Roadway Inventory within 100m:
SELECT COUNT(1) FROM crash_buf_100 WHERE nearest;
-- That's 4,727,643, about 84.0% of all crash records

-- Number of geolocated crashes that match to TxDOT Roadway Inventory within 100m:
SELECT COUNT(1) FROM crash_buf_100, share_crash WHERE nearest AND crash_buf_100.crash_id = share_crash.crash_id;
-- That's 4,727,643, about 84.0% of all crash records

-- Number with cleaned, "snapped" geometry:
SELECT COUNT(1) FROM share_crash WHERE latitude IS NOT NULL;
-- That's 4,654,402, about 82.7% of all crash records

-- Number with reported geometry (which presumably are the records
-- where police have recorded lat/lon?):
SELECT COUNT(1) FROM share_crash WHERE rpt_latitude IS NOT NULL;
-- That's 1,285,416

-- Number with reported geometry that is not cleaned:
SELECT COUNT(1) FROM share_crash
  WHERE rpt_latitude IS NOT NULL AND latitude IS NULL;
-- That's 102,269, about 1.8% of all records

-- Number that has no reported geometry:
SELECT COUNT(1) FROM share_crash
  WHERE rpt_latitude IS NULL AND latitude IS NULL;
-- That's 874,552, about 15.5% of all crash records

-- ** Analyzing crash value **
-- Number of crashes valued < $1K:
SELECT COUNT(1) FROM share_crash WHERE thousand_damage_fl = 'N';
-- That's 626,414, about 11% of all crash records

-- Number of crashes with geolocations:
SELECT COUNT(1) FROM share_crash WHERE thousand_damage_fl = 'N' AND latitude IS NOT NULL;
-- That's 441,934, about 70.5% of crash records < $1K

SELECT COUNT(1) FROM share_crash WHERE thousand_damage_fl = 'Y' AND latitude IS NOT NULL;
-- That's 4,212,468, about 84.2% of crash records > $1K

-- Number of crashes with reported geolocation:
SELECT COUNT(1) FROM share_crash WHERE thousand_damage_fl = 'N' AND rpt_latitude IS NOT NULL;
-- That's 109,565, about 17.5% of crash records < $1K

SELECT COUNT(1) FROM share_crash WHERE thousand_damage_fl = 'Y' AND rpt_latitude IS NOT NULL;
-- That's 1,175,851, about 23.5% of crash records > $1K

-- Number of "ped harmful event" crashes:
SELECT COUNT(1) FROM share_crash WHERE harm_evnt_id = 1;
-- That's 66,245, about 1.1% of all crash records.

SELECT COUNT(1) FROM share_crash WHERE harm_evnt_id = 1 AND thousand_damage_fl = 'N';
-- That's 36,349, about 54.9% of all "ped harmful event" crash records. That implies 29,896 that are above $1K.

-- Number of "ped harmful event" crashes with geolocations:
SELECT COUNT(1) FROM share_crash WHERE harm_evnt_id = 1 AND thousand_damage_fl = 'N' AND latitude IS NOT NULL;
-- That's 23,327, about 64.2% of "ped harmful event" crash records < $1K

SELECT COUNT(1) FROM share_crash WHERE harm_evnt_id = 1 AND thousand_damage_fl = 'Y' AND latitude IS NOT NULL;
-- That's 23,135, about 77.4% of "ped harmful event" crash records > $1K

-- Total number of ped crashes:
SELECT COUNT(1) FROM share_crash, ped_activity WHERE share_crash.crash_id = ped_activity.crash_id AND ped_crash;
-- That's 78,497, 1.4% of all crash records

-- Number of cleaned, "snapped" ped crashes:
SELECT COUNT(1) FROM share_crash, ped_activity
  WHERE latitude IS NOT NULL
    AND share_crash.crash_id = ped_activity.crash_id
    AND ped_activity.ped_crash;
-- That's 55,912, which is about 71.2% of all ped crashes.

-- Number of reported geometry ped crashes:
SELECT COUNT(1) FROM share_crash, ped_activity
  WHERE rpt_latitude IS NOT NULL
    AND share_crash.crash_id = ped_activity.crash_id
    AND ped_activity.ped_crash;
-- That's 12,030, which is about 15.3% of all ped crashes.

-- Number of reported geometry that is not cleaned for ped crashes:
SELECT COUNT(1) FROM share_crash, ped_activity
  WHERE latitude IS NULL AND rpt_latitude IS NOT NULL
    AND share_crash.crash_id = ped_activity.crash_id
    AND ped_activity.ped_crash;
-- That's 2,252, which is about 2.9% of all ped crashes.

-- Number of ped crashes that have no reported geometry:
SELECT COUNT(1) FROM share_crash, ped_activity
  WHERE rpt_latitude IS NULL AND latitude IS NULL
    AND share_crash.crash_id = ped_activity.crash_id
    AND ped_activity.ped_crash;
-- That's 20,333, which is about 25.9% of all ped crashes.
```

### Intersection-Related Statistics
These queries leverage the `at_intrsct_fl` field that's found in the CRIS Share data, which is a field that is intended to identify whether the crash is an intersection crash.

```sql
-- Total number of crash records marked at intersections:
SELECT COUNT(1) FROM share_crash WHERE at_intrsct_fl = 'Y';
-- That's 1,580,581, which is 28.1% of all crash records.

-- Total number of ped crashes marked at intersections:
SELECT COUNT(1) FROM share_crash, ped_activity
  WHERE share_crash.crash_id = ped_activity.crash_id AND ped_crash
    AND share_crash.at_intrsct_fl = 'Y';
-- That's 18,265, which is 23.3% of all ped crash records.

-- Number of fatal ped crashes that happen at intersections:
SELECT COUNT(1) FROM share_crash, ped_activity
  WHERE share_crash.crash_id = ped_activity.crash_id
    AND ped_crash AND ped_fatal > 0
    AND share_crash.at_intrsct_fl = 'Y';
-- That's 554, which is about 0.7% of all ped crash records.
```

## Statistics for 2011
```sql
-- Total number of crash records for 2011:
SELECT COUNT(1) FROM share_crash WHERE EXTRACT(YEAR FROM crash_date) = '2011';
-- That's 456,149

-- Number of crash records with geometry:
SELECT COUNT(1) FROM share_crash WHERE location IS NOT NULL AND EXTRACT(YEAR FROM crash_date) = '2011';
-- That's 357,678, about 78.4% of all crash records

-- Number of geolocated crashes that match to TxDOT Roadway Inventory within 100m:
SELECT COUNT(1) FROM crash_buf_100, share_crash WHERE nearest AND crash_buf_100.crash_id = share_crash.crash_id AND EXTRACT(YEAR FROM crash_date) = '2011';
-- That's 355,089, about 77.8% of all crash records

-- Number with cleaned, "snapped" geometry:
SELECT COUNT(1) FROM share_crash WHERE latitude IS NOT NULL AND EXTRACT(YEAR FROM crash_date) = '2011';
-- That's 351,370, about 77% of all crash records

-- Number with reported geometry (which presumably are the records
-- where police have recorded lat/lon?):
SELECT COUNT(1) FROM share_crash WHERE rpt_latitude IS NOT NULL AND EXTRACT(YEAR FROM crash_date) = '2011';
-- That's 88,805

-- Number with reported geometry that is not cleaned:
SELECT COUNT(1) FROM share_crash
  WHERE rpt_latitude IS NOT NULL AND latitude IS NULL AND EXTRACT(YEAR FROM crash_date) = '2011';
-- That's 6,308, about 1.4% of all records

-- Number that has no reported geometry:
SELECT COUNT(1) FROM share_crash
  WHERE rpt_latitude IS NULL AND latitude IS NULL AND EXTRACT(YEAR FROM crash_date) = '2011';
-- That's 98,471, about 21.6% of all crash records

-- Total number of ped crashes for 2011:
SELECT COUNT(1) FROM share_crash, ped_activity WHERE share_crash.crash_id = ped_activity.crash_id AND ped_crash AND EXTRACT(YEAR FROM crash_date) = '2011';
-- That's 6,174

-- Number of cleaned, "snapped" ped crashes:
SELECT COUNT(1) FROM share_crash, ped_activity
  WHERE latitude IS NOT NULL
    AND share_crash.crash_id = ped_activity.crash_id
    AND ped_activity.ped_crash AND EXTRACT(YEAR FROM crash_date) = '2011';
-- That's 4,258, which is about 69% of all ped crashes.

-- Number of reported geometry ped crashes:
SELECT COUNT(1) FROM share_crash, ped_activity
  WHERE rpt_latitude IS NOT NULL
    AND share_crash.crash_id = ped_activity.crash_id
    AND ped_activity.ped_crash AND EXTRACT(YEAR FROM crash_date) = '2011';
-- That's 782, which is about 12.7% of all ped crashes.

-- Number of reported geometry that is not cleaned for ped crashes:
SELECT COUNT(1) FROM share_crash, ped_activity
  WHERE latitude IS NULL AND rpt_latitude IS NOT NULL
    AND share_crash.crash_id = ped_activity.crash_id
    AND ped_activity.ped_crash AND EXTRACT(YEAR FROM crash_date) = '2011';
-- That's 115, which is about 1.9% of all ped crashes.

-- Number of ped crashes that have no reported geometry:
SELECT COUNT(1) FROM share_crash, ped_activity
  WHERE rpt_latitude IS NULL AND latitude IS NULL
    AND share_crash.crash_id = ped_activity.crash_id
    AND ped_activity.ped_crash AND EXTRACT(YEAR FROM crash_date) = '2011';
-- That's 1801, which is about 29.2% of all ped crashes.
```

## Statistics for 2019
```sql
-- Total number of crash records for 2019:
SELECT COUNT(1) FROM share_crash WHERE EXTRACT(YEAR FROM crash_date) = '2019';
-- That's 647,937

-- Number of crash records with geometry:
SELECT COUNT(1) FROM share_crash WHERE location IS NOT NULL AND EXTRACT(YEAR FROM crash_date) = '2019';
-- That's 569,834, about 87.9% of all crash records

-- Number of geolocated crashes that match to TxDOT Roadway Inventory within 100m:
SELECT COUNT(1) FROM crash_buf_100, share_crash WHERE nearest AND crash_buf_100.crash_id = share_crash.crash_id AND EXTRACT(YEAR FROM crash_date) = '2019';
-- That's 567,589, about 87.6% of all crash records

-- Number with cleaned, "snapped" geometry:
SELECT COUNT(1) FROM share_crash WHERE latitude IS NOT NULL AND EXTRACT(YEAR FROM crash_date) = '2019';
-- That's 562,462, about 86.8% of all crash records

-- Number with reported geometry (which presumably are the records
-- where police have recorded lat/lon?):
SELECT COUNT(1) FROM share_crash WHERE rpt_latitude IS NOT NULL AND EXTRACT(YEAR FROM crash_date) = '2019';
-- That's 130,095

-- Number with reported geometry that is not cleaned:
SELECT COUNT(1) FROM share_crash
  WHERE rpt_latitude IS NOT NULL AND latitude IS NULL AND EXTRACT(YEAR FROM crash_date) = '2019';
-- That's 7,372, about 1.1% of all records

-- Number that has no reported geometry:
SELECT COUNT(1) FROM share_crash
  WHERE rpt_latitude IS NULL AND latitude IS NULL AND EXTRACT(YEAR FROM crash_date) = '2019';
-- That's 78,103, about 12.1% of all crash records

-- Total number of ped crashes for 2019:
SELECT COUNT(1) FROM share_crash, ped_activity WHERE share_crash.crash_id = ped_activity.crash_id AND ped_crash AND EXTRACT(YEAR FROM crash_date) = '2019';
-- That's 9,059

-- Number of cleaned, "snapped" ped crashes:
SELECT COUNT(1) FROM share_crash, ped_activity
  WHERE latitude IS NOT NULL
    AND share_crash.crash_id = ped_activity.crash_id
    AND ped_activity.ped_crash AND EXTRACT(YEAR FROM crash_date) = '2019';
-- That's 6,561, which is about 72.4% of all ped crashes.

-- Number of reported geometry ped crashes:
SELECT COUNT(1) FROM share_crash, ped_activity
  WHERE rpt_latitude IS NOT NULL
    AND share_crash.crash_id = ped_activity.crash_id
    AND ped_activity.ped_crash AND EXTRACT(YEAR FROM crash_date) = '2019';
-- That's 1,194, which is about 13.2% of all ped crashes.

-- Number of reported geometry that is not cleaned for ped crashes:
SELECT COUNT(1) FROM share_crash, ped_activity
  WHERE latitude IS NULL AND rpt_latitude IS NOT NULL
    AND share_crash.crash_id = ped_activity.crash_id
    AND ped_activity.ped_crash AND EXTRACT(YEAR FROM crash_date) = '2019';
-- That's 243, which is about 2.7% of all ped crashes.

-- Number of ped crashes that have no reported geometry:
SELECT COUNT(1) FROM share_crash, ped_activity
  WHERE rpt_latitude IS NULL AND latitude IS NULL
    AND share_crash.crash_id = ped_activity.crash_id
    AND ped_activity.ped_crash AND EXTRACT(YEAR FROM crash_date) = '2019';
-- That's 2,255, which is about 24.9% of all ped crashes.
```

## Special Pedestrian Statistics

```sql
-- Finding out whether the "damage area" applies to the person:
SELECT COUNT(1)
  FROM share_crash c, share_unit u
  WHERE u.crash_id = c.crash_id
    AND c.obj_struck_id = 1 -- Pedestrian
    AND u.unit_desc_id = 4 -- Pedestrian
    AND u.veh_dmag_area_1_id IS NOT NULL;
-- Answer: None

-- What about "damage severity"?:
SELECT COUNT(1)
  FROM share_crash c, share_unit u
  WHERE u.crash_id = c.crash_id
    AND c.harm_evnt_id = 1 -- Pedestrian
    AND u.unit_desc_id = 4 -- Pedestrian
    AND u.veh_dmag_scl_1_id IS NOT NULL;
-- Answer: None

-- Utilizing person record:
-- (With or without vehicle damage reported):
WITH q AS (
SELECT DISTINCT ON (c.crash_id) c.crash_id, u1.unit_nbr, p1.prsn_nbr, c.obj_struck_id, c.othr_factr_id, c.fhe_collsn_id, p1.prsn_injry_sev_id, p1.prsn_type_id
  FROM share_crash c, share_unit u1, share_allperson p1
  WHERE u1.crash_id = c.crash_id
    AND p1.crash_id = c.crash_id
    AND p1.unit_nbr = u1.unit_nbr
    AND c.harm_evnt_id = 1
    AND u1.unit_desc_id = 4
  ORDER BY c.crash_id, p1.prsn_injry_sev_id DESC
)
SELECT COUNT(1) FROM q;
-- That's 66245

-- (With vehicle damage reported):
WITH q AS (
SELECT DISTINCT ON (c.crash_id) c.crash_id, u1.unit_nbr, u2.unit_nbr veh_unit_nbr, p1.prsn_nbr, c.obj_struck_id, c.othr_factr_id, c.fhe_collsn_id, p1.prsn_injry_sev_id, p1.prsn_type_id, u2.veh_dmag_area_1_id, u2.veh_dmag_scl_1_id, u2.force_dir_1_id
  FROM share_crash c, share_unit u1, share_unit u2, share_allperson p1
  WHERE u1.crash_id = c.crash_id
    AND u2.crash_id = c.crash_id
    AND p1.crash_id = c.crash_id
    AND p1.unit_nbr = u1.unit_nbr
    AND u1.unit_nbr <> u2.unit_nbr
    AND c.harm_evnt_id = 1
    AND u1.unit_desc_id = 4
    AND u2.unit_desc_id <> 4
    AND u2.veh_dmag_area_1_id IS NOT NULL
  ORDER BY c.crash_id, p1.prsn_injry_sev_id DESC, u2.unit_nbr
)
SELECT COUNT(1) FROM q;
-- That's 51721

-- In-between; a vehicle and pedestrian are reported, damage need not be present.
WITH q AS (
SELECT DISTINCT ON (c.crash_id) c.crash_id, u1.unit_nbr, u2.unit_nbr veh_unit_nbr, p1.prsn_nbr, c.obj_struck_id, c.othr_factr_id, c.fhe_collsn_id, p1.prsn_injry_sev_id, p1.prsn_type_id, u2.veh_dmag_area_1_id, u2.veh_dmag_scl_1_id, u2.force_dir_1_id
  FROM share_crash c, share_unit u1, share_unit u2, share_allperson p1
  WHERE u1.crash_id = c.crash_id
    AND u2.crash_id = c.crash_id
    AND p1.crash_id = c.crash_id
    AND p1.unit_nbr = u1.unit_nbr
    AND u1.unit_nbr <> u2.unit_nbr
    AND c.harm_evnt_id = 1
    AND u1.unit_desc_id = 4
    AND u2.unit_desc_id <> 4
  ORDER BY c.crash_id, p1.prsn_injry_sev_id DESC, u2.unit_nbr
)
SELECT COUNT(1) FROM q;
-- That's 66245 again.

-- Finding out whether the "damage area" applies to the vehicle:
WITH q AS (
SELECT DISTINCT ON (c.crash_id) c.crash_id, u2.veh_dmag_area_1_id
  FROM share_crash c, share_unit u1, share_unit u2
  WHERE u1.crash_id = c.crash_id
    AND u2.crash_id = c.crash_id
    AND u1.unit_nbr <> u2.unit_nbr
    AND c.harm_evnt_id = 1
    AND u1.unit_desc_id = 4
    AND u2.unit_desc_id <> 4
    AND u2.veh_dmag_area_1_id IS NOT NULL
  ORDER BY c.crash_id, u2.unit_nbr
)
SELECT COUNT(1) FROM q;
-- There's 51721 records.

-- How many of each damage area ID?
WITH q AS (
SELECT DISTINCT ON (c.crash_id) c.crash_id, u2.veh_dmag_area_1_id
  FROM share_crash c, share_unit u1, share_unit u2
  WHERE u1.crash_id = c.crash_id
    AND u2.crash_id = c.crash_id
    AND u1.unit_nbr <> u2.unit_nbr
    AND c.harm_evnt_id = 1
    AND u1.unit_desc_id = 4
    AND u2.unit_desc_id <> 4
    AND u2.veh_dmag_area_1_id IS NOT NULL
  ORDER BY c.crash_id, u2.unit_nbr
)
SELECT veh_dmag_area_1_id, COUNT(1) FROM q
  GROUP BY veh_dmag_area_1_id
  ORDER BY veh_dmag_area_1_id;

-- How many with each severity level?
WITH q AS (
SELECT DISTINCT ON (c.crash_id) c.crash_id, u2.veh_dmag_area_1_id, u2.veh_dmag_scl_1_id
  FROM share_crash c, share_unit u1, share_unit u2
  WHERE u1.crash_id = c.crash_id
    AND u2.crash_id = c.crash_id
    AND u1.unit_nbr <> u2.unit_nbr
    AND c.harm_evnt_id = 1
    AND u1.unit_desc_id = 4
    AND u2.unit_desc_id <> 4
    AND u2.veh_dmag_area_1_id IS NOT NULL
  ORDER BY c.crash_id, u2.unit_nbr
)
SELECT veh_dmag_area_1_id, veh_dmag_scl_1_id, COUNT(1) FROM q
  GROUP BY veh_dmag_area_1_id, veh_dmag_scl_1_id
  ORDER BY veh_dmag_area_1_id, veh_dmag_scl_1_id;
```

This query will attempt to isolate all of the records that can help with understanding pedestrian strikes.

```sql
CREATE TABLE ped_severity AS
WITH q AS (
SELECT DISTINCT ON (c.crash_id) c.crash_id, u1.unit_nbr, u2.unit_nbr veh_unit_nbr, p1.prsn_nbr, c.obj_struck_id, c.othr_factr_id, c.fhe_collsn_id, p1.prsn_injry_sev_id, p1.prsn_type_id, u2.veh_dmag_area_1_id, u2.veh_dmag_scl_1_id, u2.force_dir_1_id
  FROM share_crash c, share_unit u1, share_unit u2, share_allperson p1
  WHERE u1.crash_id = c.crash_id
    AND u2.crash_id = c.crash_id
    AND p1.crash_id = c.crash_id
    AND p1.unit_nbr = u1.unit_nbr
    AND u1.unit_nbr <> u2.unit_nbr
    AND c.harm_evnt_id = 1
    AND u1.unit_desc_id = 4
    AND u2.unit_desc_id <> 4
  ORDER BY c.crash_id, p1.prsn_injry_sev_id DESC, u2.unit_nbr
), v AS (
  SELECT c.crash_id, COUNT(1) veh_units
  FROM q, share_crash c, share_unit u
  WHERE q.crash_id = c.crash_id
    AND q.crash_id = u.crash_id
    AND u.unit_desc_id <> 4
  GROUP BY c.crash_id
), p AS (
  SELECT c.crash_id, COUNT(1) ped_units
  FROM q, share_crash c, share_unit u
  WHERE q.crash_id = c.crash_id
    AND q.crash_id = u.crash_id
    AND u.unit_desc_id = 4
  GROUP BY c.crash_id
)
SELECT q.*, u.veh_body_styl_id, bs.veh_body_styl_txt, u.veh_mod_year, u.veh_color_id, vc.veh_color_txt, u.veh_make_id, mm.veh_make_txt, u.veh_mod_id, mm.veh_mod_txt, v.veh_units, p.ped_units
FROM q, share_unit u
LEFT JOIN lkp_bod_styl bs ON u.veh_body_styl_id = bs.veh_body_styl_id
LEFT JOIN lkp_veh_color vc ON u.veh_color_id = vc.veh_color_id
LEFT JOIN lkp_make_mod mm ON u.veh_make_id = mm.veh_make_id AND u.veh_mod_id = mm.veh_mod_id
INNER JOIN v ON u.crash_id = v.crash_id
INNER JOIN p ON u.crash_id = p.crash_id
WHERE q.crash_id = u.crash_id
  AND q.veh_unit_nbr = u.unit_nbr;

\copy ped_severity TO '~/ped_severity.csv' DELIMITER ',' CSV HEADER;
```

### Statistics Around Ped Severity

```sql
-- Total ped crashes per the "ped_activity" table:
-- Remember, there are 4 criteria that warrant an entry to this table, which
-- includes "pedestrian-involved" crashes including swerving to avoid.
SELECT COUNT(1) FROM ped_activity WHERE ped_crash;
-- That's 78996

-- Total ped crashes per the "ped_severity" table:
-- Remember, all of these crashes have "pedestrian" as the "harmful event".
SELECT COUNT(1) FROM ped_severity;
-- That's 66245

-- Intersection crashes per crashes that appear in "ped_severity":
SELECT COUNT(1) FROM ped_severity p, share_crash c
  WHERE c.crash_id = p.crash_id
    AND c.at_intrsct_fl = 'Y';
-- That's 15922

-- Intersection ped crashes that are fatal:
SELECT COUNT(1) FROM ped_severity p, share_crash c
  WHERE c.crash_id = p.crash_id
    AND c.at_intrsct_fl = 'Y'
    AND p.prsn_injry_sev_id = 4;
-- That's 552

-- Non-intersection ped crashes that are fatal:
SELECT COUNT(1) FROM ped_severity p, share_crash c
  WHERE c.crash_id = p.crash_id
    AND c.at_intrsct_fl = 'N'
    AND p.prsn_injry_sev_id = 4;
-- That's 4533

-- Intersection ped crashes that are confirmed or suspected as injurious:
SELECT COUNT(1) FROM ped_severity p, share_crash c
  WHERE c.crash_id = p.crash_id
    AND c.at_intrsct_fl = 'Y'
    AND p.prsn_injry_sev_id IN (1, 2);
-- That's 7596

-- Non-intersection crashes that are confirmed or suspected as injurious:
SELECT COUNT(1) FROM ped_severity p, share_crash c
  WHERE c.crash_id = p.crash_id
    AND c.at_intrsct_fl = 'N'
    AND p.prsn_injry_sev_id IN (1, 2);
-- That's 24186

-- Crashes happening within proximity of cluster:
-- TODO: TBD
```

**TODO:** (From 2/9 e-mail:) To get those that are in close proximity to clusters, I need to rerun the clusters. The database that the cluster results were in went down. Natalia, Max and I had talked about better ways of considering corridors, and if we have doubt on the accuracy of "at_intrsct_fl", I want to also add some smarts to the cluster matching to try to reference cluster centers to intersection locations as found in the TxDOT Roadway Inventory. We should have a better idea of the accuracy of "at_intrsct_fl" then.

## Data Integrity Check Queries

As of Jan. 27, 2021 it was discovered that Unit Data is missing Dec. 2018. Data integrity check queries:

```sql
-- Overall number of connections. Some are double-counted:
SELECT EXTRACT(YEAR FROM c.crash_date), EXTRACT(MONTH FROM c.crash_date), COUNT(1)
  FROM share_crash c, share_allperson p, share_unit u
  WHERE c.crash_id = p.crash_id
    AND c.crash_id = u.crash_id
    AND u.unit_nbr = p.unit_nbr
  GROUP BY EXTRACT(YEAR FROM c.crash_date), EXTRACT(MONTH FROM c.crash_date)
  ORDER BY EXTRACT(YEAR FROM c.crash_date), EXTRACT(MONTH FROM c.crash_date);

-- Check for orphan units:
SELECT DISTINCT crash_id FROM share_unit u
  WHERE NOT EXISTS (
    SELECT 1 FROM share_crash
      WHERE crash_id = u.crash_id
  )
ORDER BY crash_id;

-- Check for unit-less crash records:
SELECT crash_id, crash_date FROM share_crash c
  WHERE NOT EXISTS (
    SELECT 1 FROM share_unit
      WHERE crash_id = c.crash_id
  )
ORDER BY crash_date, crash_id;

-- Check for orphan person records (e.g. those that don't have a unit):
SELECT crash_id, unit_nbr, prsn_nbr FROM share_allperson p
  WHERE NOT EXISTS (
    SELECT 1 FROM share_unit
      WHERE crash_id = p.crash_id
        AND unit_nbr = p.unit_nbr
  )
ORDER BY crash_id, unit_nbr, prsn_nbr;

-- Check for orphan person records (e.g. those that don't have a crash record):
SELECT crash_id, unit_nbr, prsn_nbr FROM share_allperson p
  WHERE NOT EXISTS (
    SELECT 1 FROM share_crash
      WHERE crash_id = p.crash_id
  )
ORDER BY crash_id, unit_nbr, prsn_nbr;
```