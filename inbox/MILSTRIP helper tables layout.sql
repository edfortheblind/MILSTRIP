/*=============================================================================
  MILSTRIP -> SCALE
  DATABASE REVERSE ENGINEERING REPORT

  Purpose:
      Produce ONE complete SSMS report containing:
        1. Database information
        2. In-scope object existence
        3. Table layouts
        4. Primary keys
        5. Foreign keys
        6. Indexes
        7. Constraints
        8. Triggers
        9. Known stored procedure definitions
       10. Planning / routing object discovery
       11. Boomi extraction object discovery
       12. Dependencies
       13. Relevant Query Store statements
       14. Known MILSTRIP manual query
       15. Known probable Boomi SELECT

  IMPORTANT:
      - READ ONLY
      - Does not modify application data.
      - COLLATE DATABASE_DEFAULT is explicitly used where needed
        to avoid Latin1_General_CI_AS / SQL_Latin1_General_CP1_CI_AS conflicts.
=============================================================================*/

SET NOCOUNT ON;


/*=============================================================================
  SCOPE
=============================================================================*/

IF OBJECT_ID('tempdb..#ScopeTables') IS NOT NULL
    DROP TABLE #ScopeTables;

CREATE TABLE #ScopeTables
(
    TableName nvarchar(128) COLLATE DATABASE_DEFAULT NOT NULL PRIMARY KEY
);

INSERT INTO #ScopeTables (TableName)
VALUES
    (N'staging_download_shipMILS'),
    (N'download_ship940'),
    (N'ShipMaster'),
    (N'ItemMaster'),
    (N'cfg_dodaac_active'),
    (N'cfg_ImportInstruction'),
    (N'cfg_Planned_Shipdays'),
    (N'cfg_zip5'),
    (N'cfg_calendar'),
    (N'cfg_UI_translate'),
    (N'staging_download_ship940'),
    (N'InterfaceControl'),
    (N'SCALE_INTERFACE_ERROR'),
    (N'ShipSCALEStatus');


IF OBJECT_ID('tempdb..#ScopeProcedures') IS NOT NULL
    DROP TABLE #ScopeProcedures;

CREATE TABLE #ScopeProcedures
(
    ProcedureName nvarchar(128) COLLATE DATABASE_DEFAULT NOT NULL PRIMARY KEY
);

INSERT INTO #ScopeProcedures (ProcedureName)
VALUES
    (N'sp_download_ship940_015_InterfaceControl'),
    (N'sp_download_ship940_020_from_staging'),
    (N'sp_ship_preprocess_030_dedupe'),
    (N'sp_ship_preprocess_035_initialize'),
    (N'sp_ship_preprocess_040_cleanse'),
    (N'sp_ship_preprocess_050_level1_cats'),
    (N'sp_ship_preprocess_075_level2_cats'),
    (N'sp_ship_preprocess_090_instruction'),
    (N'sp_ship_preprocess_125_load_ShipMaster'),
    (N'sp_ship_preprocess_148_autocancel');



/*=============================================================================
  00 — REPORT HEADER / DATABASE INFORMATION
=============================================================================*/

SELECT
    [SECTION] = '00 - DATABASE INFORMATION',
    DatabaseName = DB_NAME(),
    DatabaseCollation = DATABASEPROPERTYEX(DB_NAME(), 'Collation'),
    CompatibilityLevel = compatibility_level,
    CurrentUTC = SYSUTCDATETIME(),
    CurrentServerTime = SYSDATETIME()
FROM sys.databases
WHERE name = DB_NAME();



/*=============================================================================
  01 — OBJECT EXISTENCE / TYPE

  Useful because something assumed to be a table might actually be a view,
  or an expected object might not exist.
=============================================================================*/

SELECT
    [SECTION] = '01 - IN-SCOPE OBJECT EXISTENCE',
    RequestedObject = s.TableName,
    SchemaName = SCHEMA_NAME(o.schema_id),
    ObjectName = o.name,
    ObjectType = o.type_desc,
    CreateDate = o.create_date,
    ModifyDate = o.modify_date,
    ExistsInDB =
        CASE
            WHEN o.object_id IS NULL THEN 'NO'
            ELSE 'YES'
        END
FROM #ScopeTables s
LEFT JOIN sys.objects o
    ON o.name COLLATE DATABASE_DEFAULT =
       s.TableName COLLATE DATABASE_DEFAULT
ORDER BY
    s.TableName,
    o.type_desc;



/*=============================================================================
  02 — TABLE COLUMN LAYOUT
=============================================================================*/

SELECT
    [SECTION] = '02 - TABLE COLUMN LAYOUT',

    SchemaName = sch.name,
    TableName = t.name,

    ColumnOrder = c.column_id,
    ColumnName = c.name,

    DataType =
        CASE
            WHEN ty.name IN ('varchar','char','varbinary','binary')
                THEN
                    ty.name + '(' +
                    CASE
                        WHEN c.max_length = -1 THEN 'MAX'
                        ELSE CAST(c.max_length AS varchar(10))
                    END + ')'

            WHEN ty.name IN ('nvarchar','nchar')
                THEN
                    ty.name + '(' +
                    CASE
                        WHEN c.max_length = -1 THEN 'MAX'
                        ELSE CAST(c.max_length / 2 AS varchar(10))
                    END + ')'

            WHEN ty.name IN ('decimal','numeric')
                THEN
                    ty.name + '(' +
                    CAST(c.precision AS varchar(10)) + ',' +
                    CAST(c.scale AS varchar(10)) + ')'

            WHEN ty.name IN ('datetime2','datetimeoffset','time')
                THEN
                    ty.name + '(' +
                    CAST(c.scale AS varchar(10)) + ')'

            ELSE ty.name
        END,

    MaxLengthBytes = c.max_length,
    [Precision] = c.precision,
    Scale = c.scale,

    IsNullable = c.is_nullable,
    IsIdentity = c.is_identity,
    IsComputed = c.is_computed,

    DefaultValue = dc.definition,

    Collation = c.collation_name

FROM sys.tables t

JOIN sys.schemas sch
    ON t.schema_id = sch.schema_id

JOIN #ScopeTables st
    ON t.name COLLATE DATABASE_DEFAULT =
       st.TableName COLLATE DATABASE_DEFAULT

JOIN sys.columns c
    ON t.object_id = c.object_id

JOIN sys.types ty
    ON c.user_type_id = ty.user_type_id

LEFT JOIN sys.default_constraints dc
    ON c.default_object_id = dc.object_id

ORDER BY
    sch.name,
    t.name,
    c.column_id;



/*=============================================================================
  03 — PRIMARY KEYS
=============================================================================*/

SELECT
    [SECTION] = '03 - PRIMARY KEYS',

    SchemaName = sch.name,
    TableName = t.name,

    ConstraintName = kc.name,

    ColumnOrder = ic.key_ordinal,
    ColumnName = c.name,

    IsDescending = ic.is_descending_key

FROM sys.key_constraints kc

JOIN sys.tables t
    ON kc.parent_object_id = t.object_id

JOIN sys.schemas sch
    ON t.schema_id = sch.schema_id

JOIN #ScopeTables st
    ON t.name COLLATE DATABASE_DEFAULT =
       st.TableName COLLATE DATABASE_DEFAULT

JOIN sys.index_columns ic
    ON kc.parent_object_id = ic.object_id
    AND kc.unique_index_id = ic.index_id

JOIN sys.columns c
    ON ic.object_id = c.object_id
    AND ic.column_id = c.column_id

WHERE kc.type = 'PK'

ORDER BY
    sch.name,
    t.name,
    kc.name,
    ic.key_ordinal;



/*=============================================================================
  04 — FOREIGN KEYS

  Includes FK where either side is one of our in-scope tables.
=============================================================================*/

SELECT
    [SECTION] = '04 - FOREIGN KEYS',

    FKName = fk.name,

    FromSchema = OBJECT_SCHEMA_NAME(fk.parent_object_id),
    FromTable  = OBJECT_NAME(fk.parent_object_id),
    FromColumn = pc.name,

    ToSchema = OBJECT_SCHEMA_NAME(fk.referenced_object_id),
    ToTable  = OBJECT_NAME(fk.referenced_object_id),
    ToColumn = rc.name,

    ColumnOrder = fkc.constraint_column_id,

    DeleteAction = fk.delete_referential_action_desc,
    UpdateAction = fk.update_referential_action_desc,

    IsDisabled = fk.is_disabled,
    IsNotTrusted = fk.is_not_trusted

FROM sys.foreign_keys fk

JOIN sys.foreign_key_columns fkc
    ON fk.object_id = fkc.constraint_object_id

JOIN sys.columns pc
    ON pc.object_id = fk.parent_object_id
    AND pc.column_id = fkc.parent_column_id

JOIN sys.columns rc
    ON rc.object_id = fk.referenced_object_id
    AND rc.column_id = fkc.referenced_column_id

WHERE
    EXISTS
    (
        SELECT 1
        FROM #ScopeTables st
        WHERE
            OBJECT_NAME(fk.parent_object_id)
                COLLATE DATABASE_DEFAULT
                = st.TableName COLLATE DATABASE_DEFAULT
    )
    OR
    EXISTS
    (
        SELECT 1
        FROM #ScopeTables st
        WHERE
            OBJECT_NAME(fk.referenced_object_id)
                COLLATE DATABASE_DEFAULT
                = st.TableName COLLATE DATABASE_DEFAULT
    )

ORDER BY
    FromTable,
    FKName,
    fkc.constraint_column_id;



/*=============================================================================
  05 — INDEXES
=============================================================================*/

SELECT
    [SECTION] = '05 - INDEXES',

    SchemaName = sch.name,
    TableName = t.name,

    IndexName = i.name,
    IndexType = i.type_desc,

    IsUnique = i.is_unique,
    IsPrimaryKey = i.is_primary_key,
    IsUniqueConstraint = i.is_unique_constraint,

    IndexColumnOrder = ic.index_column_id,
    KeyOrder = ic.key_ordinal,

    ColumnName = c.name,

    IsIncludedColumn = ic.is_included_column,
    IsDescending = ic.is_descending_key,

    FilterDefinition = i.filter_definition

FROM sys.tables t

JOIN sys.schemas sch
    ON t.schema_id = sch.schema_id

JOIN #ScopeTables st
    ON t.name COLLATE DATABASE_DEFAULT =
       st.TableName COLLATE DATABASE_DEFAULT

JOIN sys.indexes i
    ON t.object_id = i.object_id

JOIN sys.index_columns ic
    ON i.object_id = ic.object_id
    AND i.index_id = ic.index_id

JOIN sys.columns c
    ON ic.object_id = c.object_id
    AND ic.column_id = c.column_id

WHERE
    i.name IS NOT NULL

ORDER BY
    sch.name,
    t.name,
    i.name,
    ic.key_ordinal,
    ic.index_column_id;



/*=============================================================================
  06 — CHECK CONSTRAINTS
=============================================================================*/

SELECT
    [SECTION] = '06 - CHECK CONSTRAINTS',

    SchemaName = sch.name,
    TableName = t.name,

    ConstraintName = cc.name,
    ConstraintDefinition = cc.definition,

    IsDisabled = cc.is_disabled,
    IsNotTrusted = cc.is_not_trusted

FROM sys.check_constraints cc

JOIN sys.tables t
    ON cc.parent_object_id = t.object_id

JOIN sys.schemas sch
    ON t.schema_id = sch.schema_id

JOIN #ScopeTables st
    ON t.name COLLATE DATABASE_DEFAULT =
       st.TableName COLLATE DATABASE_DEFAULT

ORDER BY
    sch.name,
    t.name,
    cc.name;



/*=============================================================================
  07 — TRIGGERS ON IN-SCOPE TABLES
=============================================================================*/

SELECT
    [SECTION] = '07 - TRIGGERS',

    TableSchema = OBJECT_SCHEMA_NAME(tr.parent_id),
    TableName = OBJECT_NAME(tr.parent_id),

    TriggerSchema = OBJECT_SCHEMA_NAME(tr.object_id),
    TriggerName = tr.name,

    IsDisabled = tr.is_disabled,
    IsInsteadOfTrigger = tr.is_instead_of_trigger,

    CreateDate = tr.create_date,
    ModifyDate = tr.modify_date

FROM sys.triggers tr

WHERE EXISTS
(
    SELECT 1
    FROM #ScopeTables st
    WHERE
        OBJECT_NAME(tr.parent_id)
            COLLATE DATABASE_DEFAULT
            = st.TableName COLLATE DATABASE_DEFAULT
)

ORDER BY
    TableName,
    TriggerName;



/*=============================================================================
  08 — TRIGGER DEFINITIONS

  Definition is split into 4000-character chunks so an .RPT does not lose
  long source code because of SSMS text-column truncation.
=============================================================================*/

;WITH TriggerModules AS
(
    SELECT
        ObjectID = tr.object_id,
        TableSchema = OBJECT_SCHEMA_NAME(tr.parent_id),
        TableName = OBJECT_NAME(tr.parent_id),
        TriggerSchema = OBJECT_SCHEMA_NAME(tr.object_id),
        TriggerName = tr.name,
        Definition = sm.definition

    FROM sys.triggers tr

    JOIN sys.sql_modules sm
        ON tr.object_id = sm.object_id

    WHERE EXISTS
    (
        SELECT 1
        FROM #ScopeTables st
        WHERE
            OBJECT_NAME(tr.parent_id)
                COLLATE DATABASE_DEFAULT
                = st.TableName COLLATE DATABASE_DEFAULT
    )
),
Nums AS
(
    SELECT TOP (10000)
        n = ROW_NUMBER() OVER (ORDER BY (SELECT NULL))
    FROM sys.all_objects a
    CROSS JOIN sys.all_objects b
)

SELECT
    [SECTION] = '08 - TRIGGER DEFINITIONS',

    tm.TableSchema,
    tm.TableName,
    tm.TriggerSchema,
    tm.TriggerName,

    ChunkNumber = n.n,

    DefinitionChunk =
        SUBSTRING
        (
            tm.Definition,
            ((n.n - 1) * 4000) + 1,
            4000
        )

FROM TriggerModules tm

JOIN Nums n
    ON n.n <=
       CASE
           WHEN tm.Definition IS NULL THEN 0
           ELSE CEILING(LEN(tm.Definition) / 4000.0)
       END

ORDER BY
    tm.TableName,
    tm.TriggerName,
    n.n;



/*=============================================================================
  09 — KNOWN STORED PROCEDURES: EXISTENCE
=============================================================================*/

SELECT
    [SECTION] = '09 - KNOWN STORED PROCEDURES',

    RequestedProcedure = sp.ProcedureName,

    SchemaName = sch.name,
    ProcedureName = p.name,

    CreateDate = p.create_date,
    ModifyDate = p.modify_date,

    ExistsInDB =
        CASE
            WHEN p.object_id IS NULL THEN 'NO'
            ELSE 'YES'
        END

FROM #ScopeProcedures sp

LEFT JOIN sys.procedures p
    ON p.name COLLATE DATABASE_DEFAULT =
       sp.ProcedureName COLLATE DATABASE_DEFAULT

LEFT JOIN sys.schemas sch
    ON p.schema_id = sch.schema_id

ORDER BY
    sp.ProcedureName;



/*=============================================================================
  10 — KNOWN STORED PROCEDURE DEFINITIONS

  SPLIT IN 4000 CHARACTERS PER ROW.
=============================================================================*/

;WITH Modules AS
(
    SELECT
        p.object_id,
        SchemaName = sch.name,
        ProcedureName = p.name,
        p.create_date,
        p.modify_date,
        Definition = sm.definition

    FROM sys.procedures p

    JOIN sys.schemas sch
        ON p.schema_id = sch.schema_id

    JOIN sys.sql_modules sm
        ON p.object_id = sm.object_id

    JOIN #ScopeProcedures sp
        ON p.name COLLATE DATABASE_DEFAULT =
           sp.ProcedureName COLLATE DATABASE_DEFAULT
),
Nums AS
(
    SELECT TOP (10000)
        n = ROW_NUMBER() OVER (ORDER BY (SELECT NULL))
    FROM sys.all_objects a
    CROSS JOIN sys.all_objects b
)

SELECT
    [SECTION] = '10 - STORED PROCEDURE DEFINITIONS',

    m.SchemaName,
    m.ProcedureName,
    m.create_date,
    m.modify_date,

    ChunkNumber = n.n,

    DefinitionChunk =
        SUBSTRING
        (
            m.Definition,
            ((n.n - 1) * 4000) + 1,
            4000
        )

FROM Modules m

JOIN Nums n
    ON n.n <=
       CASE
           WHEN m.Definition IS NULL THEN 0
           ELSE CEILING(LEN(m.Definition) / 4000.0)
       END

ORDER BY
    m.SchemaName,
    m.ProcedureName,
    n.n;



/*=============================================================================
  11 — DISCOVER PLANNING / ROUTING OBJECTS

  Search for the business logic that turns ShipMaster from queued
  into a fully planned/routed shipment.
=============================================================================*/

SELECT DISTINCT
    [SECTION] = '11 - PLANNING ROUTING OBJECT DISCOVERY',

    ObjectType =
        CASE o.type
            WHEN 'P'  THEN 'Stored Procedure'
            WHEN 'V'  THEN 'View'
            WHEN 'FN' THEN 'Scalar Function'
            WHEN 'IF' THEN 'Inline Table Function'
            WHEN 'TF' THEN 'Table Function'
            WHEN 'TR' THEN 'Trigger'
            ELSE o.type_desc
        END,

    SchemaName = sch.name,
    ObjectName = o.name,

    o.create_date,
    o.modify_date

FROM sys.sql_modules sm

JOIN sys.objects o
    ON sm.object_id = o.object_id

JOIN sys.schemas sch
    ON o.schema_id = sch.schema_id

WHERE
       sm.definition COLLATE DATABASE_DEFAULT LIKE N'%PLANNED_SHIP_DATE%'
    OR sm.definition COLLATE DATABASE_DEFAULT LIKE N'%PLANNED_DELIVERY_DATE%'
    OR sm.definition COLLATE DATABASE_DEFAULT LIKE N'%NextSCALEInterfaceAction%'
    OR sm.definition COLLATE DATABASE_DEFAULT LIKE N'%CarrierServiceTransitDays%'
    OR sm.definition COLLATE DATABASE_DEFAULT LIKE N'%SCALEInterfaceAction%queued%'

ORDER BY
    ObjectType,
    SchemaName,
    ObjectName;



/*=============================================================================
  12 — PLANNING / ROUTING OBJECT DEFINITIONS
=============================================================================*/

;WITH CandidateModules AS
(
    SELECT DISTINCT
        o.object_id,

        ObjectType =
            CASE o.type
                WHEN 'P'  THEN 'Stored Procedure'
                WHEN 'V'  THEN 'View'
                WHEN 'FN' THEN 'Scalar Function'
                WHEN 'IF' THEN 'Inline Table Function'
                WHEN 'TF' THEN 'Table Function'
                WHEN 'TR' THEN 'Trigger'
                ELSE o.type_desc
            END,

        SchemaName = sch.name,
        ObjectName = o.name,

        Definition = sm.definition

    FROM sys.sql_modules sm

    JOIN sys.objects o
        ON sm.object_id = o.object_id

    JOIN sys.schemas sch
        ON o.schema_id = sch.schema_id

    WHERE
           sm.definition COLLATE DATABASE_DEFAULT LIKE N'%PLANNED_SHIP_DATE%'
        OR sm.definition COLLATE DATABASE_DEFAULT LIKE N'%PLANNED_DELIVERY_DATE%'
        OR sm.definition COLLATE DATABASE_DEFAULT LIKE N'%NextSCALEInterfaceAction%'
        OR sm.definition COLLATE DATABASE_DEFAULT LIKE N'%CarrierServiceTransitDays%'
        OR sm.definition COLLATE DATABASE_DEFAULT LIKE N'%SCALEInterfaceAction%queued%'
),
Nums AS
(
    SELECT TOP (10000)
        n = ROW_NUMBER() OVER (ORDER BY (SELECT NULL))
    FROM sys.all_objects a
    CROSS JOIN sys.all_objects b
)

SELECT
    [SECTION] = '12 - PLANNING ROUTING DEFINITIONS',

    cm.ObjectType,
    cm.SchemaName,
    cm.ObjectName,

    ChunkNumber = n.n,

    DefinitionChunk =
        SUBSTRING
        (
            cm.Definition,
            ((n.n - 1) * 4000) + 1,
            4000
        )

FROM CandidateModules cm

JOIN Nums n
    ON n.n <=
       CASE
           WHEN cm.Definition IS NULL THEN 0
           ELSE CEILING(LEN(cm.Definition) / 4000.0)
       END

ORDER BY
    cm.ObjectType,
    cm.SchemaName,
    cm.ObjectName,
    n.n;



/*=============================================================================
  13 — DISCOVER POSSIBLE BOOMI EXTRACTION OBJECTS
=============================================================================*/

SELECT DISTINCT
    [SECTION] = '13 - POSSIBLE BOOMI EXTRACTION OBJECTS',

    ObjectType = o.type_desc,
    SchemaName = sch.name,
    ObjectName = o.name,

    o.create_date,
    o.modify_date

FROM sys.sql_modules sm

JOIN sys.objects o
    ON sm.object_id = o.object_id

JOIN sys.schemas sch
    ON o.schema_id = sch.schema_id

WHERE
    sm.definition COLLATE DATABASE_DEFAULT LIKE N'%ShipMaster%'

AND
(
       sm.definition COLLATE DATABASE_DEFAULT LIKE N'%ALLOCATE_COMPLETE%'
    OR sm.definition COLLATE DATABASE_DEFAULT LIKE N'%MILSPARTS_sd_udf6%'
    OR sm.definition COLLATE DATABASE_DEFAULT LIKE N'%ORDER_LIST_PRICE%'
    OR sm.definition COLLATE DATABASE_DEFAULT LIKE N'%SCALEInterfaceAction%NEW%'
)

ORDER BY
    SchemaName,
    ObjectName;



/*=============================================================================
  14 — DEPENDENCIES INVOLVING IN-SCOPE TABLES
=============================================================================*/

SELECT DISTINCT
    [SECTION] = '14 - OBJECT DEPENDENCIES',

    ReferencingSchema =
        OBJECT_SCHEMA_NAME(d.referencing_id),

    ReferencingObject =
        OBJECT_NAME(d.referencing_id),

    ReferencingType =
        o.type_desc,

    ReferencedSchema =
        d.referenced_schema_name,

    ReferencedObject =
        d.referenced_entity_name,

    ReferencedDatabase =
        d.referenced_database_name,

    IsSchemaBound =
        d.is_schema_bound_reference

FROM sys.sql_expression_dependencies d

LEFT JOIN sys.objects o
    ON d.referencing_id = o.object_id

WHERE
    EXISTS
    (
        SELECT 1
        FROM #ScopeTables st
        WHERE
            d.referenced_entity_name COLLATE DATABASE_DEFAULT =
            st.TableName COLLATE DATABASE_DEFAULT
    )

    OR

    EXISTS
    (
        SELECT 1
        FROM #ScopeTables st
        WHERE
            OBJECT_NAME(d.referencing_id)
                COLLATE DATABASE_DEFAULT =
            st.TableName COLLATE DATABASE_DEFAULT
    )

ORDER BY
    ReferencedObject,
    ReferencingSchema,
    ReferencingObject;



/*=============================================================================
  15 — QUERY STORE: KNOWN MANUAL MILSTRIP HELPER

  query_id 284305
=============================================================================*/

SELECT
    [SECTION] = '15 - QUERY STORE MANUAL MILSTRIP HELPER',

    q.query_id,
    q.object_id,

    Source =
        CASE
            WHEN q.object_id = 0
                THEN 'AD HOC / MANUAL'
            ELSE
                COALESCE
                (
                    OBJECT_SCHEMA_NAME(q.object_id) + '.' +
                    OBJECT_NAME(q.object_id),
                    'DATABASE OBJECT'
                )
        END,

    q.initial_compile_start_time,
    q.last_compile_start_time,
    q.last_execution_time,

    QueryText = qt.query_sql_text

FROM sys.query_store_query q

JOIN sys.query_store_query_text qt
    ON q.query_text_id = qt.query_text_id

WHERE q.query_id = 284305;



/*=============================================================================
  16 — QUERY STORE: MANUAL MILSTRIP EXECUTION TIMELINE
=============================================================================*/

SELECT
    [SECTION] = '16 - MANUAL MILSTRIP EXECUTION TIMELINE',

    q.query_id,

    rsi.start_time AS IntervalStartUTC,
    rsi.end_time AS IntervalEndUTC,

    MIN(rs.first_execution_time) AS FirstExecutionUTC,
    MAX(rs.last_execution_time) AS LastExecutionUTC,

    SUM(rs.count_executions) AS Executions,

    rs.execution_type_desc

FROM sys.query_store_query q

JOIN sys.query_store_plan p
    ON q.query_id = p.query_id

JOIN sys.query_store_runtime_stats rs
    ON p.plan_id = rs.plan_id

JOIN sys.query_store_runtime_stats_interval rsi
    ON rs.runtime_stats_interval_id =
       rsi.runtime_stats_interval_id

WHERE q.query_id = 284305

GROUP BY
    q.query_id,
    rsi.start_time,
    rsi.end_time,
    rs.execution_type_desc

ORDER BY
    rsi.start_time;



/*=============================================================================
  17 — QUERY STORE: PROBABLE BOOMI SELECT

  We already identified query_id 236723 as highly relevant.
=============================================================================*/

SELECT
    [SECTION] = '17 - QUERY STORE PROBABLE BOOMI SELECT',

    q.query_id,
    q.object_id,

    Source =
        CASE
            WHEN q.object_id = 0
                THEN 'AD HOC / EXTERNAL'
            ELSE
                COALESCE
                (
                    OBJECT_SCHEMA_NAME(q.object_id) + '.' +
                    OBJECT_NAME(q.object_id),
                    'DATABASE OBJECT'
                )
        END,

    q.initial_compile_start_time,
    q.last_compile_start_time,
    q.last_execution_time,

    QueryText = qt.query_sql_text

FROM sys.query_store_query q

JOIN sys.query_store_query_text qt
    ON q.query_text_id = qt.query_text_id

WHERE q.query_id = 236723;



/*=============================================================================
  18 — QUERY STORE: OTHER BOOMI-LIKE EXTRACTION QUERIES
=============================================================================*/

SELECT
    [SECTION] = '18 - QUERY STORE BOOMI-LIKE QUERIES',

    q.query_id,

    Source =
        CASE
            WHEN q.object_id = 0
                THEN 'AD HOC / EXTERNAL'
            ELSE
                COALESCE
                (
                    OBJECT_SCHEMA_NAME(q.object_id) + '.' +
                    OBJECT_NAME(q.object_id),
                    'DATABASE OBJECT'
                )
        END,

    q.initial_compile_start_time,
    q.last_execution_time,

    QueryText = qt.query_sql_text

FROM sys.query_store_query_text qt

JOIN sys.query_store_query q
    ON qt.query_text_id = q.query_text_id

WHERE
(
       qt.query_sql_text COLLATE DATABASE_DEFAULT
           LIKE N'%ALLOCATE_COMPLETE%'

    OR qt.query_sql_text COLLATE DATABASE_DEFAULT
           LIKE N'%MILSPARTS_sd_udf6%'

    OR qt.query_sql_text COLLATE DATABASE_DEFAULT
           LIKE N'%ORDER_LIST_PRICE%'
)

AND qt.query_sql_text COLLATE DATABASE_DEFAULT
        LIKE N'%ShipMaster%'

ORDER BY
    q.last_execution_time DESC;



/*=============================================================================
  19 — QUERY STORE: PLANNING / ROUTING QUERIES
=============================================================================*/

SELECT
    [SECTION] = '19 - QUERY STORE PLANNING ROUTING QUERIES',

    q.query_id,

    Source =
        CASE
            WHEN q.object_id = 0
                THEN 'AD HOC / EXTERNAL'
            ELSE
                COALESCE
                (
                    OBJECT_SCHEMA_NAME(q.object_id) + '.' +
                    OBJECT_NAME(q.object_id),
                    'DATABASE OBJECT'
                )
        END,

    q.initial_compile_start_time,
    q.last_execution_time,

    QueryText = qt.query_sql_text

FROM sys.query_store_query_text qt

JOIN sys.query_store_query q
    ON qt.query_text_id = q.query_text_id

WHERE
       qt.query_sql_text COLLATE DATABASE_DEFAULT
           LIKE N'%NextSCALEInterfaceAction%'

    OR qt.query_sql_text COLLATE DATABASE_DEFAULT
           LIKE N'%CarrierServiceTransitDays%'

    OR
    (
        qt.query_sql_text COLLATE DATABASE_DEFAULT
            LIKE N'%PLANNED_SHIP_DATE%'

        AND

        qt.query_sql_text COLLATE DATABASE_DEFAULT
            LIKE N'%SCALEInterfaceAction%'
    )

ORDER BY
    q.last_execution_time DESC;



/*=============================================================================
  20 — KNOWN MANUAL MILSTRIP ORDERS: download_ship940
=============================================================================*/

SELECT
    [SECTION] = '20 - KNOWN MILSTRIP TEST CASE DOWNLOAD_SHIP940',
    *
FROM dbo.download_ship940

WHERE ERP_ORDER IN
(
    'SL470162240DCV',
    'SL470162240DDL',
    'SL470162240DDQ',
    'SL470162240DDT'
)

ORDER BY
    ID940;



/*=============================================================================
  21 — KNOWN MANUAL MILSTRIP ORDERS: ShipMaster
=============================================================================*/

SELECT
    [SECTION] = '21 - KNOWN MILSTRIP TEST CASE SHIPMASTER',
    *
FROM dbo.ShipMaster

WHERE ERP_ORDER IN
(
    'SL470162240DCV',
    'SL470162240DDL',
    'SL470162240DDQ',
    'SL470162240DDT'
)

ORDER BY
    ERP_ORDER;



/*=============================================================================
  22 — DIRECT DOWNLOAD_SHIP940 -> SHIPMASTER LINEAGE
=============================================================================*/

SELECT
    [SECTION] = '22 - DOWNLOAD_SHIP940 TO SHIPMASTER LINEAGE',

    d.ID940,
    d.ERP_ORDER,

    d.DIC,
    d.NSN,
    d.ORDERQTY,

    d.OrderSourceType,
    d.Note3PL,

    d.LastProcessStamp,
    d.DICType,
    d.ranker,

    d.fk_shipmasterID,

    sm.ShipMasterID,

    sm.SCALEInterfaceAction,

    sm.ImportInstruction,
    sm.CustomerType,
    sm.TransportPriority,

    sm.CARRIER,
    sm.CARRIER_SERVICE,

    sm.PLANNED_SHIP_DATE,
    sm.PLANNED_DELIVERY_DATE,

    sm.LastToSCALEAction,
    sm.LastToSCALETime

FROM dbo.download_ship940 d

LEFT JOIN dbo.ShipMaster sm
    ON d.fk_shipmasterID = sm.ShipMasterID

WHERE d.ERP_ORDER IN
(
    'SL470162240DCV',
    'SL470162240DDL',
    'SL470162240DDQ',
    'SL470162240DDT'
)

ORDER BY
    d.ID940;



/*=============================================================================
  END
=============================================================================*/

SELECT
    [SECTION] = 'END OF REPORT',
    CompletedUTC = SYSUTCDATETIME(),
    DatabaseName = DB_NAME();
