"""
GetOSMInts1.py: First attempt at getting OSM intersections that follows Attempt #3, Approach #1 in
the intersections.md document
"""

import requests, urllib
from collections import namedtuple
import csv, sys

OUTFILE = "osm_ints.csv"

PROGRAM_DESC = "Gets OSM intersections that follows Attempt #3, Approach #1"

# Points to Overpass API to get data from:
OVERPASS_URL = "http://HOST-MACHINE:8090/api/interpreter"

# CAVEAT: This only has the state of Texas map in it. If it had more, we'd need to filter on the State of Texas.

CORNER_LOW = (25.5136, -107.0439)
CORNER_HIGH = (36.6501, -93.3778)
STEPS_NS = 30
STEPS_EW = 30

OVERLAP = 0.05

# Determine roadway types we're interested in:
HIGHWAY_CLAUSE='["highway"~"^(motorway|trunk|primary|secondary|tertiary|motorway_link|trunk_link|primary_link|unclassified|residential|living_street)$"]'
#(Saved as "try1"):
#HIGHWAY_CLAUSE='["highway"~"^(motorway|trunk|primary|secondary|tertiary|motorway_link|trunk_link|primary_link|secondary_link)$"]'

Intersection = namedtuple("Intersection", "lat lon signal junction midblock_sig")
Way = namedtuple("Way", "type name")

def tf(inVal):
    return "TRUE" if inVal else "FALSE"

def getChunk(nodeCache, waySets, lowCoords, highCoords):
    queryStr = '[out:json];way(%g,%g,%g,%g)%s;(._;>;);out meta;' % (lowCoords[0], lowCoords[1], highCoords[0], highCoords[1], HIGHWAY_CLAUSE)
    print("  Fetching from Overpass API... ", end="", flush=True)
    queryStr = urllib.parse.quote(queryStr)
    response = requests.get(OVERPASS_URL + "?data=" + queryStr)
    response.raise_for_status()
    result = response.json()
    print("Done.")
    
    nodeCount = 0
    for element in result["elements"]:
        if "type" in element and element["type"] == "node" and element["id"] not in nodeCache:
            sigFlag = False
            junctFlag = False
            if "tags" in element and "highway" in element["tags"]:
                sigFlag = element["tags"]["highway"] == "traffic_signals"
                junctFlag = element["tags"]["highway"] == "motorway_junction"
            nodeCache[element["id"]] = Intersection(lat=element["lat"],
                                                        lon=element["lon"],
                                                        signal=sigFlag,
                                                        junction=junctFlag,
                                                        midblock_sig=None)
            waySets[element["id"]] = {} # That's way -> True if endpoint
            nodeCount += 1
    for element in result["elements"]:
        if "type" in element and element["type"] == "way":
            if "tags" in element and "highway" in element["tags"]:
                ourName = element["tags"]["name"].strip().upper() if "name" in element["tags"] else "none"
                way = Way(type=element["tags"]["highway"], name=ourName)
                index = 0
                numNodes = len(element["nodes"])
                for nodeID in element["nodes"]:
                    if nodeID in waySets:
                        waySets[nodeID][way] = nodeID == 0 or nodeID == numNodes - 1
                    index += 1
    print("New nodes: %d." % nodeCount)

def process():
    nodeCache = {}
    waySets = {}
    
    nodeCount = 0
    blockWidth = (CORNER_HIGH[1] - CORNER_LOW[1]) / STEPS_EW
    blockHeight = (CORNER_HIGH[0] - CORNER_LOW[0]) / STEPS_NS
    for vStep in range(STEPS_NS):
        for hStep in range(STEPS_EW):
            lowCoords = (CORNER_LOW[0] + blockHeight * vStep - blockHeight * OVERLAP, CORNER_LOW[1] + blockWidth * hStep - blockWidth * OVERLAP)
            highCoords = (CORNER_LOW[0] + blockHeight * (vStep + 1) + blockHeight * OVERLAP, CORNER_LOW[1] + blockWidth * (hStep + 1) + blockWidth * OVERLAP)
            print("Getting (%.4f,%.4f)-(%.4f,%.4f)..." % (lowCoords[0], lowCoords[1], highCoords[0], highCoords[1]))
            nodeCount = getChunk(nodeCache, waySets, lowCoords, highCoords)

    print("Sorting through final geometry...")
    intList = []
    for nodeID, node in nodeCache.items():
        nonMotorwayCnt = 0
        motorwayCnt = 0
        endCnt = 0
        for way, endFlag in waySets[nodeID].items():
            if way.type.startswith("motorway"):
                motorwayCnt += 1
            else:
                nonMotorwayCnt += 1
            if endFlag:
                endCnt += 1
        if node.signal or (motorwayCnt + nonMotorwayCnt > 1 and not (endCnt == 2 and motorwayCnt + nonMotorwayCnt == 2)):
            motorwayFlag = node.junction or nonMotorwayCnt == 0
            intList.append(Intersection(lat=node.lat, lon=node.lon, signal=node.signal, junction=motorwayFlag,
                                        midblock_sig=node.signal and motorwayCnt + nonMotorwayCnt < 2)) 
    print("Number of intersections: %d" % len(intList))
    
    print("Outputting CSV '%s'..." % OUTFILE)
    outHandle = open(OUTFILE, "w")
    csvWriter = csv.writer(outHandle)
    csvWriter.writerow(['lat', 'lon', 'signal', 'junction', 'midblock_sig'])
    for node in intList:
        csvWriter.writerow([node.lat, node.lon, tf(node.signal), tf(node.junction), tf(node.midblock_sig)])
    outHandle.close()
    print("Done.")

    return 0

if __name__ == "__main__":
    sys.exit(process())
