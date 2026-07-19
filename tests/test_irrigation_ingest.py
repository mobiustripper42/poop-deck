"""
Poop Deck :: irrigation ingest daemon tests

The load-bearing tier (CLAUDE-context § Testing): validate-and-drop, unknown-v
drop, never-crash-on-poison, decouple-receive-from-persist (DEC-006), worker
reconnect/backoff, and — against the live stack — redelivery-is-a-no-op. The
unit tests use fake DB/queue seams so they run without a broker or database.
"""

import json
import os
import queue
import threading

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
            # `dies` distinguishes a dropped connection (marks the conn closed,
            # like a DB restart) from a poison-row error (conn stays usable).
            if self.conn.dies:
                self.conn.closed = True
            raise psycopg.Error("simulated db failure")


class FakeConn:
    """Records execute/commit/rollback so a test can assert what the daemon did
    without a real database. raise_on_execute exercises the error path; dies
    also marks the connection closed, simulating a dropped DB connection."""

    def __init__(self, raise_on_execute=False, dies=False):
        self.executed = []
        self.committed = 0
        self.rolled_back = 0
        self.raise_on_execute = raise_on_execute
        self.dies = dies
        self.closed = False

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        self.committed += 1

    def rollback(self):
        self.rolled_back += 1

    def close(self):
        self.closed = True


class FakeMsg:
    def __init__(self, payload, topic="farm/irrigation/tinkle/zone1"):
        if isinstance(payload, (bytes, bytearray)):
            self.payload = bytes(payload)
        else:
            self.payload = json.dumps(payload).encode()
        self.topic = topic


def _userdata(maxsize=0):
    return {"queue": queue.Queue(maxsize=maxsize)}


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


@pytest.mark.parametrize("payload", [None, 42, True, "a string", [1, 2, 3]])
def test_build_row_drops_non_object_payload(payload):
    # Valid JSON but not an object — must drop, not crash.
    assert ing.build_row(payload) is None


# --- on_message: decode + enqueue + never-crash (DEC-006) ------------------

def test_on_message_valid_enqueues_once():
    ud = _userdata()
    ing.on_message(None, ud, FakeMsg(VALID))
    assert ud["queue"].qsize() == 1
    row = ud["queue"].get_nowait()
    assert row["source"] == "tinkle"
    assert row["zone"] == 1


def test_on_message_unparseable_json_not_enqueued():
    ud = _userdata()
    ing.on_message(None, ud, FakeMsg(b"this is not json {"))
    assert ud["queue"].empty()


@pytest.mark.parametrize("raw", [b"null", b"42", b"true", b'"just a string"', b"[1, 2, 3]"])
def test_on_message_non_object_json_not_enqueued(raw):
    # Valid JSON, non-object top level — the crash case. Must drop, never raise.
    ud = _userdata()
    ing.on_message(None, ud, FakeMsg(raw))
    assert ud["queue"].empty()


def test_on_message_missing_field_not_enqueued():
    ud = _userdata()
    bad = {k: v for k, v in VALID.items() if k != "duration_s"}
    ing.on_message(None, ud, FakeMsg(bad))
    assert ud["queue"].empty()


def test_on_message_queue_full_drops_and_does_not_raise():
    # DB down long enough to fill the buffer → drop-and-log, never block the
    # network thread or raise (DEC-006 bounded/logged loss).
    ud = _userdata(maxsize=1)
    ud["queue"].put_nowait({"placeholder": True})
    ing.on_message(None, ud, FakeMsg(VALID))  # must not raise
    assert ud["queue"].qsize() == 1  # the valid row was dropped, not enqueued


# --- insert_row: idempotent insert, never-raise ----------------------------

def test_insert_row_db_error_never_raises():
    conn = FakeConn(raise_on_execute=True)
    # Must not propagate — a poison row can't kill the worker.
    assert ing.insert_row(conn, ing.build_row(VALID)) is False
    assert conn.rolled_back == 1
    assert conn.committed == 0


# --- persist: survive a dropped connection on the worker (#14/#21) ----------

def test_persist_reconnects_after_dropped_connection(monkeypatch):
    # First conn dies mid-insert (like a DB restart); persist must reconnect and
    # replay the row onto a fresh connection rather than lose it.
    dead = FakeConn(raise_on_execute=True, dies=True)
    fresh = FakeConn()
    monkeypatch.setattr(ing, "connect_db", lambda dsn: fresh)

    conn = ing.persist(dead, ing.build_row(VALID), "postgresql://x")

    assert dead.rolled_back == 1     # failed attempt rolled back
    assert conn is fresh             # returns the reconnected conn for reuse
    assert fresh.committed == 1      # row landed on the reconnect


def test_persist_poison_row_does_not_reconnect(monkeypatch):
    # A row-level DB error (conn still alive) must NOT trigger a reconnect —
    # that's the drop-and-continue path, not a connection loss.
    conn = FakeConn(raise_on_execute=True, dies=False)
    called = {"connect": 0}
    monkeypatch.setattr(
        ing, "connect_db",
        lambda dsn: called.__setitem__("connect", called["connect"] + 1),
    )

    result = ing.persist(conn, ing.build_row(VALID), "postgresql://x")

    assert conn.rolled_back == 1
    assert called["connect"] == 0    # never reconnected
    assert result is conn            # same connection retained


def test_persist_reconnects_when_conn_already_closed(monkeypatch):
    # Connection already closed when persist is called → reconnect before even
    # attempting the insert (covers a conn dropped while the queue was idle).
    closed = FakeConn()
    closed.closed = True
    fresh = FakeConn()
    monkeypatch.setattr(ing, "connect_db", lambda dsn: fresh)

    conn = ing.persist(closed, ing.build_row(VALID), "postgresql://x")

    assert closed.executed == []     # never used the dead conn
    assert conn is fresh
    assert fresh.committed == 1


# --- db_worker: drains the queue and stops gracefully ----------------------

def test_db_worker_drains_then_stops(monkeypatch):
    conn = FakeConn()
    monkeypatch.setattr(ing, "connect_db", lambda dsn: conn)

    q = queue.Queue()
    q.put_nowait(ing.build_row(VALID))
    q.put_nowait(ing.build_row(dict(VALID, ts_start="2026-07-15T01:00:00Z")))

    stop = threading.Event()
    worker = threading.Thread(target=ing.db_worker, args=(q, "postgresql://x", stop))
    worker.start()
    q.join()          # both rows processed (task_done called)
    stop.set()        # then ask it to finish
    worker.join(timeout=5)

    assert not worker.is_alive()     # exited cleanly on stop
    assert conn.committed == 2       # both rows landed
    assert conn.closed               # closed its connection on the way out


def test_db_worker_finishes_in_flight_row_when_stopped(monkeypatch):
    # stop set while a row is mid-insert must NOT drop it — the worker finishes
    # the in-flight row, then exits. (Graceful drain, not abandon.)
    entered = threading.Event()
    release = threading.Event()

    class BlockingConn(FakeConn):
        def cursor(self):
            entered.set()        # signal we're inside the insert
            release.wait(2)      # ...and block there until the test releases us
            return FakeCursor(self)

    conn = BlockingConn()
    monkeypatch.setattr(ing, "connect_db", lambda dsn: conn)

    q = queue.Queue()
    q.put_nowait(ing.build_row(VALID))
    stop = threading.Event()
    worker = threading.Thread(target=ing.db_worker, args=(q, "postgresql://x", stop))
    worker.start()

    assert entered.wait(2)   # worker is now blocked mid-insert
    stop.set()               # request stop with the row still in flight
    release.set()            # let the insert complete
    worker.join(timeout=5)

    assert not worker.is_alive()
    assert conn.committed == 1   # in-flight row finished rather than being dropped


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
