# GitHub Preparations

This document describes all of the steps needed in order to prepare the supplemental material available at [https://github.com/ut-ctr-nmc/peds-midblocks-intersections](https://github.com/ut-ctr-nmc/peds-midblocks-intersections) that's in association with the paper:

> Zuniga-Garcia, Natalia, Kenneth A. Perrine, and Kara M. Kockelman. Analysis of Pedestrian Crashes at Intersection and Midblock Segment Levels in Texas, under review for Transportation Research Record, 2021.

This is supposed to have one-mile uniform segments and OSM-intersections with supporting material.

## Segments

Create this table and copy contents over.

```sql
CREATE TABLE segs_tx_1mi (
  road_gid integer NOT NULL,
  ref_begin real NOT NULL,
  ref_end real,
  seg_count integer,
  seg_total integer,
  seg_len real,
  frm_dfo numeric,
  overlap real,
  on_system boolean,
  center_lat real,
  center_lon real,
  ident varchar,
  geog geography,
  PRIMARY KEY (road_gid, ref_begin)
);

INSERT INTO segs_tx_1mi (road_gid, ref_begin, ref_end, seg_count,
    seg_total, seg_len, frm_dfo, overlap, on_system,
    center_lat, center_lon, geog)
  SELECT roadway_gid, ref_begin, ref_end, seg_count, seg_total,
      ref_end - ref_begin, closest_frm_dfo, overlap, on_system,
      center_lat, center_lon, geog
    FROM uniform_segs_1mi;
UPDATE segs_tx_1mi s SET ident = COALESCE(i.ste_nam, i.ria_rte_id)
  FROM roadway_inv i
  WHERE s.road_gid = i.gid AND s.frm_dfo = i.frm_dfo;

\copy (SELECT road_gid, ref_begin, ref_end, seg_count, seg_total, seg_len, frm_dfo, overlap, on_system, center_lat, center_lon, ident FROM segs_tx_1mi) TO '~/pedcrash/segs_tx_1mi.csv' DELIMITER ',' CSV HEADER;
```

To extract out the Shapefile, do:

```bash
mkdir -p ~/pedcrash/segs_tx_1mi
pgsql2shp -f ~/pedcrash/segs_tx_1mi/segs_tx_1mi.shp -h localhost -p 5432 -u **** -P ***** pedcrash segs_tx_1mi
zip -r -p segs_tx_1mi.zip segs_tx_1mi
```

## Intersections

This table can be created and saved out like this:

```sql
CREATE TABLE ints_tx (
  int_id integer PRIMARY KEY,
  signal boolean,
  junction boolean,
  signal_mid boolean,
  descr varchar,
  center geography(POINT)
);

INSERT INTO ints_tx (int_id, signal, junction, signal_mid, descr, center)
  SELECT int_id, signal, junction, midblock_sig, descr, center FROM ints_osm;
```

Then, deal with the next bit to be able to update the descriptions in `ints`.

### Intersection Approaches

Create and save out the table like this:

```sql
CREATE TABLE ints_tx_appch (
  int_id integer REFERENCES ints_tx (int_id),
  road_gid integer,
  frm_dfo numeric,
  lin_ref real,
  major boolean NOT NULL,
  PRIMARY KEY (int_id, major)
);

INSERT INTO ints_tx_appch (int_id, road_gid, major)
  SELECT int_id, roadway_gid, major FROM ints_osm_approaches;
UPDATE ints_tx_appch i SET frm_dfo = ioa.closest_dfo, lin_ref = ioa.lin_ref
  FROM ints_osm_members ioa
  WHERE i.int_id = ioa.int_id AND i.road_gid = ioa.roadway_gid;

\copy ints_tx_appch TO '~/pedcrash/ints_tx_appch.csv' DELIMITER ',' CSV HEADER;
```

### Back to Intersections:

```sql
UPDATE ints_tx i SET descr = COALESCE(r1.ste_nam, r1.ria_rte_id) || ' & ' || COALESCE(r2.ste_nam, r2.ria_rte_id)
  FROM roadway_inv r1, roadway_inv r2, ints_tx_appch ita1, ints_tx_appch ita2
  WHERE i.int_id = ita1.int_id
    AND i.int_id = ita2.int_id
    AND ita1.major
    AND NOT ita2.major
    AND ita1.road_gid = r1.gid
    AND ita2.road_gid = r2.gid
    AND ita1.frm_dfo = r1.frm_dfo
    AND ita2.frm_dfo = r2.frm_dfo;

\copy (SELECT int_id, signal, junction, signal_mid, descr, ROUND(ST_Y(center::geometry)::numeric, 4)::real lat, ROUND(ST_X(center::geometry)::numeric, 4)::real lon FROM ints_tx) TO '~/pedcrash/ints_tx.csv' DELIMITER ',' CSV HEADER;
```

And:

```bash
mkdir -p ~/pedcrash/ints_tx
pgsql2shp -f ~/pedcrash/ints_tx/ints_tx.shp -h localhost -p 5432 -u **** -P ***** pedcrash ints_tx
zip -r -p ints_tx.zip ints_tx
```

## Cleanup

```sql
DROP TABLE ints_tx_appch;
DROP TABLE ints_tx;
DROP TABLE segs_tx_1mi;
```
