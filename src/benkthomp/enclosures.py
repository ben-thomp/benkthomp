"""Enclosure readings: SQLite storage, ingest validation, and queries.

Readings follow the enclosure-monitor v1 format: one object per subject per
reading, canonical units (°C, %), UTC timestamps, unknown fields ignored.
"""

import hmac
import math
import os
import random
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

# Readings older than this are shown as stale (a dead Pi or sensor matters).
STALE_AFTER = timedelta(minutes=15)

# Ranges longer than this many hours are averaged into buckets for charting.
_BUCKET_AFTER_HOURS = 48
_BUCKET_SECONDS = 1800

_SCHEMA = """
CREATE TABLE IF NOT EXISTS readings (
    subject TEXT NOT NULL,
    ts INTEGER NOT NULL,
    temp_c REAL,
    humidity_pct REAL,
    battery_pct REAL,
    source TEXT,
    PRIMARY KEY (subject, ts)
)
"""


def _db_path() -> Path:
    default = Path(__file__).resolve().parent.parent.parent / "instance"
    return Path(os.environ.get("ENCLOSURE_DB_PATH", str(default / "enclosures.db")))


def _connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute(_SCHEMA)
    return conn


def check_ingest_token(token: str) -> bool:
    """Returns True if token matches ENCLOSURE_INGEST_TOKEN (unset rejects all)."""
    expected = os.environ.get("ENCLOSURE_INGEST_TOKEN", "")
    if not expected or not token:
        return False
    return hmac.compare_digest(token.encode(), expected.encode())


def _number(value: Any, field: str) -> float | None:
    """Validates an optional numeric field; null stays None."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a number or null")
    if not math.isfinite(value):
        raise ValueError(f"{field} must be finite")
    return float(value)


def _parse_reading(obj: Any) -> tuple[str, int, float | None, float | None, Any, str]:
    """Validates one v1 reading object into a storable row."""
    if not isinstance(obj, dict):
        raise ValueError("reading must be an object")
    if obj.get("schema") != SCHEMA_VERSION:
        raise ValueError(f"unsupported schema (expected {SCHEMA_VERSION})")
    subject = obj.get("subject")
    if subject not in SUBJECTS:
        raise ValueError("unknown subject")
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
    return subject, ts, temp_c, humidity, battery, source


def ingest(payload: Any) -> dict[str, Any]:
    """Stores one reading or a list of readings (all-or-nothing).

    Returns:
        {"stored": n} on success, or {"error": message} if any reading is invalid.
    """
    items = payload if isinstance(payload, list) else [payload]
    if not items or len(items) > 500:
        return {"error": "send between 1 and 500 readings"}
    try:
        rows = [_parse_reading(item) for item in items]
    except ValueError as exc:
        return {"error": str(exc)}
    with _connect() as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO readings "
            "(subject, ts, temp_c, humidity_pct, battery_pct, source) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [(s, ts, t, h, b, src) for s, ts, t, h, b, src in rows],
        )
    return {"stored": len(rows)}


def _iso(ts: int) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _public(row: sqlite3.Row, subject: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA_VERSION,
        "subject": subject,
        "ts": _iso(row["ts"]),
        "temp_c": row["temp_c"],
        "humidity_pct": row["humidity_pct"],
        "battery_pct": row["battery_pct"],
    }


def get_latest(subject: str) -> dict[str, Any] | None:
    """Returns the newest reading for a subject, with a `stale` flag."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM readings WHERE subject = ? ORDER BY ts DESC LIMIT 1",
            (subject,),
        ).fetchone()
    if row is None:
        return None
    reading = _public(row, subject)
    age = datetime.now(timezone.utc) - datetime.fromtimestamp(row["ts"], timezone.utc)
    reading["stale"] = age > STALE_AFTER
    return reading


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
    """Returns display text for the newest reading (°F, %, age), or None."""
    reading = get_latest(subject)
    if reading is None:
        return None
    age = datetime.now(timezone.utc) - datetime.strptime(
        reading["ts"], "%Y-%m-%dT%H:%M:%SZ"
    ).replace(tzinfo=timezone.utc)
    temp_c, humidity = reading["temp_c"], reading["humidity_pct"]
    return {
        "temp_f": None if temp_c is None else f"{temp_c * 9 / 5 + 32:.1f}",
        "humidity": None if humidity is None else f"{humidity:.0f}",
        "age": _age_text(age.total_seconds()),
        "stale": reading["stale"],
    }


def get_readings(subject: str, hours: int = 24) -> list[dict[str, Any]]:
    """Returns readings from the last `hours`, oldest first.

    Ranges over two days are averaged into 30-minute buckets.
    """
    cutoff = int((datetime.now(timezone.utc) - timedelta(hours=hours)).timestamp())
    with _connect() as conn:
        if hours > _BUCKET_AFTER_HOURS:
            rows = conn.execute(
                "SELECT (ts / :b) * :b AS ts, AVG(temp_c) AS temp_c, "
                "AVG(humidity_pct) AS humidity_pct, AVG(battery_pct) AS battery_pct "
                "FROM readings WHERE subject = :s AND ts >= :c "
                "GROUP BY ts / :b ORDER BY ts",
                {"b": _BUCKET_SECONDS, "s": subject, "c": cutoff},
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM readings WHERE subject = ? AND ts >= ? ORDER BY ts",
                (subject, cutoff),
            ).fetchall()
    return [_public(row, subject) for row in rows]


def seed_demo(days: int = 30) -> int:
    """Fills the DB with synthetic readings for local previews. Not for production."""
    now = int(datetime.now(timezone.utc).timestamp()) // 300 * 300
    rng = random.Random(42)
    profiles = {"gregory": (28.5, 65.0), "roxy": (32.0, 35.0)}
    rows = []
    for subject, (base_temp, base_hum) in profiles.items():
        for i in range(days * 288):
            ts = now - i * 300
            hour = (ts % 86400) / 3600
            day = math.sin((hour - 8) * math.pi / 12)
            rows.append(
                (
                    subject,
                    ts,
                    round(base_temp + 2.0 * day + rng.uniform(-0.4, 0.4), 1),
                    round(base_hum - 5.0 * day + rng.uniform(-1.5, 1.5), 1),
                    88,
                    "demo",
                )
            )
    with _connect() as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO readings VALUES (?, ?, ?, ?, ?, ?)", rows
        )
    return len(rows)
