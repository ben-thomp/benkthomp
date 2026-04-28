"""Roadmap schedule generation, progress tracking, and admin auth."""

import hashlib
import os
import shutil
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

_INSTANCE_DIR = Path(
    os.environ.get(
        "ROADMAP_INSTANCE_DIR",
        str(Path(__file__).resolve().parent.parent.parent / "instance"),
    )
)
_DATA_DIR = Path(
    os.environ.get(
        "ROADMAP_DATA_DIR",
        str(Path(__file__).resolve().parent.parent.parent / "data"),
    )
)
_PROGRESS_FILE = _INSTANCE_DIR / "roadmap_progress.yaml"
_TEMPLATE_FILE = _DATA_DIR / "roadmap_progress_template.yaml"

_yaml = YAML()
_yaml.default_flow_style = False
_yaml.preserve_quotes = True


def _add_days(d: date, n: int) -> date:
    """Returns the date that is n days after d."""
    return d + timedelta(days=n)


def _find_section(
    data: dict[str, Any], event_type: str, label: str
) -> tuple[str, str] | None:
    """Finds a section by event type and label across all certs.

    Args:
        data: Full progress YAML data.
        event_type: The section's event type (e.g. "genai", "cpcu", "exam").
        label: The section label key.

    Returns:
        (cert_key, label) tuple, or None if not found.
    """
    for cert_key, cert in data.get("certs", {}).items():
        section = cert.get("sections", {}).get(label)
        if section is not None and section.get("type") == event_type:
            return (cert_key, label)
    return None


def _make_phase(
    types: dict[str, Any],
    phase_type: str,
    phase_start: date,
    phase_end: date,
) -> dict[str, Any]:
    type_def = types.get(phase_type, {})
    return {
        "label": type_def.get("label", phase_type.title()),
        "type": phase_type,
        "start": phase_start.isoformat(),
        "end": phase_end.isoformat(),
    }


def build_schedule(certs: dict[str, Any], types: dict[str, Any]) -> dict[str, Any]:
    """Builds the complete study schedule from the YAML certs structure.

    Iterates each cert's ordered sections list, assigning each section to
    calendar days. Exam-type sections snap to the configured exam date.
    Gantt phases are derived automatically by grouping consecutive sections
    with the same type. Phase labels and colors are resolved from the types
    block rather than hardcoded.

    Args:
        certs: The "certs" dict from the progress YAML.
        types: The "types" dict from the progress YAML.

    Returns:
        Dict with keys "schedule" (ISO-date → event list), "phases" (Gantt
        bars), "types", "start_date", "end_date", and "certs" (per-cert
        primary_type for progress tracking).
    """
    all_schedule: dict[str, list[dict[str, Any]]] = {}
    all_phases: list[dict[str, Any]] = []
    start_date: date | None = None
    end_date: date | None = None
    cert_meta: dict[str, Any] = {}

    for cert_key, cert in certs.items():
        config = cert.get("config", {})
        try:
            cert_start = date.fromisoformat(str(config.get("start", "")))
            cert_exam = date.fromisoformat(str(config.get("exam", "")))
        except (ValueError, TypeError):
            continue

        sections: dict[str, Any] = cert.get("sections", {})
        sections_list = list(sections.values())
        primary_type = sections_list[0].get("type", cert_key) if sections_list else cert_key
        cert_meta[cert_key] = {"primary_type": primary_type}

        if start_date is None or cert_start < start_date:
            start_date = cert_start

        cur = cert_start
        phase_type: str | None = None
        phase_start: date | None = None
        phase_end: date | None = None

        for label, section_data in sections.items():
            event_type = str(section_data.get("type", ""))
            duration = int(section_data.get("duration_days", 1))

            target_str = section_data.get("target")
            if target_str:
                try:
                    day_start = date.fromisoformat(str(target_str))
                except (ValueError, TypeError):
                    day_start = cur
            elif event_type == "exam":
                day_start = cert_exam
            else:
                day_start = cur

            for d in range(duration):
                day = _add_days(day_start, d)
                all_schedule.setdefault(day.isoformat(), []).append({
                    "type": event_type,
                    "label": label,
                    "complete": bool(section_data.get("complete", False)),
                })

            last_day = _add_days(day_start, duration - 1)
            if end_date is None or last_day > end_date:
                end_date = last_day

            if event_type != phase_type:
                if phase_type is not None and phase_start is not None and phase_end is not None:
                    all_phases.append(_make_phase(types, phase_type, phase_start, phase_end))
                phase_type = event_type
                phase_start = day_start
            phase_end = last_day

            if event_type != "exam":
                cur = _add_days(day_start, duration)

        if phase_type is not None and phase_start is not None and phase_end is not None:
            all_phases.append(_make_phase(types, phase_type, phase_start, phase_end))

    return {
        "schedule": all_schedule,
        "phases": all_phases,
        "types": types,
        "start_date": start_date.isoformat() if start_date else "",
        "end_date": end_date.isoformat() if end_date else "",
        "certs": cert_meta,
    }


def seed_if_missing() -> None:
    """Seeds the progress YAML from the template if it does not yet exist."""
    _INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
    if not _PROGRESS_FILE.exists():
        shutil.copy(_TEMPLATE_FILE, _PROGRESS_FILE)


def load_progress() -> Any:
    """Loads and returns the progress YAML, seeding from the template if missing."""
    seed_if_missing()
    with open(_PROGRESS_FILE, encoding="utf-8") as f:
        return _yaml.load(f)


def save_progress(data: Any) -> None:
    """Writes the progress data back to the YAML file.

    Args:
        data: The progress data object returned by load_progress.
    """
    _INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
    with open(_PROGRESS_FILE, "w", encoding="utf-8") as f:
        _yaml.dump(data, f)


def check_admin(key: str) -> bool:
    """Returns True if the SHA-256 hash of key matches ROADMAP_ADMIN_KEY.

    Args:
        key: The raw admin key supplied by the client.
    """
    expected = os.environ.get("ROADMAP_ADMIN_KEY", "")
    if not expected or not key:
        return False
    return hashlib.sha256(key.encode()).hexdigest() == expected


def toggle_section(phase_type: str, label: str, key: str) -> dict[str, Any]:
    """Toggles the completion state of a schedule section in the progress YAML.

    Args:
        phase_type: Schedule event type; used to disambiguate sections with
            the same label across certs.
        label: Section label to toggle; must exist in the progress YAML.
        key: Raw admin key; must pass check_admin or returns an error dict.

    Returns:
        Dict with "complete" (bool) and "completed_on" (ISO date or None) on
        success, or {"error": "unauthorized"} / {"error": "not found"} on failure.
    """
    if not check_admin(key):
        return {"error": "unauthorized"}

    data = load_progress()
    result = _find_section(data, phase_type, label)
    if result is None:
        return {"error": "not found"}

    cert_key, section_label = result
    section = data["certs"][cert_key]["sections"][section_label]
    now_complete = not bool(section.get("complete", False))
    section["complete"] = now_complete
    section["completed_on"] = date.today().isoformat() if now_complete else None
    save_progress(data)
    return {"complete": now_complete, "completed_on": section["completed_on"]}


def get_page_data() -> dict[str, Any]:
    """Loads progress, builds the schedule, and returns the roadmap template context.

    Returns:
        Dict with "schedule_data" (built schedule or None on config error) and
        "cert_progress" (cert_key → {label, pct}).
    """
    progress_data = load_progress()
    certs: dict[str, Any] = progress_data.get("certs", {})
    types: dict[str, Any] = progress_data.get("types", {})

    if not certs:
        return {"schedule_data": None, "cert_progress": {}}

    schedule = build_schedule(certs, types)

    if not schedule["start_date"]:
        return {"schedule_data": None, "cert_progress": {}}

    needs_save = False
    for day_key, events in schedule["schedule"].items():
        for ev in events:
            result = _find_section(progress_data, ev["type"], ev["label"])
            if result is None:
                continue
            cert_key, section_label = result
            section = progress_data["certs"][cert_key]["sections"][section_label]
            if section.get("target") is None:
                section["target"] = day_key
                needs_save = True
            ev["complete"] = bool(section.get("complete", False))

    if needs_save:
        save_progress(progress_data)

    cert_progress: dict[str, Any] = {}
    for cert_key, cert in certs.items():
        sections = cert.get("sections", {})
        sections_list = list(sections.values())
        primary_type = sections_list[0].get("type", cert_key) if sections_list else cert_key
        primary = [s for s in sections_list if s.get("type") == primary_type]
        pct = (
            round(sum(1 for s in primary if s.get("complete")) / len(primary) * 100)
            if primary
            else 0
        )
        cert_progress[cert_key] = {"label": cert.get("label", cert_key), "pct": pct}

    return {"schedule_data": schedule, "cert_progress": cert_progress}
