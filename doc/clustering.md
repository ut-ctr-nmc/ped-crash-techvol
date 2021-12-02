# Clustering

This documents efforts to use clustering to find "hotspots" for pedestrian crashes across Texas.

## Preparation

Copy the "pedcrash" database to the PostgreSQL 10 server that has a version of PostGIS new enough to do clustering right in the database.

## Attempt #1: ST_ClusterDBSCAN()

We are going to try to use the ST_ClusterDBScan() PostGIS stored procedure to create clusters.

Create a destination location for cluster results and a means to visualize it:

```sql
CREATE TABLE cluster_test (
  crash_id integer PRIMARY KEY REFERENCES share_crash(crash_id),
  cluster_num integer,
  cluster_count integer,
  ranking integer
);

CREATE VIEW cluster_test_view AS
SELECT cr.crash_id, cl.cluster_num, cl.cluster_count, cl.ranking, cr.location
  FROM share_crash cr, cluster_test cl
    WHERE cr.crash_id = cl.crash_id;
```

Now, perform the clustering, using ~100-meter radii and core cluster count of 3.

```sql
-- Was SRID 2950
INSERT INTO cluster_test (crash_id, cluster_num)
SELECT cr.crash_id, ST_ClusterDBSCAN(ST_Transform(cr.location::geometry, 2278), eps := 100, minPoints := 3) OVER (ORDER BY cr.crash_id) AS cluster_num
  FROM share_crash cr, ped_activity p
  WHERE cr.crash_id = p.crash_id
    AND p.ped_crash
    AND cr.location IS NOT NULL
    AND ST_X(cr.location::geometry) < 0; -- TODO: There are problematic points
DELETE FROM cluster_test
  WHERE cluster_num IS NULL;

WITH q AS (
  SELECT cluster_num, COUNT(1) cluster_count
    FROM cluster_test
    GROUP BY cluster_num
), r AS (
    SELECT q.cluster_num, q.cluster_count,
      row_number() OVER (ORDER BY q.cluster_count DESC) AS ranking
    FROM q
)
UPDATE cluster_test AS cl
  SET cluster_count = r.cluster_count,
      ranking = r.ranking
  FROM r
  WHERE cl.cluster_num = r.cluster_num;
```

To get a shapefile, run on the host system (this example: NMC-Compute2):

```bash
pgsql2shp -f ./OUTFILE -h localhost -p 5434 -u nmc -P ***** pedcrash "SELECT * FROM cluster_test_view;"
```

## Attempt #2: Trying Various Options

We will again use the ST_ClusterDBScan() PostGIS stored procedure, but try it with various options.

Create a destination location for cluster results and a means to visualize it:

```sql
CREATE TABLE cluster_runs (
  cluster_run_id integer PRIMARY KEY,
  descr varchar
);
CREATE TABLE clusters (
  crash_id integer REFERENCES share_crash(crash_id),
  cluster_run_id integer REFERENCES cluster_runs(cluster_run_id) ON DELETE CASCADE,
  cluster_num integer,
  cluster_count integer,
  ranking integer,
  PRIMARY KEY (cluster_run_id, crash_id)
);
CREATE VIEW cluster_view AS
SELECT cr.crash_id, cl.cluster_run_id, cl.cluster_num, cl.cluster_count, cl.ranking, cruns.descr AS cl_run_descr, cr.location
  FROM share_crash cr, clusters cl, cluster_runs cruns
    WHERE cr.crash_id = cl.crash_id
      AND cl.cluster_run_id = cruns.cluster_run_id;
```

### Run #1: 50m, All Crashes

This is basically what was run with the "cluster_test" above, except that we're looking at all crashes, 100m radius, and with minimum points = 3. Keeping the top 300 clusters.

```sql
INSERT INTO cluster_runs (cluster_run_id, descr) VALUES (1, '50m, All Crashes');
INSERT INTO clusters (crash_id, cluster_num, cluster_run_id)
SELECT cr.crash_id, ST_ClusterDBSCAN(ST_Transform(cr.location::geometry, 2278), eps := 50, minPoints := 3) OVER (ORDER BY cr.crash_id) AS cluster_num, 1 AS cluster_run_id
  FROM share_crash cr
  WHERE cr.location IS NOT NULL
    AND ST_X(cr.location::geometry) < 0; -- Filter problematic points
DELETE FROM clusters
  WHERE cluster_num IS NULL AND cluster_run_id = 1;

WITH q AS (
  SELECT cluster_num, COUNT(1) cluster_count
    FROM clusters WHERE cluster_run_id = 1
    GROUP BY cluster_num
), r AS (
    SELECT q.cluster_num, q.cluster_count,
      row_number() OVER (ORDER BY q.cluster_count DESC) AS ranking
    FROM q
)
UPDATE clusters AS cl
  SET cluster_count = r.cluster_count,
      ranking = r.ranking
  FROM r
  WHERE cl.cluster_num = r.cluster_num AND cluster_run_id = 1;
DELETE FROM clusters WHERE cluster_run_id = 1 AND ranking > 300;
```

### Run #2: 50m, Ped Crashes

We reduce the radius to 50m and keep the minimum cluster count at 3.

```sql
INSERT INTO cluster_runs (cluster_run_id, descr) VALUES (2, '50m, Ped Crashes');
INSERT INTO clusters (crash_id, cluster_num, cluster_run_id)
SELECT cr.crash_id, ST_ClusterDBSCAN(ST_Transform(cr.location::geometry, 2278), eps := 50, minPoints := 3) OVER (ORDER BY cr.crash_id) AS cluster_num, 2 AS cluster_run_id
  FROM share_crash cr, ped_activity p
  WHERE cr.crash_id = p.crash_id
    AND p.ped_crash
    AND cr.location IS NOT NULL
    AND ST_X(cr.location::geometry) < 0; -- Filter problematic points
DELETE FROM clusters
  WHERE cluster_num IS NULL AND cluster_run_id = 2;

WITH q AS (
  SELECT cluster_num, COUNT(1) cluster_count
    FROM clusters WHERE cluster_run_id = 2
    GROUP BY cluster_num
), r AS (
    SELECT q.cluster_num, q.cluster_count,
      row_number() OVER (ORDER BY q.cluster_count DESC) AS ranking
    FROM q
)
UPDATE clusters AS cl
  SET cluster_count = r.cluster_count,
      ranking = r.ranking
  FROM r
  WHERE cl.cluster_num = r.cluster_num AND cluster_run_id = 2;
DELETE FROM clusters WHERE cluster_run_id = 2 AND ranking > 500;
```

### Run #3: 100m, Ped Crashes

This is ped crashes only, 100m radius, with minimum points = 2.

```sql
INSERT INTO cluster_runs (cluster_run_id, descr) VALUES (3, '100m, Ped Crashes');
INSERT INTO clusters (crash_id, cluster_num, cluster_run_id)
SELECT cr.crash_id, ST_ClusterDBSCAN(ST_Transform(cr.location::geometry, 2278), eps := 100, minPoints := 2) OVER (ORDER BY cr.crash_id) AS cluster_num, 3 AS cluster_run_id
  FROM share_crash cr, ped_activity p
  WHERE cr.crash_id = p.crash_id
    AND p.ped_crash
    AND cr.location IS NOT NULL
    AND ST_X(cr.location::geometry) < 0; -- Filter problematic points
DELETE FROM clusters
  WHERE cluster_num IS NULL AND cluster_run_id = 3;

WITH q AS (
  SELECT cluster_num, COUNT(1) cluster_count
    FROM clusters WHERE cluster_run_id = 3
    GROUP BY cluster_num
), r AS (
    SELECT q.cluster_num, q.cluster_count,
      row_number() OVER (ORDER BY q.cluster_count DESC) AS ranking
    FROM q
)
UPDATE clusters AS cl
  SET cluster_count = r.cluster_count,
      ranking = r.ranking
  FROM r
  WHERE cl.cluster_num = r.cluster_num AND cluster_run_id = 3;
DELETE FROM clusters WHERE cluster_run_id = 3 AND ranking > 500;
```

### Run #4: 100m, Ped Crashes at Intersections

This is ped crashes only at places where "at_intrsct_fl" is set, with 100m radius, and minimum points = 3.

```sql
INSERT INTO cluster_runs (cluster_run_id, descr) VALUES (4, '100m, Ped Crashes w/ at_intersct_fl');
INSERT INTO clusters (crash_id, cluster_num, cluster_run_id)
SELECT cr.crash_id, ST_ClusterDBSCAN(ST_Transform(cr.location::geometry, 2278), eps := 100, minPoints := 2) OVER (ORDER BY cr.crash_id) AS cluster_num, 4 AS cluster_run_id
  FROM share_crash cr, ped_activity p
  WHERE cr.crash_id = p.crash_id
    AND p.ped_crash
    AND cr.at_intrsct_fl = 'Y'
    AND cr.location IS NOT NULL
    AND ST_X(cr.location::geometry) < 0; -- Filter problematic points
DELETE FROM clusters
  WHERE cluster_num IS NULL AND cluster_run_id = 4;

WITH q AS (
  SELECT cluster_num, COUNT(1) cluster_count
    FROM clusters WHERE cluster_run_id = 4
    GROUP BY cluster_num
), r AS (
    SELECT q.cluster_num, q.cluster_count,
      row_number() OVER (ORDER BY q.cluster_count DESC) AS ranking
    FROM q
)
UPDATE clusters AS cl
  SET cluster_count = r.cluster_count,
      ranking = r.ranking
  FROM r
  WHERE cl.cluster_num = r.cluster_num AND cluster_run_id = 4;
DELETE FROM clusters WHERE cluster_run_id = 4 AND ranking > 500;
```

### Run #5: 100m, Fatal Ped Crashes

This is ped crashes only where fatalities are found. Here, radius is 100m and minimum cluster is 2 points.

```sql
INSERT INTO cluster_runs (cluster_run_id, descr) VALUES (5, '100m, Fatal Ped Crashes');
INSERT INTO clusters (crash_id, cluster_num, cluster_run_id)
SELECT cr.crash_id, ST_ClusterDBSCAN(ST_Transform(cr.location::geometry, 2278), eps := 100, minPoints := 2) OVER (ORDER BY cr.crash_id) AS cluster_num, 5 AS cluster_run_id
  FROM share_crash cr, ped_activity p
  WHERE cr.crash_id = p.crash_id
    AND p.ped_fatal > 0
    AND cr.location IS NOT NULL
    AND ST_X(cr.location::geometry) < 0; -- Filter problematic points
DELETE FROM clusters
  WHERE cluster_num IS NULL AND cluster_run_id = 5;

WITH q AS (
  SELECT cluster_num, COUNT(1) cluster_count
    FROM clusters WHERE cluster_run_id = 5
    GROUP BY cluster_num
), r AS (
    SELECT q.cluster_num, q.cluster_count,
      row_number() OVER (ORDER BY q.cluster_count DESC) AS ranking
    FROM q
)
UPDATE clusters AS cl
  SET cluster_count = r.cluster_count,
      ranking = r.ranking
  FROM r
  WHERE cl.cluster_num = r.cluster_num AND cluster_run_id = 5;
DELETE FROM clusters WHERE cluster_run_id = 5 AND ranking > 500;
```

### Run #6: 100m, Ped Crashes On-System

This is ped crashes only at places where "onsys_fl" is set, with 100m radius, and minimum points = 3.

```sql
INSERT INTO cluster_runs (cluster_run_id, descr) VALUES (6, '100m, Ped Crashes On-System');
INSERT INTO clusters (crash_id, cluster_num, cluster_run_id)
SELECT cr.crash_id, ST_ClusterDBSCAN(ST_Transform(cr.location::geometry, 2278), eps := 100, minPoints := 2) OVER (ORDER BY cr.crash_id) AS cluster_num, 6 AS cluster_run_id
  FROM share_crash cr, ped_activity p
  WHERE cr.crash_id = p.crash_id
    AND p.ped_crash
    AND cr.onsys_fl = 'Y'
    AND cr.location IS NOT NULL
    AND ST_X(cr.location::geometry) < 0; -- Filter problematic points
DELETE FROM clusters
  WHERE cluster_num IS NULL AND cluster_run_id = 6;

WITH q AS (
  SELECT cluster_num, COUNT(1) cluster_count
    FROM clusters WHERE cluster_run_id = 6
    GROUP BY cluster_num
), r AS (
    SELECT q.cluster_num, q.cluster_count,
      row_number() OVER (ORDER BY q.cluster_count DESC) AS ranking
    FROM q
)
UPDATE clusters AS cl
  SET cluster_count = r.cluster_count,
      ranking = r.ranking
  FROM r
  WHERE cl.cluster_num = r.cluster_num AND cluster_run_id = 6;
DELETE FROM clusters WHERE cluster_run_id = 6 AND ranking > 500;
```

### Outputting the Shapefile:

To get a shapefile, run on the host system (this example: NMC-Compute2):

```bash
pgsql2shp -f ./OUTFILE -h localhost -p 5434 -u nmc -P ***** pedcrash "SELECT * FROM cluster_view;"
```

## Tying Cluster Centers to Nearby Intersections

For purposes of analyzing against the TxDOT Roadway Inventory, it may be helpful to match clusters to nearby intersections. (Keep in mind that this is kind of another approach to doing the same thing as what's been documented in intersections.md. There, the quasi-clustering scheme is different than what had been done here.)

```sql
CREATE TABLE cluster_centers (
  cluster_run_id integer REFERENCES cluster_runs(cluster_run_id) ON DELETE CASCADE,
  cluster_num integer,
  center geography(point),
  int_id integer DEFAULT 0 REFERENCES intersections(int_id) ON DELETE CASCADE,
  PRIMARY KEY (cluster_run_id, cluster_num)
);
CREATE INDEX idx_cluster_centers_point ON cluster_centers USING GIST(center);

-- Get the cluster centers using an outlier-resilient method:
INSERT INTO cluster_centers (cluster_run_id, cluster_num, center)
  SELECT cluster_run_id, cluster_num, ST_GeometricMedian(ST_Collect(location::geometry))::geography
  FROM cluster_view
  GROUP BY cluster_run_id, cluster_num;

-- Find the TxDOT Roadway Inventory intersection that's closest to the center:
WITH q AS (
  SELECT DISTINCT ON (cc.cluster_run_id, cc.cluster_num)
    cc.cluster_run_id, cc.cluster_num, i.int_id
  FROM cluster_centers cc, intersections i
  WHERE ST_DWithin(cc.center, i.center, 200, FALSE)
  ORDER BY cc.cluster_run_id, cc.cluster_num, ST_Distance(cc.center, i.center, FALSE)
)
UPDATE cluster_centers AS cc
SET int_id = q.int_id
FROM q
WHERE q.cluster_run_id = cc.cluster_run_id
  AND q.cluster_num = cc.cluster_num;

-- Create a convenience view:
CREATE VIEW cluster_centers_intnames AS
  SELECT cc.*, i.descr
  FROM cluster_centers cc, intersections i
  WHERE cc.int_id = i.int_id;
```

These steps output shapefiles that can be used for visualization:

```bash
pgsql2shp -f ./OUTFILE -h localhost -p 5434 -u nmc -P ***** pedcrash "SELECT * FROM cluster_centers_intnames;"
```
