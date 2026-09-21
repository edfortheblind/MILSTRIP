-- Pure parsing helper for the recovered owner-run MILSTRIP contract.
-- This function does not read or write legacy tables.

CREATE OR REPLACE FUNCTION milstrip_app.parse_legacy_mils(p_mils text)
RETURNS TABLE (
    dic text,
    nsn text,
    ui text,
    order_qty_raw text,
    requisition text,
    suffix text,
    supp_addr text,
    signal_cd text,
    prioritycode text,
    rdd text,
    advicecode text,
    cond_cd text,
    effective_dodaac text,
    erp_order text
)
LANGUAGE plpgsql
AS $$
DECLARE
    normalized text := rpad(p_mils, 80, ' ');
BEGIN
    IF length(p_mils) > 80 OR length(p_mils) < 71 THEN
        RAISE EXCEPTION 'MILSTRIP must be between 71 and 80 characters';
    END IF;

    RETURN QUERY
    SELECT
        upper(substr(normalized, 1, 3)),
        upper(trim(substr(normalized, 8, 13))),
        upper(substr(normalized, 23, 2)),
        upper(substr(normalized, 25, 5)),
        upper(substr(normalized, 30, 14)),
        upper(substr(normalized, 44, 1)),
        upper(substr(normalized, 45, 6)),
        upper(substr(normalized, 51, 1)),
        upper(substr(normalized, 60, 2)),
        upper(substr(normalized, 62, 3)),
        upper(substr(normalized, 65, 2)),
        upper(substr(normalized, 71, 1)),
        CASE
            WHEN upper(substr(normalized, 51, 1)) < 'J' THEN upper(substr(normalized, 30, 6))
            ELSE upper(substr(normalized, 45, 6))
        END,
        rtrim(upper(substr(normalized, 30, 14) || substr(normalized, 44, 1)));
END;
$$;