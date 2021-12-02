# VIN Testing

## Extracting Common Make/Model Matches from CRIS

This exercise involves finding the most common linkages between VIN number clauses and the make/model information stored in CRIS.

```sql
CREATE TABLE vin_work (
  crash_id integer,
  prsn_type_id integer,
  unit_nbr integer,
  unit_desc_id integer,
  veh_parked_fl varchar,
  veh_hnr_fl varchar,
  veh_lic_state_id integer,
  vin varchar,
  veh_mod_year integer,
  veh_color_id integer,
  veh_make_id integer,
  veh_mod_id integer,
  veh_body_styl_id integer
);

\copy vin_work(crash_id, prsn_type_id, unit_nbr, unit_desc_id, veh_parked_fl, veh_hnr_fl, veh_lic_state_id, vin, veh_mod_year, veh_color_id, veh_make_id, veh_mod_id, veh_body_styl_id) FROM '~/tmp/Ped Crash Master List.csv' DELIMITER ',' CSV HEADER;

-- Match makes:
CREATE TEMP TABLE vin_make_work AS
WITH q AS (
  SELECT *, substring(vin, 2, 2) vin_make
  FROM vin_work
  WHERE length(coalesce(vin, '')) = 17
), r AS (
  SELECT veh_make_id, vin_make, count(1) cnt
  FROM q
  GROUP BY veh_make_id, vin_make
), s AS (
  SELECT q.vin_make, count(1) all_cnt
  FROM q, r
  WHERE q.vin_make = r.vin_make
  GROUP BY q.vin_make
)
SELECT DISTINCT ON (veh_make_id)
  r.veh_make_id, r.vin_make, mm.veh_make_txt, r.cnt, s.all_cnt
FROM r
LEFT JOIN lkp_make_mod mm ON r.veh_make_id = mm.veh_make_id
INNER JOIN s ON r.vin_make = s.vin_make
ORDER BY r.veh_make_id, r.cnt DESC;

\copy vin_make_work TO '~/tmp/vin_make_work.csv' DELIMITER ',' CSV HEADER;

-- Match models:
CREATE TEMP TABLE vin_model_work AS
WITH q AS (
  SELECT *, substring(vin, 4, 4) vin_model
  FROM vin_work
  WHERE length(coalesce(vin, '')) = 17
), r AS (
  SELECT q.veh_make_id, vmw.vin_make, q.veh_mod_id, q.vin_model, q.veh_body_styl_id, count(1) cnt
  FROM q, vin_make_work vmw
  WHERE q.veh_make_id = vmw.veh_make_id
  GROUP BY q.veh_make_id, vmw.vin_make, q.veh_mod_id, q.vin_model, q.veh_body_styl_id
)
SELECT DISTINCT ON (r.veh_make_id, r.veh_mod_id)
  r.veh_make_id, r.vin_make, mm.veh_make_txt, r.veh_mod_id, r.vin_model, mm.veh_mod_txt, r.veh_body_styl_id, bs.veh_body_styl_txt, cnt
FROM r
LEFT JOIN lkp_make_mod mm ON r.veh_make_id = mm.veh_make_id
LEFT JOIN lkp_bod_styl bs ON r.veh_body_styl_id = bs.veh_body_styl_id
ORDER BY r.veh_make_id, r.veh_mod_id, cnt DESC;

\copy vin_model_work TO '~/tmp/vin_model_work.csv' DELIMITER ',' CSV HEADER;
```

## IIHS Table Import and Comparison

### Part 1: The "Feb_2021" Set

The first step is to import the "Feb. 2021" IHS VIN number matches into the database. Then we can determine how many of them correspond with ped-related crashes.

I loaded "UofTexasDataRequest_Feb_2021.xlsx" into Excel and manually dropped most the safety features fields. What I have left would be represented in this table:

```sql
CREATE TABLE iihs_vin (
  VIN varchar,
  ModelYear integer,
  MakeNumber integer,
  MakeName varchar,
  SeriesNumber integer,
  SeriesName varchar,
  ModelNumber integer,
  ModelName varchar,
  CurbWeight integer,
  Wheelbase float,
  Length float,
  Width float,
  Height float,
  EngineText varchar,
  MinimumHorsepower integer,
  MaximumHorsepower integer,
  VehicleSizeID integer,
  VehicleSizeDescription varchar,
  VehicleClassID integer,
  VehicleClassDescription varchar,
  AutomobileType varchar,
  GVWRMinimum integer,
  GVWRMaximum integer,
  CheckDigit varchar,
  CollPrevent varchar
);
```

This is used to import the CSV file:

```sql
\copy iihs_vin (VIN, ModelYear, MakeNumber, MakeName, SeriesNumber, SeriesName, ModelNumber, ModelName, CurbWeight, Wheelbase, Length, Width, Height, EngineText, MinimumHorsepower, MaximumHorsepower, VehicleSizeID, VehicleSizeDescription, VehicleClassID, VehicleClassDescription, AutomobileType, GVWRMinimum, GVWRMaximum, CheckDigit, CollPrevent) FROM '~/pedcrash/UofTexasDataRequest_Feb_2021_min.csv' DELIMITER ',' CSV HEADER;
```

How many of these correspond with our actual records?

```sql
-- How many VIN numbers are there in the IIHS set?
SELECT COUNT(DISTINCT vin) FROM iihs_vin;
-- Result: 61934

-- Count how many are represented in crash data:
SELECT COUNT(DISTINCT i.vin) FROM iihs_vin i, share_unit u
  WHERE i.vin = u.vin;
-- Result: 58856
```

Now we will see how many of these correspond with ped crashes:

```sql
-- According to "ped_activity"
SELECT COUNT(DISTINCT i.vin) FROM iihs_vin i, share_unit u, ped_activity p
  WHERE i.vin = u.vin
    AND u.crash_id = p.crash_id
    AND p.ped_crash;
-- Result: 753

-- According to "harm_evnt_id = 1" in share_crash:
SELECT COUNT(DISTINCT i.vin) FROM iihs_vin i, share_unit u, share_crash c
  WHERE i.vin = u.vin
    AND u.crash_id = c.crash_id
    AND c.harm_evnt_id = 1;
-- Result: 537
```

Requesting IIHS data for ped-related crashes:

```sql
-- Create a table that has VIN numbers for ped-related crashes:
CREATE TEMP TABLE ped_vins AS
  SELECT DISTINCT u.vin FROM share_crash c, share_unit u, ped_activity p
    WHERE c.crash_id = u.crash_id
      AND c.crash_id = p.crash_id
      AND p.ped_crash;
-- That's 81283 records.

-- Remove those that are already retrieved:
DELETE FROM ped_vins v
  USING iihs_vin i
  WHERE v.vin = i.vin;
-- 753 are removed.

-- Clean out erroneous VINs:
DELETE FROM ped_vins WHERE length(vin) <> 17 OR vin IS NULL;
-- 526 are removed.

-- Export the remaining list:
\copy ped_vins (vin) TO '~/pedcrash/ped_vins_20210224.csv' DELIMITER ',' CSV HEADER;
```

### Part 2: The "Mar_2021" Set

HLDI returned the decoding from the above request quickly and I'm thankful for it. Upon opening the Excel file, I extracted out the cars tab, ignoring the following:

* 2,180 of 77,589 records where the "check digit" field is marked as "failed" on the "cars" tab, presumably because of transcription errors on those who collected the original crash record
* 418 motorcycles
* 1,998 "other insurables" which appear to include heavy trucks

Now I am going to import "VINs_Cars_UofTexasDataRequest_Mar_01_2021.csv" into the "iihs_vin" table:

```sql
\copy iihs_vin (VIN, ModelYear, MakeNumber, MakeName, SeriesNumber, SeriesName, ModelNumber, ModelName, CurbWeight, Wheelbase, Length, Width, Height, EngineText, MinimumHorsepower, MaximumHorsepower, VehicleSizeID, VehicleSizeDescription, VehicleClassID, VehicleClassDescription, AutomobileType, GVWRMinimum, GVWRMaximum, CheckDigit, CollPrevent) FROM '~/pedcrash/VINs_Cars_UofTexasDataRequest_Mar_01_2021.csv' DELIMITER ',' CSV HEADER;
```

Now we will verify how many of these correspond with ped crashes:

```sql
-- According to "ped_activity"
SELECT COUNT(DISTINCT i.vin) FROM iihs_vin i, share_unit u, ped_activity p
  WHERE i.vin = u.vin
    AND u.crash_id = p.crash_id
    AND p.ped_crash;
-- Result: 76162

-- According to "harm_evnt_id = 1" in share_crash:
SELECT COUNT(DISTINCT i.vin) FROM iihs_vin i, share_unit u, share_crash c
  WHERE i.vin = u.vin
    AND u.crash_id = c.crash_id
    AND c.harm_evnt_id = 1;
-- Result: 53540
```

