"""Enclosure readings: SQLite storage, ingest validation, and queries.

Readings follow the enclosure-monitor v1 format: one object per subject per
reading, canonical units (°C, %), UTC timestamps, unknown fields ignored. An
optional `zone` (e.g. "hot", "cool") says which spot in the enclosure a sensor
measures; readings without one are stored with the empty zone "".
"""

import hmac
import math
import os
import random
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1

# Subject id -> display info. Sensors map to subjects, so swapping a sensor
# keeps the history.
SUBJECTS: dict[str, dict[str, Any]] = {
    "gregory": {
        "name": "Gregory",
        "species": "Boa constrictor",
        "desc": "Temperature and humidity in Gregory's enclosure.",
    },
    "roxy": {
        "name": "Roxy",
        "species": "Bearded dragon",
        "desc": "Temperature and humidity in Roxy's enclosure.",
        # Plan drawings live in templates/plans/<subject>/<file>.html.
        "plans": {
            "label": "6x2x2 Enclosure",
            "summary": "Planned 6 ft x 2 ft x 24 in tall enclosure: layout, then heat "
            "and light, from above and from the front.",
            "figures": [
                {"file": "color-key", "title": ""},
                {"file": "decor-top", "title": "Layout, top-down"},
                {"file": "heat-light-top", "title": "Heat and light, top-down"},
                {"file": "decor-front", "title": "Layout, front view"},
                {"file": "heat-light-front", "title": "Heat and light, front view"},
            ],
        },
    },
}

# Display names and order for known zones. Other zone ids are shown title-cased,
# after these; the empty zone (readings sent without one) comes last.
ZONE_LABELS = {"hot": "Hot side", "cool": "Cool side"}
_ZONE_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")

# Readings older than this are shown as stale (a dead Pi or sensor matters).
STALE_AFTER = timedelta(minutes=15)

# Ranges longer than this many hours are averaged into buckets for charting.
_BUCKET_AFTER_HOURS = 48
_BUCKET_SECONDS = 1800

_SCHEMA = """
CREATE TABLE IF NOT EXISTS readings (
    subject TEXT NOT NULL,
    zone TEXT NOT NULL DEFAULT '',
    ts INTEGER NOT NULL,
    temp_c REAL,
    humidity_pct REAL,
    battery_pct REAL,
    source TEXT,
    PRIMARY KEY (subject, zone, ts)
)
"""

_COLUMNS = "subject, zone, ts, temp_c, humidity_pct, battery_pct, source"


class UnknownSubject(ValueError):
    """A reading names a subject this site doesn't show."""


def _db_path() -> Path:
    default = Path(__file__).resolve().parent.parent.parent / "instance"
    return Path(os.environ.get("ENCLOSURE_DB_PATH", str(default / "enclosures.db")))


def _migrate(conn: sqlite3.Connection) -> None:
    """Adds the zone column to a pre-zone database, keeping its rows (zone '')."""
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(readings)")}
    if not columns or "zone" in columns:
        return
    with conn:
        conn.execute("ALTER TABLE readings RENAME TO readings_old")
        conn.execute(_SCHEMA)
        conn.execute(
            f"INSERT INTO readings ({_COLUMNS}) "
            "SELECT subject, '', ts, temp_c, humidity_pct, battery_pct, source "
            "FROM readings_old"
        )
        conn.execute("DROP TABLE readings_old")


def _connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    _migrate(conn)
    conn.execute(_SCHEMA)
    return conn


def check_ingest_token(token: str) -> bool:
    """Returns True if token matches ENCLOSURE_INGEST_TOKEN (unset rejects all)."""
    expected = os.environ.get("ENCLOSURE_INGEST_TOKEN", "")
    if not expected or not token:
        return False
    return hmac.compare_digest(token.encode(), expected.encode())


def zone_label(zone: str) -> str:
    """Display name for a zone id ("" for readings sent without a zone)."""
    if not zone:
        return "Enclosure"
    return ZONE_LABELS.get(zone, zone.replace("-", " ").replace("_", " ").title())


def _zone_sort_key(zone: str) -> tuple[int, str]:
    order = list(ZONE_LABELS)
    if zone in order:
        return (0, f"{order.index(zone):03}")
    return (1, zone) if zone else (2, "")


def _number(value: Any, field: str) -> float | None:
    """Validates an optional numeric field; null stays None."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a number or null")
    if not math.isfinite(value):
        raise ValueError(f"{field} must be finite")
    return float(value)


def _parse_reading(
    obj: Any,
) -> tuple[str, str, int, float | None, float | None, float | None, str]:
    """Validates one v1 reading object into a storable row."""
    if not isinstance(obj, dict):
        raise ValueError("reading must be an object")
    if obj.get("schema") != SCHEMA_VERSION:
        raise ValueError(f"unsupported schema (expected {SCHEMA_VERSION})")
    subject = obj.get("subject")
    if subject not in SUBJECTS:
        raise UnknownSubject("unknown subject")
    zone = obj.get("zone") or ""
    if zone and (not isinstance(zone, str) or not _ZONE_RE.match(zone)):
        raise ValueError("zone must be a short lowercase id like 'hot'")
    try:
        parsed = datetime.fromisoformat(str(obj.get("ts")).replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("ts must be an ISO-8601 timestamp") from None
    if parsed.tzinfo is None:
        raise ValueError("ts must include a timezone")
    ts = int(parsed.timestamp())
    if ts > int(datetime.now(timezone.utc).timestamp()) + 300:
        raise ValueError("ts is in the future")
    temp_c = _number(obj.get("temp_c"), "temp_c")
    humidity = _number(obj.get("humidity_pct"), "humidity_pct")
    battery = _number(obj.get("battery_pct"), "battery_pct")
    if humidity is not None and not 0 <= humidity <= 100:
        raise ValueError("humidity_pct must be 0-100")
    if battery is not None and not 0 <= battery <= 100:
        raise ValueError("battery_pct must be 0-100")
    source = str(obj.get("source") or "")[:64]
    return subject, zone, ts, temp_c, humidity, battery, source


def ingest(payload: Any) -> dict[str, Any]:
    """Stores one reading or a list of readings.

    Readings for subjects this site doesn't show are skipped, so adding a sensor
    on the Pi before the site knows about it can't block the others. Any other
    invalid reading rejects the whole batch.

    Returns:
        {"stored": n} (plus "skipped": n when some were skipped), or
        {"error": message} if a reading is invalid or nothing could be stored.
    """
    items = payload if isinstance(payload, list) else [payload]
    if not items or len(items) > 500:
        return {"error": "send between 1 and 500 readings"}
    rows = []
    skipped = 0
    try:
        for item in items:
            try:
                rows.append(_parse_reading(item))
            except UnknownSubject:
                skipped += 1
    except ValueError as exc:
        return {"error": str(exc)}
    if not rows:
        return {"error": "unknown subject"}
    with _connect() as conn:
        conn.executemany(
            f"INSERT OR REPLACE INTO readings ({_COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
    result: dict[str, Any] = {"stored": len(rows)}
    if skipped:
        result["skipped"] = skipped
    return result


def assign_zone(subject: str, zone: str) -> int:
    """Moves a subject's readings without a zone into `zone`; returns the count.

    For history recorded before the sensors were given zones.
    """
    if not _ZONE_RE.match(zone):
        raise ValueError("zone must be a short lowercase id like 'hot'")
    with _connect() as conn:
        cur = conn.execute(
            "UPDATE OR REPLACE readings SET zone = ? WHERE subject = ? AND zone = ''",
            (zone, subject),
        )
    return cur.rowcount


def _iso(ts: int) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _public(row: sqlite3.Row, subject: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA_VERSION,
        "subject": subject,
        "zone": row["zone"] or None,
        "ts": _iso(row["ts"]),
        "temp_c": row["temp_c"],
        "humidity_pct": row["humidity_pct"],
        "battery_pct": row["battery_pct"],
    }


def _with_stale(row: sqlite3.Row, subject: str) -> dict[str, Any]:
    reading = _public(row, subject)
    age = datetime.now(timezone.utc) - datetime.fromtimestamp(row["ts"], timezone.utc)
    reading["stale"] = age > STALE_AFTER
    reading["zone_label"] = zone_label(row["zone"])
    return reading


def get_latest(subject: str) -> dict[str, Any] | None:
    """Returns the newest reading for a subject (any zone), with a `stale` flag."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM readings WHERE subject = ? ORDER BY ts DESC LIMIT 1",
            (subject,),
        ).fetchone()
    return None if row is None else _with_stale(row, subject)


def get_latest_by_zone(subject: str) -> list[dict[str, Any]]:
    """Returns the newest reading per zone, in display order, each with `stale`.

    Once a subject has named zones, its old zone-less history is left out here.
    """
    with _connect() as conn:
        rows = conn.execute(
            "SELECT r.* FROM readings r JOIN ("
            "  SELECT zone, MAX(ts) AS ts FROM readings WHERE subject = ? GROUP BY zone"
            ") m ON r.zone = m.zone AND r.ts = m.ts WHERE r.subject = ?",
            (subject, subject),
        ).fetchall()
    if any(row["zone"] for row in rows):
        rows = [row for row in rows if row["zone"]]
    rows.sort(key=lambda row: _zone_sort_key(row["zone"]))
    return [_with_stale(row, subject) for row in rows]


def _age_text(seconds: float) -> str:
    minutes = int(seconds // 60)
    if minutes < 1:
        return "just now"
    if minutes < 60:
        return f"{minutes} min ago"
    if minutes < 24 * 60:
        return f"{minutes // 60} hr ago"
    return f"{minutes // (24 * 60)} d ago"


def get_summary(subject: str) -> dict[str, Any] | None:
    """Returns display text for the newest readings (°F, %, age), or None.

    `zones` has one entry per zone; it is stale if any zone is.
    """
    latest = get_latest_by_zone(subject)
    if not latest:
        return None
    newest = max(reading["ts"] for reading in latest)
    age = datetime.now(timezone.utc) - datetime.strptime(
        newest, "%Y-%m-%dT%H:%M:%SZ"
    ).replace(tzinfo=timezone.utc)
    zones = []
    for reading in latest:
        temp_c, humidity = reading["temp_c"], reading["humidity_pct"]
        zones.append(
            {
                "label": reading["zone_label"] if reading["zone"] else None,
                "temp_f": None if temp_c is None else f"{temp_c * 9 / 5 + 32:.1f}",
                "humidity": None if humidity is None else f"{humidity:.0f}",
            }
        )
    return {
        "zones": zones,
        "age": _age_text(age.total_seconds()),
        "stale": any(reading["stale"] for reading in latest),
    }


def get_readings(subject: str, hours: int = 24) -> list[dict[str, Any]]:
    """Returns readings from the last `hours`, oldest first, across all zones.

    Ranges over two days are averaged into 30-minute buckets per zone.
    """
    cutoff = int((datetime.now(timezone.utc) - timedelta(hours=hours)).timestamp())
    with _connect() as conn:
        if hours > _BUCKET_AFTER_HOURS:
            rows = conn.execute(
                "SELECT zone, (ts / :b) * :b AS ts, AVG(temp_c) AS temp_c, "
                "AVG(humidity_pct) AS humidity_pct, AVG(battery_pct) AS battery_pct "
                "FROM readings WHERE subject = :s AND ts >= :c "
                "GROUP BY zone, ts / :b ORDER BY ts, zone",
                {"b": _BUCKET_SECONDS, "s": subject, "c": cutoff},
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM readings WHERE subject = ? AND ts >= ? ORDER BY ts, zone",
                (subject, cutoff),
            ).fetchall()
    return [_public(row, subject) for row in rows]


def seed_demo(days: int = 30) -> int:
    """Fills the DB with synthetic readings for local previews. Not for production."""
    now = int(datetime.now(timezone.utc).timestamp()) // 300 * 300
    rng = random.Random(42)
    profiles = {
        ("gregory", "hot"): (31.0, 60.0),
        ("gregory", "cool"): (26.0, 70.0),
        ("roxy", "hot"): (38.0, 30.0),
        ("roxy", "cool"): (27.0, 38.0),
    }
    rows = []
    for (subject, zone), (base_temp, base_hum) in profiles.items():
        for i in range(days * 288):
            ts = now - i * 300
            hour = (ts % 86400) / 3600
            day = math.sin((hour - 8) * math.pi / 12)
            rows.append(
                (
                    subject,
                    zone,
                    ts,
                    round(base_temp + 2.0 * day + rng.uniform(-0.4, 0.4), 1),
                    round(base_hum - 5.0 * day + rng.uniform(-1.5, 1.5), 1),
                    88,
                    "demo",
                )
            )
    with _connect() as conn:
        conn.executemany(
            f"INSERT OR REPLACE INTO readings ({_COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
    return len(rows)
