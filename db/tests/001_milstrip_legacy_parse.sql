BEGIN;

DO $$
DECLARE
    parsed record;
BEGIN
    SELECT * INTO parsed
    FROM milstrip_app.parse_legacy_mils(
        'A2ASTZ08405016819440  EA00520SL470162240DCV SC0141MKK      15     SMSAA'
    );

    IF parsed.dic <> 'A2A' THEN RAISE EXCEPTION 'unexpected DIC: %', parsed.dic; END IF;
    IF parsed.nsn <> '8405016819440' THEN RAISE EXCEPTION 'unexpected NSN: %', parsed.nsn; END IF;
    IF parsed.ui <> 'EA' THEN RAISE EXCEPTION 'unexpected UI: %', parsed.ui; END IF;
    IF parsed.order_qty_raw <> '00520' THEN RAISE EXCEPTION 'unexpected quantity: %', parsed.order_qty_raw; END IF;
    IF parsed.prioritycode <> '15' THEN RAISE EXCEPTION 'unexpected priority: %', parsed.prioritycode; END IF;
    IF parsed.effective_dodaac <> 'SC0141' THEN RAISE EXCEPTION 'unexpected DODAAC: %', parsed.effective_dodaac; END IF;
    IF parsed.erp_order <> 'SL470162240DCV' THEN RAISE EXCEPTION 'unexpected ERP order: %', parsed.erp_order; END IF;
END;
$$;

ROLLBACK;

\echo 'MILSTRIP PostgreSQL parser unit test passed'