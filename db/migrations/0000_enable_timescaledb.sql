-- Poop Deck :: enable TimescaleDB
-- Runs first (0000) so every producer's hypertable migration can call
-- create_hypertable(). Not irrigation-specific — soundings and weather need it too.
-- Self-contained on purpose: don't depend on the container image having done it.

CREATE EXTENSION IF NOT EXISTS timescaledb;
