# Other Lookup Tables

This document covers analyses around other lookups-- specifically make/model and color for now.

## Database Creation and Initialization

Table "lkp_make_mod" contains the information that's in the "veh_mod_lkp" page in the CRIS table definitions. The snippet shows PSQL commands to create and populate the lookup table:

```sql
CREATE TABLE lkp_make_mod (
    veh_mod_id integer,
    veh_make_id integer,
    veh_mod_txt varchar,
    veh_make_txt varchar,
    PRIMARY KEY (veh_make_id, veh_mod_id)
);
\copy lkp_make_mod(veh_mod_id, veh_make_id, veh_mod_txt, veh_make_txt) FROM '~/pedcrash/veh_mod_lkp.csv' DELIMITER ',' CSV HEADER;
INSERT INTO lkp_make_mod (veh_mod_id, veh_make_id, veh_mod_txt, veh_make_txt)
    VALUES (0, 0, 'Undefined', 'Undefined');
```

Table "lkp_bod_styl" contains the "veh_bod_styl_lkp" CRIS table definition contents.

```sql
CREATE TABLE lkp_bod_styl (
    veh_body_styl_id integer PRIMARY KEY,
    veh_body_styl_txt varchar
);
\copy lkp_bod_styl(veh_body_styl_id, veh_body_styl_txt) FROM '~/pedcrash/veh_bod_styl_lkp.csv' DELIMITER ',' CSV HEADER;
```

Table "lkp_veh_color" contains the "veh_color_lkp" CRIS table definition contents.

```sql
CREATE TABLE lkp_veh_color (
    veh_color_id integer PRIMARY KEY,
    veh_color_txt varchar
);
\copy lkp_veh_color(veh_color_id, veh_color_txt) FROM '~/pedcrash/lkp_color.csv' DELIMITER ',' CSV HEADER;
INSERT INTO lkp_veh_color (veh_color_id, veh_color_txt)
    VALUES (0, 'Undefined');
```

## Analyzing With These Lookups

> **TODO:** Find out if the first vehicle unit is more likely the primary cause of the crash.

```sql
-- Total cars/light trucks in the database 2010-2019:
SELECT COUNT(1) FROM share_unit u
    WHERE u.unit_desc_id = 1 -- Vehicle
      AND u.veh_cmv_fl = 'N' OR u.cmv_veh_type_id IN (1, 2); -- Car or light truck
-- Result: 10284221

-- Total cars/light trucks that are involved in ped-related crashes:
SELECT COUNT(1) FROM share_unit u, ped_activity p
    WHERE u.unit_desc_id = 1 -- Vehcile
      AND (u.veh_cmv_fl = 'N' OR u.cmv_veh_type_id IN (1, 2)) -- Car or light truck
      AND p.crash_id = u.crash_id
      AND p.ped_crash;
-- Result: 92416

-- Total number of crash incidents where cars/light trucks are involved in ped injuries.
-- (We're picking the first ped and vehicle combination for each eligible crash ID):
WITH q AS (
    SELECT DISTINCT ON (c.crash_id)
        c.crash_id, u1.unit_nbr first_ped_unit, u2.unit_nbr first_veh_unit
    FROM share_crash c, share_unit u1, share_unit u2, share_allperson p1
    WHERE u1.crash_id = c.crash_id
      AND p1.crash_id = c.crash_id
      AND p1.unit_nbr = u1.unit_nbr
      AND u1.unit_desc_id = 4 -- Pedestrian
      AND p1.prsn_injry_sev_id IN (1, 2, 3, 4) -- Severe enough
      AND u2.crash_id = c.crash_id
      AND u2.unit_desc_id = 1 -- Vehicle
      AND (u2.veh_cmv_fl = 'N' OR u2.cmv_veh_type_id IN (1, 2)) -- Car or light truck
    ORDER BY c.crash_id, u1.unit_nbr + u2.unit_nbr
)
SELECT COUNT(1) FROM q;
-- Result: 66395
```

Now for aggregating numbers of makes/models/colors and body types:

```sql
-- Top cars/light truck makes/models/colors in database 2010-2019:
create temp table t as
SELECT m.veh_make_txt, m.veh_mod_txt, c.veh_color_txt, COUNT(1) quantity
    FROM share_unit u, lkp_make_mod m, lkp_veh_color c
    WHERE u.unit_desc_id = 1 -- Vehicle
      AND (u.veh_cmv_fl = 'N' OR u.cmv_veh_type_id IN (1, 2))
      AND u.veh_make_id = m.veh_make_id
      AND u.veh_mod_id = m.veh_mod_id
      AND COALESCE(u.veh_color_id, 0) = c.veh_color_id
    GROUP BY m.veh_make_txt, m.veh_mod_txt, c.veh_color_txt
    ORDER BY COUNT(1) DESC;
\copy t to '~/pedcrash/all_makes_models_colors.csv' delimiter ',' csv header;
drop table t;

-- Body type classifier:
create temp table t as
SELECT b.veh_body_styl_txt, COUNT(1) quantity
    FROM share_unit u, lkp_bod_styl b
    WHERE u.unit_desc_id = 1 -- Vehicle
      AND (u.veh_cmv_fl = 'N' OR u.cmv_veh_type_id IN (1, 2))
      AND u.veh_body_styl_id = b.veh_body_styl_id
    GROUP BY b.veh_body_styl_txt
    ORDER BY COUNT(1) DESC;
\copy t to '~/pedcrash/all_bodstyl.csv' delimiter ',' csv header;
drop table t;

-- Top cars/light truck makes/models/colors in database for crash incidents
-- where first car/light truck is involved in ped injury
create temp table t as
WITH q AS (
    SELECT DISTINCT ON (c.crash_id)
        c.crash_id, u1.unit_nbr first_ped_unit, u2.unit_nbr first_veh_unit,
            u2.veh_make_id, u2.veh_mod_id, u2.veh_body_styl_id, u2.veh_color_id
    FROM share_crash c, share_unit u1, share_unit u2, share_allperson p1
    WHERE u1.crash_id = c.crash_id
      AND p1.crash_id = c.crash_id
      AND p1.unit_nbr = u1.unit_nbr
      AND u1.unit_desc_id = 4 -- Pedestrian
      AND p1.prsn_injry_sev_id IN (1, 2, 3, 4) -- Severe enough
      AND u2.crash_id = c.crash_id
      AND u2.unit_desc_id = 1 -- Vehicle
      AND (u2.veh_cmv_fl = 'N' OR u2.cmv_veh_type_id IN (1, 2)) -- Car or light truck
    ORDER BY c.crash_id, u1.unit_nbr + u2.unit_nbr
)
SELECT m.veh_make_txt, m.veh_mod_txt, c.veh_color_txt, COUNT(1) quantity
    FROM q, lkp_make_mod m, lkp_veh_color c
    WHERE q.veh_make_id = m.veh_make_id
      AND q.veh_mod_id = m.veh_mod_id
      AND COALESCE(q.veh_color_id, 0) = c.veh_color_id
    GROUP BY m.veh_make_txt, m.veh_mod_txt, c.veh_color_txt
    ORDER BY COUNT(1) DESC;
\copy t to '~/pedcrash/ped_inj_make_model_color.csv' delimiter ',' csv header;
drop table t;

-- Body type classifier:
create temp table t as
WITH q AS (
    SELECT DISTINCT ON (c.crash_id)
        c.crash_id, u1.unit_nbr first_ped_unit, u2.unit_nbr first_veh_unit,
            u2.veh_make_id, u2.veh_mod_id, u2.veh_body_styl_id, u2.veh_color_id
    FROM share_crash c, share_unit u1, share_unit u2, share_allperson p1
    WHERE u1.crash_id = c.crash_id
      AND p1.crash_id = c.crash_id
      AND p1.unit_nbr = u1.unit_nbr
      AND u1.unit_desc_id = 4 -- Pedestrian
      AND p1.prsn_injry_sev_id IN (1, 2, 3, 4) -- Severe enough
      AND u2.crash_id = c.crash_id
      AND u2.unit_desc_id = 1 -- Vehicle
      AND (u2.veh_cmv_fl = 'N' OR u2.cmv_veh_type_id IN (1, 2)) -- Car or light truck
    ORDER BY c.crash_id, u1.unit_nbr + u2.unit_nbr
)
SELECT b.veh_body_styl_txt, COUNT(1) quantity
    FROM q, lkp_bod_styl b
    WHERE q.veh_body_styl_id = b.veh_body_styl_id
    GROUP BY b.veh_body_styl_txt
    ORDER BY COUNT(1) DESC;
\copy t to '~/pedcrash/ped_inj_bodstyl.csv' delimiter ',' csv header;
drop table t;
```

This is to help in seeing what the majority reported body styles are for each vehicle type.

```sql
create temp table t as
SELECT m.veh_make_txt, m.veh_mod_txt, b.veh_body_styl_txt, COUNT(1) quantity
    FROM share_unit u, lkp_make_mod m, lkp_bod_styl b
    WHERE u.unit_desc_id = 1 -- Vehicle
      AND (u.veh_cmv_fl = 'N' OR u.cmv_veh_type_id IN (1, 2))
      AND u.veh_make_id = m.veh_make_id
      AND u.veh_mod_id = m.veh_mod_id
      AND COALESCE(u.veh_body_styl_id, 0) = b.veh_body_styl_id
    GROUP BY m.veh_make_txt, m.veh_mod_txt, b.veh_body_styl_txt
    ORDER BY COUNT(1) DESC;
\copy t to '~/pedcrash/make_model_bodystyl.csv' delimiter ',' csv header;
drop table t;
```

All crashes involving a pedestrian injury (severity 1-4) grouped by make, model, body style, year of crash, fatality, and vehicle strike location.

```sql
create temp table t as
WITH q AS (
    SELECT DISTINCT ON (c.crash_id)
        c.crash_id, EXTRACT(YEAR FROM c.crash_date) crash_year, c.crash_fatal_fl = 'Y' AS fatality,
            u1.unit_nbr first_ped_unit, u2.unit_nbr first_veh_unit, u2.veh_make_id,
            u2.veh_mod_id, u2.veh_body_styl_id, u2.veh_color_id, u2.veh_dmag_area_1_id
    FROM share_crash c, share_unit u1, share_unit u2, share_allperson p1
    WHERE u1.crash_id = c.crash_id
      AND p1.crash_id = c.crash_id
      AND p1.unit_nbr = u1.unit_nbr
      AND u1.unit_desc_id = 4 -- Pedestrian
      AND p1.prsn_injry_sev_id IN (1, 2, 3, 4) -- Severe enough
      AND u2.crash_id = c.crash_id
      AND u2.unit_desc_id = 1 -- Vehicle
      AND (u2.veh_cmv_fl = 'N' OR u2.cmv_veh_type_id IN (1, 2)) -- Car or light truck
    ORDER BY c.crash_id, u1.unit_nbr + u2.unit_nbr
)
SELECT m.veh_make_txt, m.veh_mod_txt, b.veh_body_styl_txt, q.crash_year, q.fatality, d.veh_damage_text, COUNT(1) quantity
    FROM q, lkp_make_mod m, lkp_bod_styl b, lkp_veh_dmag_area d
    WHERE q.veh_make_id = m.veh_make_id
      AND q.veh_mod_id = m.veh_mod_id
      AND COALESCE(q.veh_body_styl_id, 0) = b.veh_body_styl_id
      AND COALESCE(q.veh_dmag_area_1_id, 0) = d.veh_damage_id
    GROUP BY m.veh_make_txt, m.veh_mod_txt, b.veh_body_styl_txt, d.veh_damage_text, q.crash_year, q.fatality
    ORDER BY COUNT(1) DESC;
\copy t to '~/pedcrash/ped_inj_bodstyl.csv' delimiter ',' csv header;
drop table t;
```