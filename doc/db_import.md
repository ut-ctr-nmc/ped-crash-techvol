# <!-- omit in toc -->Importing Major Data Files

This document identifies the importing of major data resources-- CRIS Share and TxDOT Roadway Inventory-- into the database.

- [Source File Locations](#source-file-locations)
- [CRIS Share Crash File](#cris-share-crash-file)
  - [Table Creation](#table-creation)
  - [Data Importing](#data-importing)
    - [Further Analyzing Lat/Lon Data](#further-analyzing-latlon-data)
- [CRIS Share Unit File](#cris-share-unit-file)
  - [Table Creation](#table-creation-1)
  - [Data Importing](#data-importing-1)
  - [Missing Data](#missing-data)
- [CRIS Share Person Files](#cris-share-person-files)
  - [Person File](#person-file)
    - [Table Creation](#table-creation-2)
    - [Data Importing](#data-importing-2)
  - [Primaryperson File](#primaryperson-file)
    - [Table Creation](#table-creation-3)
    - [Data Importing](#data-importing-3)
  - [Joining Person and Primaryperson Together](#joining-person-and-primaryperson-together)
- [TxDOT Roadway Inventory](#txdot-roadway-inventory)
  - [Importing into the Database](#importing-into-the-database)
  - [Lookups](#lookups)
    - [Table Creation and Importing](#table-creation-and-importing)
    - [Lookup Discrepancies](#lookup-discrepancies)
      - [Cities](#cities)
      - [Counties](#counties)

## Source File Locations
On the compute server:
- CRIS Share (for example, 2018): `~/pedcrash/CRIS_2018`
  - See John's document on creating and assembling CRIS Share data into CSV files.
- Roadway Inventory: `~/pedcrash/roadInv`
  - Downloaded from [TxDOT](https://www.txdot.gov/inside-txdot/division/transportation-planning/roadway-inventory.html)

## CRIS Share Crash File
In importing CRIS 2018 Share:
- Lookup tables are found in `publicextractfilespecification.xlsx`, but many can be left alone.

### Table Creation
This describes the creation of the CRIS Crash Share database table representation in PostgreSQL.

```sql
CREATE DATABASE pedcrash;
\c pedcrash
CREATE EXTENSION postgis;

CREATE TABLE share_crash (
    Crash_ID INTEGER PRIMARY KEY,
    Crash_Fatal_Fl CHAR(1),
    Cmv_Involv_Fl CHAR(1),
    Schl_Bus_Fl CHAR(1),
    Rr_Relat_Fl CHAR(1),
    Medical_Advisory_Fl CHAR(1),
    Amend_Supp_Fl CHAR(1),
    Active_School_Zone_Fl CHAR(1),
    Crash_Date DATE,
    Crash_Time TIME,
    Case_ID VARCHAR(20),
    Local_Use VARCHAR(20),
    Rpt_CRIS_Cnty_ID INTEGER,
    Rpt_City_iD INTEGER,
    Rpt_Outside_City_Limit_Fl CHAR(1),
    Thousand_Damage_Fl CHAR(1),
    Rpt_Latitude DECIMAL(11,8),
    Rpt_Longitude DECIMAL(11,8),
    Rpt_Rdwy_Sys_ID INTEGER,
    Rpt_Hwy_Num VARCHAR(4),
    Rpt_Hwy_Sfx CHAR(1),
    Rpt_Road_Part_ID INTEGER,
    Rpt_Block_Num VARCHAR(64),
    Rpt_Street_Pfx VARCHAR(64),
    Rpt_Street_Name VARCHAR(254),
    Rpt_Street_Sfx VARCHAR(64),
    Private_Dr_Fl CHAR(1),
    Toll_Road_Fl CHAR(1),
    Crash_Speed_Limit INTEGER,
    Road_Constr_Zone_Fl CHAR(1),
    Road_Constr_Zone_Wrkr_Fl CHAR(1),
    Rpt_Street_Desc VARCHAR(40),
    At_Intrsct_Fl CHAR(1),
    Rpt_Sec_Rdwy_Sys_ID INTEGER,
    Rpt_Sec_Hwy_Num VARCHAR(4),
    Rpt_Sec_Hwy_Sfx VARCHAR(1),
    Rpt_Sec_Road_Part_ID INTEGER,
    Rpt_Sec_Block_Num VARCHAR(64),
    Rpt_Sec_Street_Pfx VARCHAR(64),
    Rpt_Sec_Street_Name VARCHAR(254),
    Rpt_Sec_Street_Sfx VARCHAR(64),
    Rpt_Ref_Mark_Offset_Amt DECIMAL(7,3),
    Rpt_Ref_Mark_Dist_Uom VARCHAR(2),
    Rpt_Ref_Mark_Dir VARCHAR(64),
    Rpt_Ref_Mark_Nbr VARCHAR(64),
    Rpt_Sec_Street_Desc VARCHAR,
    Rpt_CrossingNumber VARCHAR(7),
    Wthr_Cond_ID INTEGER,
    Light_Cond_ID INTEGER,
    Entr_Road_ID INTEGER,
    Road_Type_ID INTEGER,
    Road_Algn_ID INTEGER,
    Surf_Cond_ID INTEGER,
    Traffic_Cntl_ID INTEGER,
    Investigat_Notify_Time TIME,
    Investigat_Notify_Meth VARCHAR(20),
    Investigat_Arrv_Time TIME,
    Report_Date DATE,
    Investigat_Comp_Fl CHAR(1),
    ORI_Number VARCHAR(9),
    Investigat_Agency_ID INTEGER,
    Investigat_Area_ID INTEGER,
    Investigat_District_ID INTEGER,
    Investigat_Region_ID INTEGER,
    Bridge_Detail_ID INTEGER,
    Harm_Evnt_Id INTEGER,
    Intrsct_Relat_ID INTEGER,
    FHE_Collsn_ID INTEGER,
    Obj_Struck_Id INTEGER,
    Othr_Factr_ID INTEGER,
    Road_Part_Adj_ID INTEGER,
    Road_Cls_ID INTEGER,
    Road_Relat_ID INTEGER,
    Phys_Featr_1_ID INTEGER,
    Phys_Featr_2_ID INTEGER,
    Cnty_ID INTEGER,
    City_ID INTEGER,
    Latitude DECIMAL(11,8),
    Longitude DECIMAL(11,8),
    Hwy_Sys CHAR(10),
    Hwy_Nbr CHAR(4),
    Hwy_Sfx CHAR(40),
    Dfo DECIMAL(7,3),
    Street_Name VARCHAR(254),
    Street_Nbr VARCHAR(64),
    Control INTEGER,
    Section INTEGER,
    Milepoint DECIMAL(7,3),
    Ref_Mark_Nbr VARCHAR(5),
    Ref_Mark_Displ DECIMAL(7,3),
    Hwy_Sys_2 CHAR(10),
    Hwy_Nbr_2 CHAR(4),
    Hwy_Sfx_2 CHAR(40),
    Street_Name_2 VARCHAR(254),
    Street_Nbr_2 VARCHAR(64),
    Control_2 INTEGER,
    Section_2 INTEGER,
    Milepoint_2 DECIMAL(7,3),
    Txdot_Rptable_Fl CHAR(1),
    Onsys_Fl CHAR(1),
    Rural_Fl CHAR(1),
    Crash_Sev_ID INTEGER,
    Pop_Group_ID INTEGER,
    Located_Fl CHAR(1),
    Day_of_Week CHAR(3),
    Hwy_Dsgn_Lane_ID INTEGER,
    Hwy_Dsgn_Hrt_ID INTEGER,
    Hp_Shldr_Left INTEGER,
    Hp_Shldr_Right INTEGER,
    Hp_Median_Width INTEGER,
    Base_Type_ID INTEGER,
    Nbr_Of_Lane INTEGER,
    Row_Width_Usual INTEGER,
    Roadbed_Width INTEGER,
    Surf_Width INTEGER,
    Surf_Type_ID INTEGER,
    Curb_Type_Left_ID INTEGER,
    Curb_Type_Right_ID INTEGER,
    Shldr_Type_Left_ID INTEGER,
    Shldr_Width_Left INTEGER,
    Shldr_Use_Left_ID INTEGER,
    Shldr_Type_Right_ID INTEGER,
    Shldr_Width_Right INTEGER,
    Shldr_Use_Right_ID INTEGER,
    Median_Type_ID INTEGER,
    Median_Width INTEGER,
    Rural_Urban_Type_ID INTEGER,
    Func_Sys_ID INTEGER,
    Adt_Curnt_Amt INTEGER,
    Adt_Curnt_Year INTEGER,
    Adt_Adj_Curnt_Amt INTEGER,
    Pct_Single_Trk_Adt DECIMAL(3,1),
    Pct_Combo_Trk_Adt DECIMAL(3,1),
    Trk_Aadt_Pct DECIMAL(3,1),
    Curve_Type_ID INTEGER,
    Curve_Lngth INTEGER,
    Cd_Degr INTEGER,
    Delta_Left_Right_ID INTEGER,
    Dd_Degr INTEGER,
    Feature_Crossed VARCHAR(24),
    Structure_Number INTEGER,
    I_R_Min_Vert_Clear DECIMAL(4,2),
    Approach_Width INTEGER,
    Bridge_Median_ID INTEGER,
    Bridge_Loading_Type_ID INTEGER,
    Bridge_Loading_In_1000_Lbs INTEGER,
    Bridge_Srvc_Type_On_ID INTEGER,
    Bridge_Srvc_Type_Under_ID INTEGER,
    Culvert_Type_ID INTEGER,
    Roadway_Width DECIMAL(5,1),
    Deck_Width DECIMAL(5,1),
    Bridge_Dir_Of_Traffic_ID INTEGER,
    Bridge_Rte_Struct_Func_ID INTEGER,
    Bridge_IR_Struct_Func_ID INTEGER,
    CrossingNumber CHAR(7),
    RRCo CHAR(4),
    Poscrossing_ID INTEGER,
    WDCode_ID INTEGER,
    Standstop SMALLINT,
    Yield SMALLINT,
    MPO_ID INTEGER,
    Investigat_Service_ID INTEGER,
    Investigat_Da_ID INTEGER,
    Sus_Serious_Injry_Cnt Integer,
    Nonincap_Injry_Cnt Integer,
    Poss_Injry_Cnt Integer,
    Non_Injry_Cnt Integer,
    Unkn_Injry_Cnt Integer,
    Tot_Injry_Cnt Integer,
    Death_Cnt Integer,
    Investigator_Narrative VARCHAR
);
CREATE INDEX idx_share_crash_date ON share_crash(Crash_Date);
```

### Data Importing
Then, to load the 2018 CSV contents into the `share_crash` table, do the following:

`\copy share_crash(Crash_ID,Crash_Fatal_Fl,Cmv_Involv_Fl,Schl_Bus_Fl,Rr_Relat_Fl,Medical_Advisory_Fl,Amend_Supp_Fl,Active_School_Zone_Fl,Crash_Date,Crash_Time,Case_ID,Local_Use,Rpt_CRIS_Cnty_ID,Rpt_City_ID,Rpt_Outside_City_Limit_Fl,Thousand_Damage_Fl,Rpt_Latitude,Rpt_Longitude,Rpt_Rdwy_Sys_ID,Rpt_Hwy_Num,Rpt_Hwy_Sfx,Rpt_Road_Part_ID,Rpt_Block_Num,Rpt_Street_Pfx,Rpt_Street_Name,Rpt_Street_Sfx,Private_Dr_Fl,Toll_Road_Fl,Crash_Speed_Limit,Road_Constr_Zone_Fl,Road_Constr_Zone_Wrkr_Fl,Rpt_Street_Desc,At_Intrsct_Fl,Rpt_Sec_Rdwy_Sys_ID,Rpt_Sec_Hwy_Num,Rpt_Sec_Hwy_Sfx,Rpt_Sec_Road_Part_ID,Rpt_Sec_Block_Num,Rpt_Sec_Street_Pfx,Rpt_Sec_Street_Name,Rpt_Sec_Street_Sfx,Rpt_Ref_Mark_Offset_Amt,Rpt_Ref_Mark_Dist_Uom,Rpt_Ref_Mark_Dir,Rpt_Ref_Mark_Nbr,Rpt_Sec_Street_Desc,Rpt_CrossingNumber,Wthr_Cond_ID,Light_Cond_ID,Entr_Road_ID,Road_Type_ID,Road_Algn_ID,Surf_Cond_ID,Traffic_Cntl_ID,Investigat_Notify_Time,Investigat_Notify_Meth,Investigat_Arrv_Time,Report_Date,Investigat_Comp_Fl,ORI_Number,Investigat_Agency_ID,Investigat_Area_ID,Investigat_District_ID,Investigat_Region_ID,Bridge_Detail_ID,Harm_Evnt_ID,Intrsct_Relat_ID,FHE_Collsn_ID,Obj_Struck_ID,Othr_Factr_ID,Road_Part_Adj_ID,Road_Cls_ID,Road_Relat_ID,Phys_Featr_1_ID,Phys_Featr_2_ID,Cnty_ID,City_ID,Latitude,Longitude,Hwy_Sys,Hwy_Nbr,Hwy_Sfx,Dfo,Street_Name,Street_Nbr,Control,Section,Milepoint,Ref_Mark_Nbr,Ref_Mark_Displ,Hwy_Sys_2,Hwy_Nbr_2,Hwy_Sfx_2,Street_Name_2,Street_Nbr_2,Control_2,Section_2,Milepoint_2,Txdot_Rptable_Fl,Onsys_Fl,Rural_Fl,Crash_Sev_ID,Pop_Group_ID,Located_Fl,Day_of_Week,Hwy_Dsgn_Lane_ID,Hwy_Dsgn_Hrt_ID,Hp_Shldr_Left,Hp_Shldr_Right,Hp_Median_Width,Base_Type_ID,Nbr_Of_Lane,Row_Width_Usual,Roadbed_Width,Surf_Width,Surf_Type_ID,Curb_Type_Left_ID,Curb_Type_Right_ID,Shldr_Type_Left_ID,Shldr_Width_Left,Shldr_Use_Left_ID,Shldr_Type_Right_ID,Shldr_Width_Right,Shldr_Use_Right_ID,Median_Type_ID,Median_Width,Rural_Urban_Type_ID,Func_Sys_ID,Adt_Curnt_Amt,Adt_Curnt_Year,Adt_Adj_Curnt_Amt,Pct_Single_Trk_Adt,Pct_Combo_Trk_Adt,Trk_Aadt_Pct,Curve_Type_ID,Curve_Lngth,Cd_Degr,Delta_Left_Right_ID,Dd_Degr,Feature_Crossed,Structure_Number,I_R_Min_Vert_Clear,Approach_Width,Bridge_Median_ID,Bridge_Loading_Type_ID,Bridge_Loading_In_1000_Lbs,Bridge_Srvc_Type_On_ID,Bridge_Srvc_Type_Under_ID,Culvert_Type_ID,Roadway_Width,Deck_Width,Bridge_Dir_Of_Traffic_ID,Bridge_Rte_Struct_Func_ID,Bridge_IR_Struct_Func_ID,CrossingNumber,RRCo,Poscrossing_ID,WDCode_ID,Standstop,Yield,Sus_Serious_Injry_Cnt,Nonincap_Injry_Cnt,Poss_Injry_Cnt,Non_Injry_Cnt,Unkn_Injry_Cnt,Tot_Injry_Cnt,Death_Cnt,MPO_ID,Investigat_Service_ID,Investigat_DA_ID,Investigator_Narrative) FROM '~/pedcrash/CRIS_2018/crash 2018.csv' DELIMITER ',' CSV HEADER;'

The following commands add geometry derived from latitude and longitude and allow for geographic querying:
```sql
ALTER TABLE share_crash ADD COLUMN location GEOGRAPHY(Point);
UPDATE share_crash SET location = ST_Point(Longitude, Latitude);
CREATE INDEX idx_share_crash_location ON share_crash USING GIST (location); 

-- There are the "rpt_" lat/lon fields for some of the entries that don't have "lat/lon":
-- TODO: Determine if we want to do this. 81,389 records (out of 94,813) are like this.
-- TODO: How many of these coordinates are wonky?
UPDATE share_crash
SET location = ST_Point(rpt_longitude, rpt_latitude)
WHERE location IS NULL;
```

The remainder offer opportunities for doing geocoding with the other pieces of information, although such a geocoding process has likely already been performed on CRIS Share data, populating the `latitude` and `longitude` fields:
- For a street: rpt_block_num, rpt_street_pfx, rpt_street_name, rpt_street_sfx rpt_sec_block_num, rpt_sec_street_name, rpt_sec_street_sfx
- Example: Record 16215852 street blocks don't line up, but primary and secondary streets do cross in Houston.
- Example: Record 16429136 cross streets can't really be found in Laredo, TX
- For a highway:
rpt_street_name (or, highway_sys, hwy_nbr, hwy_sfx)
rpt_block_num
- Others?

#### Further Analyzing Lat/Lon Data
In studying lat/lon geometry in the CRIS Share crash data, it is helpful to find how much is missing:

```sql
-- Total number of crash records for 2010-2019:
SELECT COUNT(1) FROM share_crash;
-- That's 5,631,223

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

-- Total number of ped crashes for 2010-2019:
SELECT COUNT(1) FROM ped_activity WHERE ped_crash;
-- That's 78,497

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

## CRIS Share Unit File
The following pertains to the creation of CRIS Share Unit data:

### Table Creation
```sql
CREATE TABLE share_unit (
    Crash_ID INTEGER,
    Unit_Nbr INTEGER,
    Unit_Desc_ID INTEGER,
    Veh_Parked_Fl VARCHAR(64),
    Veh_HNR_Fl CHAR(1),
    Veh_Lic_State_ID INTEGER,
    VIN VARCHAR(19),
    Veh_Mod_Year INTEGER,
    Veh_Color_ID INTEGER,
    Veh_Make_ID INTEGER,
    Veh_Mod_ID INTEGER,
    Veh_Body_Styl_ID INTEGER,
    Emer_Respndr_Fl CHAR(1),
    Ownr_Zip VARCHAR(15),
    Fin_Resp_Proof_ID INTEGER,
    Fin_Resp_Type_ID INTEGER,
    Veh_Dmag_Area_1_ID INTEGER,
    Veh_Dmag_Scl_1_ID INTEGER,
    Force_Dir_1_ID INTEGER,
    Veh_Dmag_Area_2_ID INTEGER,
    Veh_Dmag_Scl_2_ID INTEGER,
    Force_Dir_2_ID INTEGER,
    Veh_Inventoried_Fl VARCHAR(64),
    Veh_Transp_Name VARCHAR(64),
    Veh_Transp_Dest VARCHAR(64),
    Veh_CMV_Fl CHAR(1),
    Cmv_Fiveton_Fl CHAR(1),
    Cmv_Hazmat_Fl CHAR(1),
    Cmv_Nine_Plus_Pass_Fl CHAR(1),
    Cmv_Veh_Oper_ID INTEGER,
    Cmv_Carrier_ID_Type_ID INTEGER,
    Cmv_Carrier_Zip VARCHAR(15),
    Cmv_Veh_Type_ID INTEGER,
    Cmv_GVWR INTEGER,
    Cmv_RGVW INTEGER,
    Cmv_Hazmat_Rel_Fl CHAR(1),
    Hazmat_Cls_1_ID INTEGER,
    Hazmat_IDNbr_1_ID INTEGER,
    Hazmat_Cls_2_ID INTEGER,
    Hazmat_IDNbr_2_ID INTEGER,
    Cmv_Cargo_Body_ID INTEGER,
    Cmv_Evnt1_ID INTEGER,
    Cmv_Evnt2_ID INTEGER,
    Cmv_Evnt3_ID INTEGER,
    Cmv_Evnt4_ID INTEGER,
    Cmv_Tot_Axle INTEGER,
    Cmv_Tot_Tire INTEGER,
    Contrib_Factr_1_ID INTEGER,
    Contrib_Factr_2_ID INTEGER,
    Contrib_Factr_3_ID INTEGER,
    Contrib_Factr_P1_ID INTEGER,
    Contrib_Factr_P2_ID INTEGER,
    Veh_Dfct_1_ID INTEGER,
    Veh_Dfct_2_ID INTEGER,
    Veh_Dfct_3_ID INTEGER,
    Veh_Dfct_P1_ID INTEGER,
    Veh_Dfct_P2_ID INTEGER,
    Veh_Trvl_Dir_ID INTEGER,
    First_Harm_Evt_Inv_ID INTEGER,
    Sus_Serious_Injry_Cnt INTEGER,
    Nonincap_Injry_Cnt INTEGER,
    Poss_Injry_Cnt INTEGER,
    Non_Injry_Cnt INTEGER,
    Unkn_Injry_Cnt INTEGER,
    Tot_Injry_Cnt INTEGER,
    Death_Cnt INTEGER,
    Cmv_Disabling_Damage_Fl CHAR(1),
    Cmv_Bus_Type_ID  INTEGER,
    Trlr_GVWR INTEGER,
    Trlr_RGVW INTEGER,
    Trlr_Type_ID INTEGER,
    Trlr_Disabling_Dmag_ID CHAR(1),
    CMV_Intermodal_Container_Permit_FL CHAR(1),
    CMV_Actual_Gross_Weight INTEGER,
    PRIMARY KEY (Crash_ID, Unit_Nbr)
);
```

### Data Importing

This is for the 2018 Share Unit file. **TODO:** For other years, there are some subtle variations that were not documented here because the efforts for importing were a one-time occurrence.
```sql
\copy share_unit(Crash_ID,Unit_Nbr,Unit_Desc_ID,Veh_Parked_Fl,Veh_HNR_Fl,
Veh_Lic_State_ID,VIN,Veh_Mod_Year,Veh_Color_ID,Veh_Make_ID,Veh_Mod_ID,
Veh_Body_Styl_ID,Emer_Respndr_Fl,Ownr_Zip,Fin_Resp_Proof_ID,
Fin_Resp_Type_ID,Veh_Dmag_Area_1_ID,Veh_Dmag_Scl_1_ID,Force_Dir_1_ID,
Veh_Dmag_Area_2_ID,Veh_Dmag_Scl_2_ID,Force_Dir_2_ID,Veh_Inventoried_Fl,
Veh_Transp_Name,Veh_Transp_Dest,Veh_Cmv_Fl,Cmv_Fiveton_Fl,Cmv_Hazmat_Fl,
Cmv_Nine_Plus_Pass_Fl,Cmv_Veh_Oper_ID,Cmv_Carrier_ID_Type_ID,
Cmv_Carrier_Zip,Cmv_Veh_Type_ID,Cmv_GVWR,Cmv_RGVW,Cmv_Hazmat_Rel_Fl,
Hazmat_Cls_1_ID,Hazmat_IDNbr_1_ID,Hazmat_Cls_2_ID,Hazmat_IDNbr_2_ID,
Cmv_Cargo_Body_ID,Cmv_Evnt1_ID,Cmv_Evnt2_ID,Cmv_Evnt3_ID,Cmv_Evnt4_ID,
Cmv_Tot_Axle,Cmv_Tot_Tire,Contrib_Factr_1_ID,Contrib_Factr_2_ID,
Contrib_Factr_3_ID,Contrib_Factr_P1_ID,Contrib_Factr_P2_ID,Veh_Dfct_1_ID,
Veh_Dfct_2_ID,Veh_Dfct_3_ID,Veh_Dfct_P1_ID,Veh_Dfct_P2_ID,Veh_Trvl_Dir_ID,
First_Harm_Evt_Inv_ID,Sus_Serious_Injry_Cnt,Nonincap_Injry_Cnt,
Poss_Injry_Cnt,Non_Injry_Cnt,Unkn_Injry_Cnt,Tot_Injry_Cnt,Death_Cnt,
Cmv_Disabling_Damage_Fl,Cmv_Bus_Type_ID,Trlr_GVWR,Trlr_RGVW,Trlr_Type_ID,
Trlr_Disabling_Dmag_ID,Cmv_Intermodal_Container_Permit_Fl,
CMV_Actual_Gross_Weight) FROM '~/pedcrash/CRIS_2018/unit 2018.csv'
DELIMITER ',' NULL 'NA' CSV HEADER;
```

### Missing Data

As of Jan. 2021, it was discovered for several years' worth of data that Unit data was underrepresented (e.g. missing) from the last month or two. An effort was conducted to re-query for the public share Unit data, and this process is used to add in the missing records.

1. Create a temporary table: `CREATE TEMP TABLE su (LIKE share_unit INCLUDING ALL);`.
2. Make modifications to the new table to make it consistent with the newer CSV file format:
    ```sql
    ALTER TABLE su RENAME COLUMN Veh_Dmag_Area_1_ID TO Veh_Damage_Description1_Id;
    ALTER TABLE su RENAME COLUMN Veh_Dmag_Scl_1_ID TO Veh_Damage_Severity1_Id;
    ALTER TABLE su RENAME COLUMN Force_Dir_1_ID TO Veh_Damage_Direction_Of_Force1_Id;
    ALTER TABLE su RENAME COLUMN Veh_Dmag_Area_2_ID TO Veh_Damage_Description2_Id;
    ALTER TABLE su RENAME COLUMN Veh_Dmag_Scl_2_ID TO Veh_Damage_Severity2_Id;
    ALTER TABLE su RENAME COLUMN Force_Dir_2_ID TO Veh_Damage_Direction_Of_Force2_Id;
    --ALTER TABLE su RENAME COLUMN Trlr_GVWR TO Trlr1_GVWR;
    --ALTER TABLE su RENAME COLUMN Trlr_RGVW TO Trlr1_RGVW;
    --ALTER TABLE su RENAME COLUMN Trlr_Type_ID TO Trlr1_Type_ID;
    ALTER TABLE su RENAME COLUMN Trlr_Disabling_Dmag_ID TO Trlr1_Disabling_Dmag_ID;
    ALTER TABLE su ADD COLUMN Cmv_Road_Acc_ID varchar;
    ALTER TABLE su ADD COLUMN Trlr2_GVWR varchar;
    ALTER TABLE su ADD COLUMN Trlr2_RGVW varchar;
    ALTER TABLE su ADD COLUMN Trlr2_Type_ID varchar;
    ALTER TABLE su ADD COLUMN Trlr2_Disabling_Dmag_ID varchar;
    ALTER TABLE su ADD COLUMN Pedestrian_Action_ID varchar;
    ALTER TABLE su ADD COLUMN Pedalcyclist_Action_ID varchar;
    ALTER TABLE su ADD COLUMN PBCAT_Pedestrian_ID varchar;
    ALTER TABLE su ADD COLUMN PBCAT_Pedalcyclist_ID varchar;
    ALTER TABLE su ADD COLUMN E_Scooter_ID varchar;
    ALTER TABLE su ADD COLUMN Autonomous_Unit_ID varchar;
    ```

3. Use the `\copy` statement similar to above to copy in the CSV files, making adjustments for the inconsistencies that were found from year to year. The format changed, so the statement needs to look like: `\copy su(Crash_ID,Unit_Nbr,Unit_Desc_ID,Veh_Parked_Fl,Veh_HNR_Fl,Veh_Lic_State_ID,VIN,Veh_Mod_Year,Veh_Color_ID,Veh_Make_ID,Veh_Mod_ID,Veh_Body_Styl_ID,Emer_Respndr_Fl,Ownr_Zip,Fin_Resp_Proof_ID,Fin_Resp_Type_ID,Veh_Damage_Description1_Id,Veh_Damage_Severity1_Id,Veh_Damage_Direction_Of_Force1_Id,Veh_Damage_Description2_Id,Veh_Damage_Severity2_Id,Veh_Damage_Direction_Of_Force2_Id,Veh_Inventoried_Fl,Veh_Transp_Name,Veh_Transp_Dest,Veh_Cmv_Fl,Cmv_Fiveton_Fl,Cmv_Hazmat_Fl,Cmv_Nine_Plus_Pass_Fl,Cmv_Veh_Oper_ID,Cmv_Carrier_ID_Type_ID,Cmv_Carrier_Zip,Cmv_Road_Acc_ID,Cmv_Veh_Type_ID,Cmv_GVWR,Cmv_RGVW,Cmv_Hazmat_Rel_Fl,Hazmat_Cls_1_ID,Hazmat_IDNbr_1_ID,Hazmat_Cls_2_ID,Hazmat_IDNbr_2_ID,Cmv_Cargo_Body_ID,Trlr1_GVWR,Trlr1_RGVW,Trlr1_Type_ID,Trlr2_GVWR,Trlr2_RGVW,Trlr2_Type_ID,Cmv_Evnt1_ID,Cmv_Evnt2_ID,Cmv_Evnt3_ID,Cmv_Evnt4_ID,Cmv_Tot_Axle,Cmv_Tot_Tire,Contrib_Factr_1_ID,Contrib_Factr_2_ID,Contrib_Factr_3_ID,Contrib_Factr_P1_ID,Contrib_Factr_P2_ID,Veh_Dfct_1_ID,Veh_Dfct_2_ID,Veh_Dfct_3_ID,Veh_Dfct_P1_ID,Veh_Dfct_P2_ID,Veh_Trvl_Dir_ID,First_Harm_Evt_Inv_ID,Sus_Serious_Injry_Cnt,Nonincap_Injry_Cnt,Poss_Injry_Cnt,Non_Injry_Cnt,Unkn_Injry_Cnt,Tot_Injry_Cnt,Death_Cnt,Cmv_Disabling_Damage_Fl,Cmv_Trlr1_Disabling_Dmag_ID,Cmv_Trlr2_Disabling_Dmag_ID,Cmv_Bus_Type_ID,Pedestrian_Action_ID,Pedalcyclist_Action_ID,PBCAT_Pedestrian_ID,PBCAT_Pedalcyclist_ID,E_Scooter_ID,Autonomous_Unit_ID) FROM 'my_csv_file' DELIMITER ',' NULL '' CSV HEADER;`

4. Make adjustments to revert table structure back to what's in the DB currently:
    ```sql
    ALTER TABLE su RENAME COLUMN Veh_Damage_Description1_Id TO Veh_Dmag_Area_1_ID;
    ALTER TABLE su RENAME COLUMN Veh_Damage_Severity1_Id TO Veh_Dmag_Scl_1_ID;
    ALTER TABLE su RENAME COLUMN Veh_Damage_Direction_Of_Force1_Id TO Force_Dir_1_ID;
    ALTER TABLE su RENAME COLUMN Veh_Damage_Description2_Id TO Veh_Dmag_Area_2_ID;
    ALTER TABLE su RENAME COLUMN Veh_Damage_Severity2_Id TO Veh_Dmag_Scl_2_ID;
    ALTER TABLE su RENAME COLUMN Veh_Damage_Direction_Of_Force2_Id TO Force_Dir_2_ID;
    --ALTER TABLE su RENAME COLUMN Trlr1_GVWR TO Trlr_GVWR;
    --ALTER TABLE su RENAME COLUMN Trlr1_RGVW TO Trlr_RGVW;
    --ALTER TABLE su RENAME COLUMN Trlr1_Type_ID TO Trlr_Type_ID;
    ALTER TABLE su RENAME COLUMN Trlr1_Disabling_Dmag_ID TO Trlr_Disabling_Dmag_ID;
    ALTER TABLE su DROP COLUMN Cmv_Road_Acc_ID;
    ALTER TABLE su DROP COLUMN Trlr2_GVWR;
    ALTER TABLE su DROP COLUMN Trlr2_RGVW;
    ALTER TABLE su DROP COLUMN Trlr2_Type_ID;
    ALTER TABLE su DROP COLUMN Trlr2_Disabling_Dmag_ID;
    ALTER TABLE su DROP COLUMN Pedestrian_Action_ID;
    ALTER TABLE su DROP COLUMN Pedalcyclist_Action_ID;
    ALTER TABLE su DROP COLUMN PBCAT_Pedestrian_ID;
    ALTER TABLE su DROP COLUMN PBCAT_Pedalcyclist_ID;
    ALTER TABLE su DROP COLUMN E_Scooter_ID;
    ALTER TABLE su DROP COLUMN Autonomous_Unit_ID;
    ```

5. Prevent duplicates and copy over the data:
    ```sql
    DELETE FROM su
      USING share_unit s
      WHERE s.crash_id = su.crash_id
        AND s.unit_nbr = su.unit_nbr;
    INSERT INTO share_unit SELECT * FROM su;
    -- As of Feb. 3, 2021, there were 824090 records added.
    ```

## CRIS Share Person Files
The CRIS Share Person and Primaryperson files are very similar; Person is a subset of Primaryperson. The contents are unioned into an individual table at the end of table creation and importing.

### Person File
#### Table Creation
```sql
CREATE TABLE share_person (
    Crash_ID INTEGER,
    Unit_Nbr INTEGER,
    Prsn_Nbr INTEGER,
    Prsn_Type_ID INTEGER,
    Prsn_Occpnt_Pos_ID INTEGER,
    Prsn_Injry_Sev_ID INTEGER,
    Prsn_Age INTEGER,
    Prsn_Ethnicity_ID INTEGER,
    Prsn_Gndr_ID INTEGER,
    Prsn_Ejct_ID INTEGER,
    Prsn_Rest_ID INTEGER,
    Prsn_Airbag_ID INTEGER,
    Prsn_Helmet_ID INTEGER,
    Prsn_Sol_Fl CHAR(1),
    Prsn_Alc_Spec_Type_ID INTEGER,
    Prsn_Alc_Rslt_ID INTEGER,
    Prsn_Bac_Test_Rslt DECIMAL(4,3),
    Prsn_Drg_Spec_Type_ID INTEGER,
    Prsn_Drg_Rslt_ID INTEGER,
    Prsn_Death_Time TIME,
    Sus_Serious_Injry_Cnt INTEGER,
    Nonincap_Injry_Cnt INTEGER,
    Poss_Injry_Cnt INTEGER,
    Non_Injry_Cnt INTEGER,
    Unkn_Injry_Cnt INTEGER,
    Tot_Injry_Cnt INTEGER,
    Death_Cnt INTEGER,
    PRIMARY KEY (Crash_ID, Unit_Nbr, Prsn_Nbr)
);
```

#### Data Importing
```sql
\copy share_person(Crash_ID,Unit_Nbr,Prsn_Nbr,Prsn_Type_ID,
Prsn_Occpnt_Pos_ID,Prsn_Injry_Sev_ID,Prsn_Age,Prsn_Ethnicity_ID,
Prsn_Gndr_ID,Prsn_Ejct_ID,Prsn_Rest_ID,Prsn_Airbag_ID,Prsn_Helmet_ID,
Prsn_Sol_Fl,Prsn_Alc_Spec_Type_ID,Prsn_Alc_Rslt_ID,Prsn_Bac_Test_Rslt,
Prsn_Drg_Spec_Type_ID,Prsn_Drg_Rslt_ID,Prsn_Death_Time,
Sus_Serious_Injry_Cnt,Nonincap_Injry_Cnt,Poss_Injry_Cnt,Non_Injry_Cnt,
Unkn_Injry_Cnt,Tot_Injry_Cnt,Death_Cnt)
FROM '~/pedcrash/CRIS_2018/person 2018.csv' DELIMITER ',' CSV HEADER;
```

### Primaryperson File

#### Table Creation
```sql
CREATE TABLE share_primaryperson (
    Crash_ID INTEGER,
    Unit_Nbr INTEGER,
    Prsn_Nbr INTEGER,
    Prsn_Type_ID INTEGER,
    Prsn_Occpnt_Pos_ID INTEGER,
    Prsn_Injry_Sev_ID INTEGER,
    Prsn_Age INTEGER,
    Prsn_Ethnicity_ID INTEGER,
    Prsn_Gndr_ID INTEGER,
    Prsn_Ejct_ID INTEGER,
    Prsn_Rest_ID INTEGER,
    Prsn_Airbag_ID INTEGER,
    Prsn_Helmet_ID INTEGER,
    Prsn_Sol_Fl CHAR(1),
    Prsn_Alc_Spec_Type_ID INTEGER,
    Prsn_Alc_Rslt_ID INTEGER,
    Prsn_Bac_Test_Rslt DECIMAL(4,3),
    Prsn_Drg_Spec_Type_ID INTEGER,
    Prsn_Drg_Rslt_ID INTEGER,
    Drvr_Drg_Cat_1_ID INTEGER,
    Prsn_Death_Time TIME,
    Sus_Serious_Injry_Cnt INTEGER,
    Nonincap_Injry_Cnt INTEGER,
    Poss_Injry_Cnt INTEGER,
    Non_Injry_Cnt INTEGER,
    Unkn_Injry_Cnt INTEGER,
    Tot_Injry_Cnt INTEGER,
    Death_Cnt INTEGER,
    Drvr_Lic_Type_ID INTEGER,
    Drvr_Lic_State_ID INTEGER,
    Drvr_Lic_Cls_ID INTEGER,
    Drvr_Zip VARCHAR(40),
    PRIMARY KEY (Crash_ID, Unit_Nbr)
);
```

#### Data Importing
```sql
\copy share_primaryperson(Crash_ID,Unit_Nbr,Prsn_Nbr,Prsn_Type_ID,
Prsn_Occpnt_Pos_ID,Prsn_Injry_Sev_ID,Prsn_Age,Prsn_Ethnicity_ID,
Prsn_Gndr_ID,Prsn_Ejct_ID,Prsn_Rest_ID,Prsn_Airbag_ID,Prsn_Helmet_ID,
Prsn_Sol_Fl,Prsn_Alc_Spec_Type_ID,Prsn_Alc_Rslt_ID,Prsn_Bac_Test_Rslt,
Prsn_Drg_Spec_Type_ID,Prsn_Drg_Rslt_ID,Drvr_Drg_Cat_1_ID,Prsn_Death_Time,
Sus_Serious_Injry_Cnt,Nonincap_Injry_Cnt,Poss_Injry_Cnt,Non_Injry_Cnt,
Unkn_Injry_Cnt,Tot_Injry_Cnt,Death_Cnt,Drvr_Lic_Type_ID,Drvr_Lic_State_ID,
Drvr_Lic_Cls_ID,Drvr_Zip)
FROM '~/pedcrash/CRIS_2018/primaryperson 2018.csv' DELIMITER ',' NULL 'NA' CSV HEADER;
```

### Joining Person and Primaryperson Together
To join the Person and Primaryperson records together into one table, a view is created that "unions" the two tables `share_person` and `share_primaryperson` together into a `share_allperson` resource.

```sql
CREATE VIEW share_allperson AS
SELECT *
FROM share_primaryperson
UNION SELECT crash_id, unit_nbr, prsn_nbr, prsn_type_id, 
    prsn_occpnt_pos_id, prsn_injry_sev_id, prsn_age, prsn_ethnicity_id, 
    prsn_gndr_id, prsn_ejct_id, prsn_rest_id, prsn_airbag_id, prsn_helmet_id, 
    prsn_sol_fl, prsn_alc_spec_type_id, prsn_alc_rslt_id, prsn_bac_test_rslt, 
    prsn_drg_spec_type_id, prsn_drg_rslt_id, NULL drvr_drg_cat_1_id, 
    prsn_death_time, sus_serious_injry_cnt, nonincap_injry_cnt, poss_injry_cnt, 
    non_injry_cnt, unkn_injry_cnt, tot_injry_cnt, death_cnt, NULL 
    Drvr_Lic_Type_ID, NULL Drvr_Lic_State_ID, NULL Drvr_Lic_Cls_ID, NULL Drvr_Zip
FROM share_person;
```

## TxDOT Roadway Inventory
Column specifications are in file `TxDOT_Roadway_Inventory_Specifications.pdf` that come with the TxDOT Roadway Inventory download from the TxDOT website.

### Importing into the Database
To do the import from the Shapefile located within the downloadable package:
```bash
shp2pgsql -D -I -G ~/pedcrash/roadInv/TxDOT_Roadway_Inventory_Linework_wAssets.shp roadway_inv | psql -U **** -d pedcrash
```

During the import process, the `gid` column is rewritten with unique identifiers while the the old `gid` is renamed to `__gid`. For consistency and clarity with the TxDOT documentation, this is corrected:
```sql
ALTER TABLE roadway_inv DROP COLUMN gid;
ALTER TABLE roadway_inv RENAME COLUMN __gid TO gid;
ALTER TABLE roadway_inv ALTER COLUMN gid SET DATA TYPE integer;
ALTER TABLE roadway_inv ADD PRIMARY KEY (gid, frm_dfo);
```

### Lookups
In both the CRIS Share and TxDOT Roadway Inventory, cities and counties are coded as integers. For ease of use, lookup tables need to be created in order to assist with querying and displaying results with readable names of these places.

#### Table Creation and Importing
The lookups that are being imported into the respective tables had been extracted from the CRIS `standardextractfilespecification.xlsx` file.

```sql
CREATE TABLE lkp_mpo (
  mpo_id integer PRIMARY KEY,
  mpo_txt varchar);
-- mpo_lkp.csv comes from the "mpo_lkp" tab of standardextractfilespecification.xlsx
COPY lkp_mpo(mpo_id, mpo_txt) FROM '/tmp/mpo_lkp.csv' DELIMITER ',' CSV HEADER;
  
CREATE TABLE lkp_cnty (
  cnty_id integer PRIMARY KEY,
  txdot_inv_id integer,
  cnty_name varchar);
-- cnty_lkp.csv comes from the "cnty_lkp" tab of standardextractfilespecification.xlsx
COPY lkp_cnty(cnty_id, cnty_name) FROM '/tmp/cnty_lkp.csv' DELIMITER ',' CSV HEADER;
  
CREATE TABLE lkp_city (
  city_id integer PRIMARY KEY,
  txdot_inv_id integer,
  city_name varchar);
-- city_lkp.csv comes from the "city_lkp" tab of standardextractfilespecification.xlsx
COPY lkp_city(city_id, city_name) FROM '/tmp/city_lkp.csv' DELIMITER ',' CSV HEADER;
```

#### Lookup Discrepancies
It is assumed that MPO IDs are the same between the TxDOT Roadway Inventory and the CRIS Share data. Unfortunately, the city and county lookups are different! To resolve this, either we need to find the correct lookup, find geometry files for city limits and resolve the differences, or see where crash data points lie with respect to TxDOT Roadway Inventory segments and identify the most frequently matching pairs of ID values. For now, the last option is leveraged, but it will be more ideal to eventually import a definitive list.

##### Cities
This query creates a mapping between crash city IDs to Roadway Inventory city IDs, filling out the `txdot_inv_id` column in the `lkp_city` table. Note that where no crashes occur or crashes are few, the mapping may be nonexistent or incorrect.

> **TODO:** If a more definitive table is found to resolve the TxDOT Roadway Inventory city IDs, then use it, as it will be more accurate than this sampling method.
```sql
WITH q AS (
    WITH r AS (SELECT gid, MAX(city) AS city FROM roadway_inv GROUP BY gid)
    SELECT c.city_id city_crash, r.city city_inv, COUNT(1) score
      FROM share_crash c, r, crash_buf_100 b
    WHERE c.crash_id = b.crash_id
      AND b.nearest = TRUE
      AND b.roadway_gid = r.gid
    GROUP BY c.city_id, r.city
), s AS (
    SELECT q.city_crash, q.city_inv,
      RANK() OVER (PARTITION BY q.city_crash ORDER BY q.city_crash, score DESC, q.city_inv) final_rank
    FROM q
)
UPDATE lkp_city
   SET txdot_inv_id = city_inv
  FROM s
 WHERE city_id = city_crash
   AND final_rank = 1;
```

##### Counties
The same is done for counties:
```sql
WITH q AS (
    WITH r AS (SELECT gid, MAX(co) AS co FROM roadway_inv GROUP BY gid)
    SELECT c.cnty_id cnty_crash, r.co cnty_inv, COUNT(1) score
      FROM share_crash c, r, crash_buf_100 b
    WHERE c.crash_id = b.crash_id
      AND b.nearest = TRUE
      AND b.roadway_gid = r.gid
    GROUP BY c.cnty_id, r.co
), s AS (
    SELECT q.cnty_crash, q.cnty_inv,
      RANK() OVER (PARTITION BY q.cnty_crash ORDER BY q.cnty_crash, score DESC, q.cnty_inv) final_rank
    FROM q
)
UPDATE lkp_cnty
   SET txdot_inv_id = cnty_inv
  FROM s
 WHERE cnty_id = cnty_crash
   AND final_rank = 1;
```
