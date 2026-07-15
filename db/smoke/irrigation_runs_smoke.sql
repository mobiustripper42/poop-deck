-- Poop Deck :: irrigation_runs smoke check
-- Proves the schema behaves the way the dumb-store contract needs:
--   1. it's a hypertable,
--   2. the natural-key unique index exists,
--   3. a duplicate insert on the natural key is a no-op (DEC-004 idempotency),
--   4. the gallons/min query from the 0001 comment runs.
--
-- Re-runnable and side-effect-free: everything happens inside a transaction
-- that ROLLBACKs, so it never leaves test rows behind. Any failed assertion
-- raises and, with ON_ERROR_STOP, exits psql non-zero.
--
--   docker exec -i deploy-timescale-1 psql -U poopdeck -d farm \
--       -v ON_ERROR_STOP=1 -f - < db/smoke/irrigation_runs_smoke.sql

\set ON_ERROR_STOP on
BEGIN;

-- 1 + 2: schema shape
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM timescaledb_information.hypertables
        WHERE hypertable_name = 'irrigation_runs'
    ) THEN
        RAISE EXCEPTION 'irrigation_runs is not a hypertable';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE tablename = 'irrigation_runs'
          AND indexname = 'irrigation_runs_natural_key'
    ) THEN
        RAISE EXCEPTION 'natural-key unique index irrigation_runs_natural_key missing';
    END IF;
END $$;

-- 3: idempotency. Same natural key (source, zone, ts_start) twice, second with a
-- different payload — the redelivery must not double-count or overwrite.
INSERT INTO irrigation_runs (ts_start, source, zone, duration_s, gallons)
VALUES ('2026-07-15T00:00:00Z', 'smoke-test', 1, 600, 12.5)
ON CONFLICT (source, zone, ts_start) DO NOTHING;

INSERT INTO irrigation_runs (ts_start, source, zone, duration_s, gallons)
VALUES ('2026-07-15T00:00:00Z', 'smoke-test', 1, 600, 99.9)
ON CONFLICT (source, zone, ts_start) DO NOTHING;

DO $$
DECLARE
    n int;
    g real;
BEGIN
    SELECT count(*), max(gallons) INTO n, g
    FROM irrigation_runs WHERE source = 'smoke-test';

    IF n <> 1 THEN
        RAISE EXCEPTION 'expected 1 row after duplicate insert, got %', n;
    END IF;
    IF g <> 12.5 THEN
        RAISE EXCEPTION 'redelivery overwrote the row (gallons=%, expected 12.5)', g;
    END IF;
    RAISE NOTICE 'idempotency OK: duplicate natural key is a no-op';
END $$;

-- 4: the query the schema comment promises we will actually run.
SELECT zone,
       date_trunc('day', ts_start) AS day,
       SUM(gallons)                         AS gal,
       SUM(gallons) / NULLIF(SUM(duration_s), 0) * 60 AS gpm
FROM irrigation_runs
WHERE fault IS NULL
GROUP BY zone, day
ORDER BY day DESC, zone;

ROLLBACK;
