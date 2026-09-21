# MILSTRIP → SCALE Reverse Engineering Handoff

**Status:** Reverse engineering in progress  
**Goal:** Reconstruct the complete pre-SCALE MILSTRIP flow so it can be understood, documented, and eventually automated without changing SCALE behavior.

## 1. Current reconstructed flow

```text
Client
  │
  │ incomplete information / emails / scattered data
  ▼
SHAWN — human interpretation
  │
  │ builds fixed-width MILSTRIP
  ▼
staging_download_shipMILS
  │
  │ manual SQL helper
  │ parses positional fields + fills missing data
  │ using ItemMaster / cfg_dodaac_active / etc.
  ▼
download_ship940
  │
  ├─ 030 dedupe
  ├─ 035 initialize
  ├─ 040 cleanse
  ├─ 050 level 1 categories
  ├─ 075 level 2 categories
  ├─ 090 instruction
  └─ 125 load ShipMaster
  ▼
ShipMaster
  │
  │ initially queued
  ▼
planning / routing logic
  │
  │ dates + carrier + service + eligibility
  │ queued → New
  ▼
Boomi SELECT
  │
  │ dataset already almost ready
  ▼
Boomi mapping
  │
  ▼
.shxml
  │
  ▼
SCALE
```

## 2. Working architectural conclusion

Current evidence strongly suggests that most business logic exists in SQL before Boomi.

Boomi appears to receive a relational dataset that is already close to the final SCALE shipment structure. Working hypothesis:

- SQL performs most parsing, enrichment, categorization, validation, planning and routing.
- Boomi extracts the final SQL dataset.
- Boomi maps the dataset into Manhattan `.shxml`.
- Boomi delivers the `.shxml` to SCALE.

Do not yet assume Boomi is only a serializer; confirm field-by-field.

## 3. Manual MILSTRIP helper

The manual helper:

1. Inserts raw fixed-width MILSTRIP strings into `staging_download_shipMILS`.
2. Iterates rows where `milsStatus IS NULL`.
3. Parses fixed-width positions.
4. Enriches using reference/configuration tables.
5. Inserts a structured row into `download_ship940`.
6. Marks the staging row `milsStatus = 'SENT'`.

Known enrichment sources include:

```text
ItemMaster
cfg_dodaac_active
```

Known manual exception capability includes direct address overrides.

Rows created by this helper are marked:

```text
OrderSourceType = 2
Note3PL         = YYYYMMDD_milstrip
```

## 4. Known fixed-width parsing

Observed parsing logic:

```sql
DIC          = SUBSTRING(@mils, 1, 3)
RIC          = SUBSTRING(@mils, 4, 3)
NSN          = SUBSTRING(@mils, 8, 13)
UI           = SUBSTRING(@mils, 23, 2)
ORDERQTY     = CAST(SUBSTRING(@mils, 25, 5) AS INT)
REQUISITION  = SUBSTRING(@mils, 30, 14)
SUFFIX       = SUBSTRING(@mils, 44, 1)
SUPP_ADDR    = SUBSTRING(@mils, 45, 6)
SIGNAL_CD    = SUBSTRING(@mils, 51, 1)
FUND_CD      = SUBSTRING(@mils, 52, 2)
DIST_CD      = SUBSTRING(@mils, 54, 3)
PROJECTCODE  = SUBSTRING(@mils, 57, 3)
PRIORITYCODE = SUBSTRING(@mils, 60, 2)
RDD          = SUBSTRING(@mils, 62, 3)
ADVICECODE   = SUBSTRING(@mils, 65, 2)
OP_CD        = SUBSTRING(@mils, 70, 1)
COND_CD      = SUBSTRING(@mils, 71, 1)
```

`ERP_ORDER` is derived from requisition + suffix.

The helper also derives/resolves DODAAC and retrieves item/list-price/unit data.

## 5. `download_ship940` processing pipeline

### 030 — dedupe

Known object:

```text
dbo.sp_ship_preprocess_030_dedupe
```

Purpose:

- detect duplicate records,
- delete duplicates,
- initialize/advance `LastProcessStamp`.

### 035 — initialize

Known object:

```text
dbo.sp_ship_preprocess_035_initialize
```

Purpose:

- set `ranker`,
- set `DICType`,
- initialize classification,
- update DODAAC history/reference state,
- advance process stamp.

Observed classification:

```text
A2 / A5         → order
AC6 / ACJ / AC1 → cancel request
AF6 / AFJ       → follow-up request
```

### 040 — cleanse

Known object:

```text
dbo.sp_ship_preprocess_040_cleanse
```

Purpose:

- normalize addresses,
- uppercase address fields,
- repair known state/country combinations,
- infer country/state/ZIP where possible,
- advance process stamp.

### 050 — level 1 categories

Known object:

```text
dbo.sp_ship_preprocess_050_level1_cats
```

Derives fields including:

```text
DLAOrderType
Branch
SubAgency
FinalAddLine1
FinalAddLine2
FinalAddLine3
FinalAddLine4
FinalAddCity
FinalAddState
FinalAddZIP
FinalAddCOUNTRY
```

Also performs fallback postal logic using `cfg_dodaac_active`.

### 075 — level 2 categories

Known object:

```text
dbo.sp_ship_preprocess_075_level2_cats
```

Derives:

```text
CustomerType
TransportPriority
```

Observed categories include NAVSUP, DRMO, FMS, RTC, ROTC, AAFES and AAFES Europe.

### 090 — instruction

Known object:

```text
dbo.sp_ship_preprocess_090_instruction
```

Derives:

```text
Restriction
ImportInstruction
```

Observed instruction/routing concepts include:

```text
NAVSUP TP 1 / TP 2
DRMO
FMS
AAFES Europe TP 1 / TP 2
RTC-LAFB
RTC-Parris Island
RTC-San Diego
Puerto Rico TP 1 / TP 2
Intl TP 1
Intl TP 2 (East)
Intl TP 2 (West)
US TP 1
US TP 2
Unknown
```

### 125 — load ShipMaster

Known object:

```text
dbo.sp_ship_preprocess_125_load_ShipMaster
```

This is the main transition:

```text
download_ship940
        ↓
ShipMaster
```

The SP assembles the final shipment master record from parsed MILSTRIP data, normalized addresses, customer categorization, configuration tables, item data and UI translation.

Initial `SCALEInterfaceAction` is observed as:

```text
restricted
unknown
queued
```

depending on record state.

After successful creation:

```text
download_ship940.fk_shipmasterID
```

is populated and the process stamp reaches `125`.

## 6. Planning / routing after ShipMaster

After ShipMaster creation, additional SQL logic calculates operational fields including:

```text
SCALEInterfaceAction
PLANNED_SHIP_DATE
PLANNED_DELIVERY_DATE
CARRIER
CARRIER_SERVICE
effectiveStartDate
ExtensionDays
DoDAAC_CushionDays
ExpectTransitDays
plannedshipdays
planneddeliverdays
```

Known configuration/reference tables involved include:

```text
cfg_calendar
cfg_Planned_Shipdays
cfg_zip5
cfg_ImportInstruction
cfg_dodaac_active
```

The logic evaluates:

- work calendar,
- transport priority,
- planned delivery days,
- extension days,
- ZIP,
- DODAAC cushion,
- carrier/service,
- primary versus fallback carrier/service,
- transit days,
- eligibility.

Key state transition:

```text
queued → New
```

## 7. Probable Boomi extraction query

A repeatedly executed query selects from `ShipMaster` where:

```sql
SCALEInterfaceAction IN ('NEW')
```

and emits a nearly complete SCALE shipment dataset, including:

```text
SCALEInterfaceAction
ALLOCATE_COMPLETE
CARRIER
CARRIER_SERVICE
COMPANY
CUSTOMER
CUSTOMER_NAME
CustomerType
InitialBillCategory
VSM
ImportInstruction
SHIP_TO
SHIP_TO_ADDRESS*
SHIP_TO_CITY
SHIP_TO_COUNTRY
SHIP_TO_POSTAL_CODE
SHIP_TO_STATE
CUSTOMER_PO
FREIGHT_TERMS
DLAStartDate
DLAOrderType
PLANNED_DELIVERY_DATE
PLANNED_SHIP_DATE
PRIORITYCODE
ERP_ORDER
NOTES
TransportPriority
Restriction
Warehouse
COND_CD
MILSPARTS_sd_udf6
ShipMasterID
MARK_FOR*
NSN
ORDERQTY
STD_UP
UI
UPC
toSCALE_QUANTITY_UM
ORDER_LIST_PRICE
```

Working hypothesis:

```text
ShipMaster
   ↓
Boomi SQL extraction
   ↓
Boomi field mapping
   ↓
WMWROOT / WMWDATA / Shipments XML
   ↓
.shxml
   ↓
SCALE
```

## 8. `.shxml` structure observed

Real `ToScale*.shxml` files use a structure similar to:

```xml
<WMWROOT>
  <WMWDATA>
    <Shipments>
      <Shipment>
        <Action>New</Action>
        <AllocateComplete>Y</AllocateComplete>
        <Carrier>...</Carrier>
        <Customer>...</Customer>
        <OrderDate>...</OrderDate>
        <OrderType>...</OrderType>
        <PlannedDeliveryDateTime>...</PlannedDeliveryDateTime>
        <PlannedShipDate>...</PlannedShipDate>
        <Priority>...</Priority>
        <ShipmentId>...</ShipmentId>
        <Warehouse>TRAVIS</Warehouse>
        <Details>
          <ShipmentDetail>...</ShipmentDetail>
        </Details>
      </Shipment>
    </Shipments>
  </WMWDATA>
</WMWROOT>
```

Observed field names strongly suggest direct mapping from the final SQL extraction dataset into the XML.

## 9. Confirmed 2026-08-12 test case

Four manually created MILSTRIP records:

```text
ERP_ORDER          NSN            QTY   SHIPTODODAAC
----------------------------------------------------
SL470162240DCV     8405016819440   520   SC0141
SL470162240DDL     8405016819460   420   SC0141
SL470162240DDQ     8405016819468   300   SC0141
SL470162240DDT     8405016819531   140   SC0141
```

were inserted through the manual helper at approximately:

```text
2026-08-12 10:31 Central
```

Query Store identifies the helper insert as:

```text
query_id  = 284305
object_id = 0
Source    = AD HOC / MANUAL
Executions = 4
```

The resulting rows show:

```text
OrderSourceType  = 2
Note3PL          = 20260812_milstrip
LastProcessStamp = 125
DICType          = 1
ranker           = 1
fk_shipmasterID  = populated
```

This confirms the four records completed the SQL preprocessing path into ShipMaster.

## 10. Standard 940 path versus manual MILSTRIP path

There are at least two input routes feeding `download_ship940`.

### Standard / file-driven 940

```text
staging_download_ship940
        ↓
sp_download_ship940_015_InterfaceControl
        ↓
sp_download_ship940_020_from_staging
        ↓
download_ship940
```

Typical source marker:

```text
OrderSourceType = 1
```

### Shawn manual MILSTRIP

```text
staging_download_shipMILS
        ↓
manual helper SQL
        ↓
download_ship940
```

Source marker:

```text
OrderSourceType = 2
Note3PL = *_milstrip
```

The two routes converge at `download_ship940` and appear to use the same downstream preprocessing flow.

## 11. In-scope tables

Core:

```text
staging_download_shipMILS
download_ship940
ShipMaster
```

Reference / enrichment:

```text
ItemMaster
cfg_dodaac_active
cfg_ImportInstruction
cfg_Planned_Shipdays
cfg_zip5
cfg_calendar
cfg_UI_translate
```

Supporting / standard 940 route:

```text
staging_download_ship940
InterfaceControl
```

Possible downstream / integration support:

```text
SCALE_INTERFACE_ERROR
ShipSCALEStatus
```

## 12. In-scope stored procedures

```text
sp_download_ship940_015_InterfaceControl
sp_download_ship940_020_from_staging

sp_ship_preprocess_030_dedupe
sp_ship_preprocess_035_initialize
sp_ship_preprocess_040_cleanse
sp_ship_preprocess_050_level1_cats
sp_ship_preprocess_075_level2_cats
sp_ship_preprocess_090_instruction
sp_ship_preprocess_125_load_ShipMaster
sp_ship_preprocess_148_autocancel
```

Also identify the DB object containing the planning/routing update that changes:

```text
PLANNED_SHIP_DATE
PLANNED_DELIVERY_DATE
CARRIER
CARRIER_SERVICE
SCALEInterfaceAction
```

## 13. Open reverse-engineering questions

### Human input layer

- What exact information does the client normally provide?
- Which values are reliably present?
- Which values does Shawn infer?
- Which values does Shawn obtain from reference systems?
- Which exceptions require manual address entry?
- How are A2, A5 and A5E handled differently?

### MILSTRIP helper

- Complete fixed-width specification.
- Validation before insert.
- Meaning of `milsStatus = SENT`.
- Failure behavior if `ItemMaster` has no item.
- Failure behavior if `cfg_dodaac_active` has no DODAAC.
- Duplicate behavior.

### SQL pipeline

- Full definitions of all preprocessing SPs.
- Exact execution schedule/orchestration.
- Exact planning/routing procedure name.
- Object that transitions `New` to `SENT`.

### Boomi

- Exact SQL connector operation.
- Exact field mapping.
- Any transformations performed only in Boomi.
- File naming.
- batching/grouping rules.
- retry/error handling.
- DB update after successful export.

### SCALE

- Required/optional `.shxml` fields.
- acknowledgement/error response.
- retry/recovery behavior.

## 14. Codex instructions

1. Do not redesign yet.
2. Treat current SQL behavior as the source of truth.
3. Clearly separate confirmed behavior, inferred behavior and unknown behavior.
4. Reconstruct one real order end-to-end.
5. Preserve existing table/SP names and business terminology.
6. Do not simplify odd SQL behavior before documenting it.
7. Build a final lineage matrix:

```text
Client field / Shawn decision
→ MILSTRIP position
→ download_ship940 column
→ SQL transformation
→ ShipMaster column
→ Boomi SELECT alias
→ .shxml element
→ SCALE field
```

8. Identify hard-coded business rules.
9. Identify every manual decision currently made by Shawn.
10. Identify every reference/configuration table required to reproduce those decisions.
11. Do not propose replacement architecture until the current-state flow is materially complete.

## 15. Immediate next step

Extract schema/layout and SQL definitions for all in-scope tables and stored procedures.

Then reconstruct one of these known orders end-to-end:

```text
SL470162240DCV
SL470162240DDL
SL470162240DDQ
SL470162240DDT
```

through:

```text
download_ship940
→ ShipMaster
→ planning/routing
→ Boomi SELECT
→ .shxml
```
