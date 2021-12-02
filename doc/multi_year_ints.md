# Multi-Year Intersections

There is a need to analyze VMT along segments and AADT within intersections over multiple years. This maps out how to manage multiple years' worth of TxDOT Roadway Inventory among a fixed set of intersections.

## ADT History

TxDOT Roadway Inventory has defined "HY_1", "HY_2", etc. which is a running history of ADT, back from "ADT_CUR". In many places, this goes back 10 years from the date of the TxDOT Roadway Inventory, but in some cases there are values of 0. These seem to indicate that data is not available.

### Preparation

Import the 2019 Roadway Inventory into the database:

```bash
shp2pgsql -D -I -G ~/pedcrash/2019/TxDOT_Roadway_Linework_wAssets.shp roadway_inv_2019 | psql -U **** -d pedcrash
```

During the import process, the `gid` column is rewritten with unique identifiers while the the old `gid` is renamed to `__gid`. For consistency and clarity with the TxDOT documentation, this is corrected:

```sql
ALTER TABLE roadway_inv_2019 DROP COLUMN gid;
ALTER TABLE roadway_inv_2019 RENAME COLUMN __gid TO gid;
ALTER TABLE roadway_inv_2019 ALTER COLUMN gid SET DATA TYPE integer;
ALTER TABLE roadway_inv_2019 ADD PRIMARY KEY (ria_rte_id, frm_dfo);
```

### Mapping from 2018 at Intersections to 2019

We want to create a mapping from all necessary 2018 LRFs to allow for possible shifts in LRFs between the 2018 and 2019 Roadway Inventories.

```sql
-- Temporary mapping table:
CREATE TEMP TABLE m (
  roadway_gid_2018 integer,
  ria_rte_id varchar,
  frm_dfo_2018 numeric,
  frm_dfo_2019 numeric,
  PRIMARY KEY (roadway_gid_2018, frm_dfo_2018)
);
CREATE INDEX idx_m_map2 ON m USING BTREE(ria_rte_id, frm_dfo_2019);

-- Gather the 2018 information we need:
INSERT INTO m (roadway_gid_2018, frm_dfo_2018)
  SELECT DISTINCT roadway_gid, closest_dfo
  FROM ints_osm_appch_ri;
UPDATE m
  SET ria_rte_id = r.ria_rte_id
  FROM roadway_inv r
  WHERE m.roadway_gid_2018 = r.gid
    AND m.frm_dfo_2018 = r.frm_dfo;

-- Map this to 2019:
-- (Good example of a subquery that somehow ends up not running too long)
UPDATE m
  SET frm_dfo_2019 = (
    SELECT r19.frm_dfo
      FROM roadway_inv_2019 r19
      WHERE m.ria_rte_id = r19.ria_rte_id
        AND m.frm_dfo_2018 >= r19.frm_dfo
      ORDER BY m.frm_dfo_2018 - r19.frm_dfo
      LIMIT 1
  );

-- There are 929 entries that are null, presumably from map changes.
-- Try again to populate, taking closest linear reference:
UPDATE m
  SET frm_dfo_2019 = (
    SELECT r19.frm_dfo
      FROM roadway_inv_2019 r19
      WHERE m.ria_rte_id = r19.ria_rte_id
      ORDER BY ABS(m.frm_dfo_2018 - r19.frm_dfo)
      LIMIT 1
  )
  WHERE m.frm_dfo_2019 IS NULL;

-- Now there's 878. Let's just delete these to clean up:
DELETE FROM m WHERE frm_dfo_2019 IS NULL;
```

### Useful Output: Intersection ADT History

The idea is to provide a running history of ADT for major and minor approaches at intersections, supplementing what's already represented in View "ints_osm_appch_ri".

Here's the table for it:

```sql
CREATE TABLE ints_osm_appch_adt_2019 (
    int_id integer REFERENCES ints_osm(int_id) ON DELETE CASCADE,
    major boolean,
    ria_rte_id varchar,
    closest_dfo numeric,
    adt_cur integer,
    adt_adj integer,
    adt_year integer,
    aadt_trucks integer,
    adt_hist_yr integer,
    hy_1 integer,
    hy_2 integer,
    hy_3 integer,
    hy_4 integer,
    hy_5 integer,
    hy_6 integer,
    hy_7 integer,
    hy_8 integer,
    hy_9 integer,
    PRIMARY KEY (int_id, major)
);
```

Then, to fill it out (using our 2018 to 2019 mapping):

```sql
INSERT INTO ints_osm_appch_adt_2019
  SELECT v.int_id, v.major, v.ria_rte_id, r.frm_dfo AS closest_dfo, r.adt_cur, r.adt_adj, r.adt_year,
    r.aadt_truck, r.adt_hist_y, r.hy_1, r.hy_2, r.hy_3, r.hy_4, r.hy_5,
    r.hy_6, r.hy_7, r.hy_8, r.hy_9
  FROM ints_osm_appch_ri v, roadway_inv_2019 r, m
  WHERE v.roadway_gid = m.roadway_gid_2018
    AND v.closest_dfo = m.frm_dfo_2018
    AND m.ria_rte_id = r.ria_rte_id
    AND m.frm_dfo_2019 = r.frm_dfo;
```

With that, export:

```sql
\copy ints_osm_appch_adt_2019 TO '~/pedcrash/ints_osm_appch_adt_2019.csv' DELIMITER ',' CSV HEADER;
```

This is what each column in there means:

* **int_id:** The identifier for the OSM-based intersection-- the same as used in other tables
* **major:** True if this corresponds with the major approach; otherwise False. More cross-streets than 2 are ignored here.
* **ria_rte_id:** Used to reference into the TxDOT Roadway Inventory 2019
* **closest_dfo:** Maps to the closest "frm_dfo" found in TxDOT Roadway Inventory 2019
* **adt_cur:** AADT-CURRENT as recorded in TxDOT Roadway Inventory 2019
* **adt_adj:** AADT-ADJUST-CURRENT as recorded in TxDOT Roadway Inventory 2019
* **adt_year:** ANNUAL-AVERAGE-DAILY-TRAFFIC-DT-CURRENT-YEAR
* **aadt_trucks:** Number of all trucks in AADT
* **adt_hist_yr:** The year that "hy_1" represents 
* **hy_1, hy_2, hy_3, hy_4, hy_5, hy_6, hy_7, hy_8, hy_9:** Historic ADT starting with "adt_hist_yr", going back year by year. I've seen suddenly low values such as "0" or "99", which probably means that history doesn't go back that far in these cases.