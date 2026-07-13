# docs/reference/ — reference producer implementations

Example code from producers, kept here so the ingest side has a concrete picture of a conformant publisher. These are **references, not owned here** — the authoritative copy lives in the producer's repo.

- `tinkle_publish.ino` — tinkle's ESP32 publisher snippet. The canonical shape of a Poop Deck producer: fire-and-forget (publishing never blocks the producer's real job), QoS 0, topic `farm/irrigation/<source>/zone<N>`, schema `v:1` JSON, UTC ISO-8601 timestamps. The DB's natural-key unique index makes replay idempotent, so a backfill ring buffer can drain on reconnect without double-counting. tinkle owns the authoritative copy.
