"""
Poop Deck :: irrigation ingest daemon tests

The load-bearing tier (CLAUDE-context § Testing): validate-and-drop, unknown-v
drop, never-crash-on-poison, and — against the live stack — redelivery-is-a-no-op.
The unit tests use a fake DB seam so they run without a broker or database.
"""

import json
import os

import psycopg
import pytest

import irrigation_ingest as ing

VALID = {
    "v": 1,
    "source": "tinkle",
    "zone": 1,
    "ts_start": "2026-07-15T00:00:00Z",
    "duration_s": 600,
    "gallons": 12.5,
}


# --- fake DB / MQTT seam ---------------------------------------------------

class FakeCursor:
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        self.conn.executed.append((sql, params))
        if self.conn.raise_on_execute:
            raise psycopg.Error("simulated db failure")


class FakeConn:
    """Records execute/commit/rollback so a test can assert what the daemon did
    without a real database. Set raise_on_execute to exercise the error path."""

    def __init__(self, raise_on_execute=False):
        self.executed = []
        self.committed = 0
        self.rolled_back = 0
        self.raise_on_execute = raise_on_execute

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        self.committed += 1

    def rollback(self):
        self.rolled_back += 1


class FakeMsg:
    def __init__(self, payload, topic="farm/irrigation/tinkle/zone1"):
        if isinstance(payload, (bytes, bytearray)):
            self.payload = bytes(payload)
        else:
            self.payload = json.dumps(payload).encode()
        self.topic = topic


# --- build_row: validate-and-drop ------------------------------------------

def test_build_row_valid():
    row = ing.build_row(VALID)
    assert row["source"] == "tinkle"
    assert row["zone"] == 1
    assert row["duration_s"] == 600
    assert row["gallons"] == 12.5
    assert row["v"] == 1


def test_build_row_applies_defaults():
    payload = {k: VALID[k] for k in ("v", "source", "zone", "ts_start", "duration_s")}
    row = ing.build_row(payload)
    assert row["gallons"] is None
    assert row["fertigated"] is False
    assert row["trigger"] is None
    assert row["fault"] is None


@pytest.mark.parametrize("field", ing.REQUIRED)
def test_build_row_drops_when_required_field_missing(field):
    payload = {k: v for k, v in VALID.items() if k != field}
    assert ing.build_row(payload) is None


def test_build_row_drops_unknown_schema_version():
    payload = dict(VALID, v=2)
    assert ing.build_row(payload) is None


# --- on_message: decode + never-crash --------------------------------------

def test_on_message_valid_inserts_once():
    conn = FakeConn()
    ing.on_message(None, {"conn": conn}, FakeMsg(VALID))
    assert len(conn.executed) == 1
    assert conn.committed == 1
    sql, params = conn.executed[0]
    assert "ON CONFLICT" in sql
    assert params["source"] == "tinkle"


def test_on_message_unparseable_json_dropped():
    conn = FakeConn()
    ing.on_message(None, {"conn": conn}, FakeMsg(b"this is not json {"))
    assert conn.executed == []
    assert conn.committed == 0


def test_on_message_missing_field_no_insert():
    conn = FakeConn()
    bad = {k: v for k, v in VALID.items() if k != "duration_s"}
    ing.on_message(None, {"conn": conn}, FakeMsg(bad))
    assert conn.executed == []


def test_insert_row_db_error_never_raises():
    conn = FakeConn(raise_on_execute=True)
    # Must not propagate — a poison row can't kill the daemon.
    ing.insert_row(conn, ing.build_row(VALID))
    assert conn.rolled_back == 1
    assert conn.committed == 0


# --- redelivery-is-a-no-op: against the live stack -------------------------

@pytest.fixture
def live_conn():
    dsn = os.environ.get("PG_DSN", "postgresql://poopdeck@localhost/farm")
    try:
        conn = psycopg.connect(dsn, autocommit=False, connect_timeout=2)
    except psycopg.Error as exc:
        pytest.skip(f"no live Timescale ({exc})")
    yield conn
    conn.rollback()
    conn.close()


def test_redelivery_is_a_noop_live(live_conn):
    row = ing.build_row(dict(VALID, source="pytest-live", ts_start="2026-07-15T12:00:00Z"))

    # clean slate for this source, in case a prior run left a row
    with live_conn.cursor() as cur:
        cur.execute("DELETE FROM irrigation_runs WHERE source = %s", (row["source"],))
    live_conn.commit()

    ing.insert_row(live_conn, row)
    ing.insert_row(live_conn, row)  # QoS-1 redelivery — must be a no-op

    with live_conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM irrigation_runs WHERE source = %s", (row["source"],))
        n = cur.fetchone()[0]

    with live_conn.cursor() as cur:
        cur.execute("DELETE FROM irrigation_runs WHERE source = %s", (row["source"],))
    live_conn.commit()

    assert n == 1
