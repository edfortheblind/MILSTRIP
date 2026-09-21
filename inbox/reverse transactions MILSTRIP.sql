SELECT
    ID940,
    ERP_ORDER,
    DIC,
    NSN,
    ORDERQTY,
    SHIPTODODAAC,
    DATECREATED,
    BornOnDate,
    calendarDate3PL,
    OrderSourceType,
    Note3PL,
    LastProcessStamp,
    DICType,
    ranker,
    fk_shipmasterID
FROM dbo.download_ship940
WHERE OrderSourceType = 2
  AND (
        Note3PL LIKE '%_milstrip'
        OR ERP_ORDER IN
        (
            'SL470162240DCV',
            'SL470162240DDL',
            'SL470162240DDQ',
            'SL470162240DDT'
        )
      )
ORDER BY BornOnDate, ID940;



DECLARE @From datetimeoffset = '2026-08-10 00:00:00 +00:00';
DECLARE @To   datetimeoffset = '2026-08-19 00:00:00 +00:00';

SELECT
    q.query_id,

    CASE
        WHEN q.object_id = 0 THEN 'AD HOC / MANUAL'
        ELSE
            COALESCE(
                OBJECT_SCHEMA_NAME(q.object_id) + '.' +
                OBJECT_NAME(q.object_id),
                'DATABASE OBJECT'
            )
    END AS Source,

    rsi.start_time AS IntervalStartUTC,
    rsi.end_time   AS IntervalEndUTC,

    MIN(rs.first_execution_time) AS FirstExecutionUTC,
    MAX(rs.last_execution_time)  AS LastExecutionUTC,

    SUM(rs.count_executions) AS Executions,

    rs.execution_type_desc,

    qt.query_sql_text

FROM sys.query_store_query_text qt

JOIN sys.query_store_query q
    ON qt.query_text_id = q.query_text_id

JOIN sys.query_store_plan p
    ON q.query_id = p.query_id

JOIN sys.query_store_runtime_stats rs
    ON p.plan_id = rs.plan_id

JOIN sys.query_store_runtime_stats_interval rsi
    ON rs.runtime_stats_interval_id =
       rsi.runtime_stats_interval_id

WHERE
    qt.query_sql_text LIKE '%download_ship940%'
    AND rs.last_execution_time >= @From
    AND rs.first_execution_time < @To

GROUP BY
    q.query_id,
    q.object_id,
    rsi.start_time,
    rsi.end_time,
    rs.execution_type_desc,
    qt.query_sql_text

ORDER BY
    FirstExecutionUTC,
    q.query_id;



    SELECT
    q.query_id,
    q.object_id,

    CASE
        WHEN q.object_id = 0 THEN 'AD HOC / MANUAL'
        ELSE OBJECT_SCHEMA_NAME(q.object_id) + '.'
             + OBJECT_NAME(q.object_id)
    END AS Source,

    rsi.start_time
        AT TIME ZONE 'Central Standard Time'
        AS IntervalCentral,

    MIN(rs.first_execution_time)
        AT TIME ZONE 'Central Standard Time'
        AS FirstExecutionCentral,

    MAX(rs.last_execution_time)
        AT TIME ZONE 'Central Standard Time'
        AS LastExecutionCentral,

    SUM(rs.count_executions) AS Executions,

    rs.execution_type_desc,

    qt.query_sql_text

FROM sys.query_store_query q

JOIN sys.query_store_query_text qt
    ON q.query_text_id = qt.query_text_id

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
    q.object_id,
    rsi.start_time,
    rs.execution_type_desc,
    qt.query_sql_text

ORDER BY
    FirstExecutionCentral;



    SELECT
    q.query_id,
    q.object_id,
    q.initial_compile_start_time,
    q.last_compile_start_time,
    q.last_execution_time,
    st.text AS FullBatchText
FROM sys.query_store_query q

OUTER APPLY
    sys.dm_exec_sql_text(q.last_compile_batch_sql_handle) st

WHERE q.query_id = 284305;



