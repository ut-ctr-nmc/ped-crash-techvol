"""
GreedyInts1.py: Experiment to produce clusters of intersections
"""

import psycopg2
import bisect
import csv

SCORE_CUTOFF = 5
MAX_MISSES = 4
TEST_FLAG = False

DB_CREDS = {"dbName": "pedcrash",
            "user": "****",
            "password": "****",
            "host": "HOST-MACHINE",
            "port": 5432}

conn = psycopg2.connect("dbname='%s' user='%s' host='%s' port=%d password='%s'" \
            % (DB_CREDS["dbName"], DB_CREDS["user"], DB_CREDS["host"], DB_CREDS["port"], DB_CREDS["password"]))

class Intersection:
    def __init__(self, intID, signal, midblockSig, count, ranking, kabcoPts, lat, lon):
        self.intID = intID
        self.signal = signal
        self.midblockSig = midblockSig
        self.count = count
        self.ranking = ranking
        self.kabcoPts = kabcoPts
        self.lat = lat
        self.lon = lon
        self.members = set()
        
class Member:
    def __init__(self, intID, streetName, roadway, refBegin):
        self.intID = intID
        self.streetName = streetName
        self.roadway = roadway
        self.refBegin = refBegin
        
class Segment:
    def __init__(self, gid, lrf, count, kabcoPts):
        self.gid = gid
        self.lrf = lrf
        self.count = count
        self.kabcoPts = kabcoPts
        self.ints = set()
        
class Roadway:
    def __init__(self, gid):
        self.gid = gid
        self.lrfs = []
        self.segs = []
        
    def addSeg(self, seg):
        self.segs.append(seg)
        
    def prepSegs(self):
        self.segs.sort(key=lambda x: x.lrf)
        self.lrfs = [x.lrf for x in self.segs]
        
    def getSeg(self, lrf):
        i = bisect.bisect_left(self.lrfs, lrf)
        if i != len(self.lrfs) and self.segs[i].lrf == lrf:
            return self.segs[i]
        return None
        
    def getNextSeg(self, lrf):
        i = bisect.bisect_right(self.lrfs, lrf)
        if i != len(self.lrfs):
            return self.segs[i]
        return None
        
    def getPrevSeg(self, lrf):
        i = bisect.bisect_left(self.lrfs, lrf)
        if i:
            return self.segs[i - 1]
        return None

class IntRecord:
    def __init__(self, intersection, streetName):
        self.intersection = intersection
        self.streetName = streetName
        self.memberInts = set()
        self.memberSegs = set()
        self.count = 0
        self.score = 0
        self.clusterNum = None

cur = conn.cursor()

# First, grab all of the uniform segments:
print("Retrieving segments...")
roadways = {}
testSQL = ""
if TEST_FLAG:
    testSQL = """, uniform_segs_01mi u WHERE css.roadway_gid = u.roadway_gid AND css.ref_begin = u.ref_begin
                 AND ST_DWithin(ST_SetSRID(ST_Point(-97.7404, 30.2747), 4326)::geography, u.geog, 1000)"""
sql = "SELECT css.roadway_gid, css.ref_begin, css.count_ped_nonint, css.pts_pedni_kabco FROM crash_stats_seg_01mi css%s;" % testSQL
cur.execute(sql);
cnt = 0
for row in cur:
    if row[1] is None:
        continue
    gid = row[0]
    if not gid in roadways:
        roadways[gid] = Roadway(gid)
    roadways[gid].addSeg(Segment(gid, row[1], row[2], row[3]))
    cnt += 1
print("  Roadways: %d; Segments: %d" % (len(roadways), cnt))
print("Preparing segments...")
for roadway in roadways.values():
    roadway.prepSegs()

print("Retrieving intersections...")
rankedInts = []
ints = {}
testSQL = ""
if TEST_FLAG:
    testSQL = " AND ST_DWithin(ST_SetSRID(ST_Point(-97.7404, 30.2747), 4326)::geography, i.center, 1000)"""
sql = """
    SELECT i.int_id, r.ranking_ped, r.count_ped, i.signal, i.midblock_sig, r.pts_ped_kabco, ST_Y(i.center::geometry) lat, ST_X(i.center::geometry) lon
    FROM ints_osm i, crash_int_osm_rankings r
    WHERE i.int_id = r.int_id
        AND NOT i.junction%s
    ORDER BY pts_ped_kabco DESC NULLS LAST, ranking_ped NULLS LAST;""" % testSQL
cur.execute(sql)
for row in cur:
    intersection = Intersection(row[0], row[3], row[4], row[2], row[1], row[5], row[6], row[7])
    if intersection.ranking:
        rankedInts.append(intersection)
    ints[intersection.intID] = intersection
print("  Intersections: %d; Ranked: %d" % (len(ints), len(rankedInts)))
    
print("Gathering intersection members...")
testSQL = ""
if TEST_FLAG:
    testSQL = """, ints_osm i WHERE iom.int_id = i.int_id
                 AND ST_DWithin(ST_SetSRID(ST_Point(-97.7404, 30.2747), 4326)::geography, i.center, 1000)"""
sql = "SELECT iom.int_id, iom.roadway_gid, iom.ref_begin_01, iom.lin_ref, iom.descr FROM ints_osm_members iom%s;" % testSQL
cur.execute(sql)
cnt = 0
for row in cur:
    if row[0] not in ints or row[2] is None or row[3] is None:
        continue
    intersection = ints[row[0]]
    roadway = roadways[row[1]]
    member = Member(intersection.intID, row[4], roadway, row[2])
    intersection.members.add(member)
    segment = roadway.getSeg(member.refBegin)
    segment.ints.add(intersection)
    cnt += 1
print("  Members: %d" % cnt)

def grow(current, roadway, segment, direction=0, missCount=0):
    global usedIntersections
    localScore = segment.count
    for intersection in segment.ints:
        key = (intersection.intID, current.streetName)
        if key in usedIntersections:
            return
        localScore += intersection.count
    if localScore < SCORE_CUTOFF:
        missCount += 1
        if missCount >= MAX_MISSES:
            return
    else:
        missCount = 0

    # Re-iterate and persist the score and member lists:
    for intersection in segment.ints:
        key = (intersection.intID, current.streetName)
        usedIntersections.add(key)
        current.memberInts.add(intersection)
        current.score += intersection.kabcoPts if intersection.kabcoPts is not None else 0
        current.count += intersection.count
    current.memberSegs.add(segment)
    current.score += segment.kabcoPts if segment.kabcoPts is not None else 0
    current.count += segment.count
    
    # Branch out:
    if direction >= 0:
        nextSeg = roadway.getNextSeg(segment.lrf)
        if nextSeg:
            grow(current, roadway, nextSeg, 1, missCount)
    if direction <= 0:
        prevSeg = roadway.getPrevSeg(segment.lrf)
        if prevSeg:
            grow(current, roadway, prevSeg, -1, missCount)

print("Greedy operation...")
results = []
usedIntersections = set()
for intersection in rankedInts:
    for member in intersection.members:
        key = (intersection.intID, member.streetName)
        if key in usedIntersections:
            continue
        current = IntRecord(intersection, member.streetName)
        segment = member.roadway.getSeg(member.refBegin)
        grow(current, member.roadway, segment)
        if current.score >= SCORE_CUTOFF:
            results.append(current)

print("Number of results: %d" % len(results))
results.sort(key=lambda x: x.score, reverse=True)

# Now get to reporting the results!
print("Writing clusterSeeds.csv...")
clusterNum = 1
with open("clusterSeeds.csv", "w", newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["corr_id", "int_id", "street_name", "kabco_pts", "num_segs", "num_ints", "count", "lat", "lon"])
    for result in results:
        result.clusterNum = clusterNum
        writer.writerow([result.clusterNum, result.intersection.intID, result.streetName, result.score, len(result.memberSegs), len(result.memberInts), result.count, \
                         result.intersection.lat, result.intersection.lon])
        clusterNum += 1

print("Writing clusterInts.csv...")
with open("clusterInts.csv", "w", newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["corr_id", "int_id", "signal", "midblock_sig", "count", "kabco_pts", "ranking", "lat", "lon"])
    for result in results:
        for memberInt in result.memberInts:
            writer.writerow([result.clusterNum, memberInt.intID, memberInt.signal, memberInt.midblockSig, memberInt.count, memberInt.kabcoPts, memberInt.ranking, memberInt.lat, memberInt.lon])

print("Writing clusterSegs.csv...")
with open("clusterSegs.csv", "w", newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["corr_id", "roadway_gid", "ref_begin", "non_int_count", "kabco_pts"])
    for result in results:
        for memberSeg in result.memberSegs:
            writer.writerow([result.clusterNum, memberSeg.gid, memberSeg.lrf, memberSeg.count, memberSeg.kabcoPts])

print("Done.")
