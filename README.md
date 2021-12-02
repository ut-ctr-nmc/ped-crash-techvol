# ped-crash-techvol: Texas Ped Crash Tech Volume Pack

In conjunction with the Final Report "Identifying Risk Factors that Lead to Increase in Fatal Pedestrian Crashes and Developing Countermeasures to Reverse the Trend" for the TxDOT Research and Technology Implementation 0-7048 project conducted Jan. 2020-Dec. 2021.

## Introduction

This repository contains technical documentation and source code that were used to analyze data from TxDOT's Crash Records Information System (CRIS) and other sources to determine causes of pedestrian-related crashes, and to assist in determining the best roadway treatments for mitigating the most severe pedestrian injuries and fatalities. While this was a project using Texas data, the processes and results may be applicable to other locations.

Another repository [peds-midblocks-intersections](https://github.com/ut-ctr-nmc/peds-midblocks-intersections) had been created that contains the results of the methods described for [finding intersections](doc/intersections.md) and [0.1-mile resampled roadway segments](doc/uniform_seg_10.md) from the [TxDOT Roadway Inventory](https://www.txdot.gov/inside-txdot/division/transportation-planning/roadway-inventory.html).

This documentation was written by [Kenneth Perrine](mailto:kperrine@utexas.edu), Research Associate at Center for Transportation Research at The University of Texas at Austin. Licensed under the [MIT License](LICENSE).

## Contents

### Database Preparation

* [Database Functions](doc/database.md): Outlines database tables, queries and access
* [Importing Major Data Files](doc/db_import.md): Importing CRIS Share and TxDOT Roadway Inventory into the database
* [Crash Statistics for 2010-2019](doc/crash_stats_2010-2019.md): Summary queries for crash data
* [Other Lookup Tables](doc/other_lookups.md): Preparing for queries around vehicle make/model

### Initial Crash Matching and Analysis

* [Crash Stats Segments Breakdown](doc/crash_stats_seg.md): Queries for summarizing crash-prone areas of [TxDOT Roadway Inventory](https://www.txdot.gov/inside-txdot/division/transportation-planning/roadway-inventory.html) data
* [Clustering](doc/clustering.md): A first attempt at grouping clusters of crashes around intersections for hotspot analysis

### Roadway Inventory

* [Uniform Segments](doc/uniform_seg.md): First round of resampling [TxDOT Roadway Inventory](https://www.txdot.gov/inside-txdot/division/transportation-planning/roadway-inventory.html) to 1-mile segments, plus crash-matching
* [0.1-mile Uniform Segments](doc/uniform_seg_10.md): Second round of resampling 0.1-mile segments plus crash-matching
* [Intersection](doc/intersections.md): Strategies for mapping intersections to TxDOT Roadway Inventory, including the use of OpenStretMap
* [Multi-Year Intersections](doc/multi_year_ints.md): Processing multi-year AADT estimates from TxDOT Roadway Inventory for intersections

### Subsequent Analysis

* [BCR Corridors](doc/bcr_corridors.md): Documents the final "Top 100 worst corridors" ranking strategy used in the project
* [Analysis that Includes Sidewalks](doc/sidewalks.md): Further statistics on Roadway Inventory plus use of sidewalk data

### Supporting Activities

* [GitHub Preparations](doc/prep_github.md): Instructions for preparing the [peds-midblocks-intersections](https://github.com/ut-ctr-nmc/peds-midblocks-intersections) dataset
* [VIN Testing](doc/vin_testing.md): Additional analysis that uses VIN numbers as recorded in CRIS
* [Crash Direction](doc/crash_direction.md): Documents future work that would be needed to more positively position crashes relative to roadway geometry
