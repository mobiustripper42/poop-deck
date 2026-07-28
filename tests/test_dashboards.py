"""
Poop Deck :: provisioned dashboard structure tests

Grafana is the only UI here, and it is provisioned from JSON on disk
(dashboards/provisioning/dashboards/poopdeck.yml, updateIntervalSeconds 30).
A malformed or overlapping dashboard fails silently — Grafana logs and keeps
serving the previous version, so a broken panel layout can ship unnoticed.

These are structural checks only, deliberately: they assert nothing about what
a query returns (that needs the live stack) and nothing about how a panel
renders. They catch the mistakes that are actually easy to make when hand-
editing panel JSON — a stray comma, a duplicate panel id, a gridPos that
overlaps or leaves a gap after inserting a panel at the top.

Stdlib only, so they run without a venv, a broker, or a database.
"""

import json
from pathlib import Path

import pytest

DASHBOARD_DIR = Path(__file__).resolve().parent.parent / "dashboards"
DASHBOARDS = sorted(DASHBOARD_DIR.rglob("*.json"))

# Provisioning config lives under dashboards/provisioning as YAML; if a JSON
# file ever appears there it is not a dashboard and should not be asserted on.
DASHBOARDS = [p for p in DASHBOARDS if "provisioning" not in p.parts]


def _load(path):
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def test_dashboards_exist():
    """Guard the glob itself — an empty list would make every test below vacuous."""
    assert DASHBOARDS, f"no dashboard JSON found under {DASHBOARD_DIR}"


@pytest.mark.parametrize("path", DASHBOARDS, ids=lambda p: p.name)
def test_dashboard_parses_and_has_required_keys(path):
    dash = _load(path)
    for key in ("uid", "title", "schemaVersion", "panels"):
        assert key in dash, f"{path.name} missing top-level '{key}'"
    assert dash["panels"], f"{path.name} has no panels"


@pytest.mark.parametrize("path", DASHBOARDS, ids=lambda p: p.name)
def test_panel_ids_unique(path):
    ids = [p["id"] for p in _load(path)["panels"]]
    dupes = {i for i in ids if ids.count(i) > 1}
    assert not dupes, f"{path.name} has duplicate panel ids: {sorted(dupes)}"


@pytest.mark.parametrize("path", DASHBOARDS, ids=lambda p: p.name)
def test_full_width_panels_tile_without_gap_or_overlap(path):
    """
    Every panel in these dashboards is full width (w=24) and stacked, so the
    layout is correct exactly when each panel's y equals the previous panel's
    y+h. Inserting a panel at the top without shifting the rest is the failure
    this catches. Non-full-width panels are skipped rather than guessed at.
    """
    panels = sorted(_load(path)["panels"], key=lambda p: p["gridPos"]["y"])
    cursor = 0
    for panel in panels:
        grid = panel["gridPos"]
        if grid["w"] != 24:
            pytest.skip(f"{path.name} has a non-full-width panel; tiling check does not apply")
        assert grid["y"] == cursor, (
            f'{path.name} panel {panel["id"]} ("{panel["title"]}") starts at y={grid["y"]}, '
            f"expected y={cursor} — gap or overlap in the stack"
        )
        cursor = grid["y"] + grid["h"]


@pytest.mark.parametrize("path", DASHBOARDS, ids=lambda p: p.name)
def test_targets_are_raw_sql_against_the_provisioned_datasource(path):
    """
    Panels are provisioned, not UI-built, so every target should carry an
    explicit datasource uid — a target that inherits the default silently
    breaks if the default datasource ever changes.
    """
    dash = _load(path)
    for panel in dash["panels"]:
        for target in panel.get("targets", []):
            label = f'{path.name} panel {panel["id"]} target {target.get("refId")}'
            assert target.get("rawSql"), f"{label} has no rawSql"
            assert target.get("datasource", {}).get("uid"), f"{label} has no datasource uid"


@pytest.mark.parametrize("path", DASHBOARDS, ids=lambda p: p.name)
def test_no_panel_query_computes_a_stored_value(path):
    """
    DEC-001: the store never computes. That constrains migrations and daemons,
    not the read side — a dashboard is free to derive gal/min for display. This
    test only pins the boundary that would actually violate the decision: a
    dashboard query that writes.
    """
    forbidden = ("insert ", "update ", "delete ", "create ", "drop ", "alter ")
    for panel in _load(path)["panels"]:
        for target in panel.get("targets", []):
            sql = target.get("rawSql", "").lower()
            for word in forbidden:
                assert word not in sql, (
                    f'{path.name} panel {panel["id"]} issues a writing statement '
                    f"({word.strip()}) — dashboards are read-only"
                )
