-- Poop Deck :: farm/irrigation slice
-- One row per zone, per run. Blessed payload v1.

CREATE TABLE IF NOT EXISTS irrigation_runs (
    ts_start    TIMESTAMPTZ  NOT NULL,
    source      TEXT         NOT NULL,
    zone        SMALLINT     NOT NULL,
    duration_s  INTEGER      NOT NULL,
    gallons     REAL,
    fertigated  BOOLEAN      NOT NULL DEFAULT FALSE,
    trigger     TEXT,
    fault       TEXT,
    schema_v    SMALLINT     NOT NULL DEFAULT 1,
    received_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

SELECT create_hypertable('irrigation_runs', 'ts_start', if_not_exists => TRUE);

-- QoS 1 can redeliver. This makes a duplicate a no-op instead of a double-count.
CREATE UNIQUE INDEX IF NOT EXISTS irrigation_runs_natural_key
    ON irrigation_runs (source, zone, ts_start);

-- The query you'll actually run: gallons/minute by zone, to catch the far-end
-- under-delivery you already suspect from the EC gradient.
--
--   SELECT zone,
--          date_trunc('day', ts_start) AS day,
--          SUM(gallons) AS gal,
--          SUM(gallons) / NULLIF(SUM(duration_s), 0) * 60 AS gpm
--   FROM irrigation_runs
--   WHERE fault IS NULL
--   GROUP BY zone, day
--   ORDER BY day DESC, zone;

-- Retention: irrigation events are tiny. A run every 15 min all season is
-- ~4k rows/year. Keep raw forever; no downsampling needed. Video is the
-- arm with a disk problem, not this one.
