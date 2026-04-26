"""Roadmap schedule generation, progress tracking, and admin auth."""

import hashlib
import os
import shutil
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

GENAI_SECTIONS: dict[str, list[str]] = {
    "Mon-0": ["1.1", "1.1.1"],
    "Tue-0": ["1.1.2"],
    "Wed-0": ["1.1.3", "1.1.4"],
    "Thu-0": ["1.2", "1.2.1"],
    "Fri-0": ["1.2.2"],
    "Mon-1": ["2.1", "2.1.1"],
    "Tue-1": ["2.1.2"],
    "Wed-1": ["2.1.3"],
    "Thu-1": ["2.2", "2.2.1"],
    "Fri-1": ["2.2.2"],
    "Mon-2": ["2.2.3"],
    "Tue-2": ["2.2.4"],
    "Wed-2": ["2.2.5"],
    "Thu-2": ["2.3", "2.3.1"],
    "Fri-2": ["2.3.2"],
    "Mon-3": ["3.1", "3.1.1"],
    "Tue-3": ["3.1.2"],
    "Wed-3": ["3.1.3", "3.1.4"],
    "Thu-3": ["3.2", "3.2.1"],
    "Fri-3": ["3.2.2", "3.2.3"],
    "Mon-4": ["3.3", "3.3.1"],
    "Tue-4": ["3.4", "3.4.1"],
    "Wed-4": ["4.1", "4.1.1"],
    "Thu-4": ["4.1.2"],
    "Fri-4": ["4.1.3"],
    "Mon-5": ["4.2", "4.2.1"],
    "Tue-5": ["4.2.2", "5.1"],
    "Wed-5": ["5.1.1", "5.1.2"],
    "Thu-5": ["5.1.3", "5.1.4"],
    "Fri-5": ["5.2", "5.2.1"],
    "Mon-6": ["5.2.2", "5.2.3"],
}

CPCU_SECTIONS: list[list[str]] = [
    ["1.1", "1.2", "1.3", "1.4", "1.5", "1.6"],
    ["2.1", "2.2", "2.3", "2.4", "2.5"],
    ["3.1", "3.2", "3.3", "3.4", "3.5", "3.6"],
    ["4.1", "4.2", "4.3", "4.4"],
    ["5.1", "5.2", "5.3", "5.4", "5.5"],
    ["6.1", "6.2", "6.3", "6.4"],
]

_JS_DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

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


def _is_weekend(d: date) -> bool:
    """Returns True if d falls on Saturday or Sunday."""
    return d.isoweekday() in (6, 7)


def _js_day_name(d: date) -> str:
    """Returns the JavaScript-convention day abbreviation (Sun…Sat) for d."""
    return _JS_DAY_NAMES[d.isoweekday() % 7]


def _progress_path(event_type: str, label: str) -> tuple[str, str] | None:
    """Maps a schedule event to its (cert_key, sub_key) path in the progress YAML.

    Args:
        event_type: Schedule event type (e.g. "genai", "study", "exam").
        label: Event label; used to distinguish which cert an exam belongs to.

    Returns:
        A (cert_key, sub_key) tuple for YAML lookup, or None if unrecognized.
    """
    if event_type == "genai":
        return ("genai", "sections")
    if event_type == "review":
        return ("genai", "review")
    if event_type == "ilc":
        return ("genai", "online_course")
    if event_type == "study":
        return ("genai", "study")
    if event_type == "cpcu":
        return ("cpcu555", "sections")
    if event_type == "exam":
        return ("cpcu555", "exam") if "CPCU" in label else ("genai", "exam")
    return None


def build_schedule(
    genai_start: date,
    cpcu_start: date,
    cpcu_exam: date,
) -> dict[str, Any]:
    """Builds the complete study schedule for Gen AI and CPCU 555.

    Args:
        genai_start: First day of Gen AI content study.
        cpcu_start: First day of CPCU 555 section study.
        cpcu_exam: Date of the CPCU 555 exam.

    Returns:
        Dict with keys "schedule" (ISO-date → event list), "phases" (Gantt bars),
        "start_date", and "end_date".
    """
    schedule: dict[str, list[dict]] = {}
    phases: list[dict] = []

    def add_event(d: date, event_type: str, label: str) -> None:
        schedule.setdefault(d.isoformat(), []).append(
            {"type": event_type, "label": label, "complete": False}
        )

    # Gen AI content: 7 weeks × 7 calendar days
    cur = genai_start
    for w in range(7):
        for _ in range(7):
            day_key = f"{_js_day_name(cur)}-{w}"
            for section in GENAI_SECTIONS.get(day_key, []):
                add_event(cur, "genai", section)
            cur = _add_days(cur, 1)

    phases.append(
        {
            "label": "Gen AI content",
            "start": genai_start.isoformat(),
            "end": _add_days(cur, -1).isoformat(),
            "type": "genai",
        }
    )

    # Review: 6 consecutive days
    review_start = cur
    for r in range(1, 7):
        add_event(cur, "review", f"Review {r}")
        cur = _add_days(cur, 1)
    phases.append(
        {
            "label": "Review (1–6)",
            "start": review_start.isoformat(),
            "end": _add_days(cur, -1).isoformat(),
            "type": "review",
        }
    )

    # Online Course: 2 days
    online_start = cur
    for _ in range(2):
        add_event(cur, "ilc", "Online Course")
        cur = _add_days(cur, 1)
    phases.append(
        {
            "label": "Online Course",
            "start": online_start.isoformat(),
            "end": _add_days(cur, -1).isoformat(),
            "type": "ilc",
        }
    )

    # Study: 2 days
    study_start = cur
    for _ in range(2):
        add_event(cur, "study", "Study")
        cur = _add_days(cur, 1)
    phases.append(
        {
            "label": "Study days",
            "start": study_start.isoformat(),
            "end": _add_days(cur, -1).isoformat(),
            "type": "study",
        }
    )

    # Gen AI exam
    exam_date = cur
    add_event(cur, "exam", "GenAI Exam")
    phases.append(
        {
            "label": "GenAI exam",
            "start": exam_date.isoformat(),
            "end": exam_date.isoformat(),
            "type": "exam",
        }
    )

    # CPCU study: weekdays only, start date read directly from config
    all_sections = [s for chapter in CPCU_SECTIONS for s in chapter]
    chapter_lengths = [len(c) for c in CPCU_SECTIONS]
    chapter_starts: list[date | None] = [None] * len(CPCU_SECTIONS)

    si = 0
    cpcu_cur = cpcu_start
    while si < len(all_sections) and cpcu_cur < cpcu_exam:
        if not _is_weekend(cpcu_cur):
            acc, ch = 0, 0
            for i, length in enumerate(chapter_lengths):
                acc += length
                if si < acc:
                    ch = i
                    break
            if chapter_starts[ch] is None:
                chapter_starts[ch] = cpcu_cur
            add_event(cpcu_cur, "cpcu", all_sections[si])
            si += 1
        cpcu_cur = _add_days(cpcu_cur, 1)

    for i in range(len(CPCU_SECTIONS)):
        ch_start = chapter_starts[i]
        if ch_start is None:
            continue
        next_start = chapter_starts[i + 1] if i < len(CPCU_SECTIONS) - 1 else None
        ch_end = _add_days(next_start, -1) if next_start else _add_days(cpcu_exam, -1)
        phases.append(
            {
                "label": f"CPCU Ch. {i + 1}",
                "start": ch_start.isoformat(),
                "end": ch_end.isoformat(),
                "type": "cpcu",
            }
        )

    add_event(cpcu_exam, "exam", "CPCU 555 Exam")
    phases.append(
        {
            "label": "CPCU 555 exam",
            "start": cpcu_exam.isoformat(),
            "end": cpcu_exam.isoformat(),
            "type": "exam",
        }
    )

    return {
        "schedule": schedule,
        "phases": phases,
        "start_date": genai_start.isoformat(),
        "end_date": cpcu_exam.isoformat(),
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
        phase_type: Schedule event type (matches types used in build_schedule).
        label: Section label to toggle; must exist in the progress YAML.
        key: Raw admin key; must pass check_admin or returns an error dict.

    Returns:
        Dict with "complete" (bool) and "completed_on" (ISO date or None) on
        success, or {"error": "unauthorized"} / {"error": "not found"} on failure.
    """
    if not check_admin(key):
        return {"error": "unauthorized"}

    path = _progress_path(phase_type, label)
    if path is None:
        return {"error": "not found"}

    cert, sub = path
    data = load_progress()
    section = data.get(cert, {}).get(sub, {}).get(label)
    if section is None:
        return {"error": "not found"}

    now_complete = not bool(section.get("complete", False))
    section["complete"] = now_complete
    section["completed_on"] = date.today().isoformat() if now_complete else None
    save_progress(data)
    return {"complete": now_complete, "completed_on": section["completed_on"]}


def get_page_data() -> dict[str, Any]:
    """Loads progress, builds the schedule, and returns the roadmap template context.

    Returns:
        Dict with "schedule_data" (built schedule or None on config error),
        "genai_pct" (int 0–100), and "cpcu_pct" (int 0–100).
    """
    progress_data = load_progress()

    try:
        genai_start = date.fromisoformat(str(progress_data["genai"]["config"]["start"]))
        cpcu_start = date.fromisoformat(
            str(progress_data["cpcu555"]["config"]["start"])
        )
        cpcu_exam = date.fromisoformat(str(progress_data["cpcu555"]["config"]["exam"]))
    except (ValueError, KeyError, TypeError):
        return {"schedule_data": None, "genai_pct": 0, "cpcu_pct": 0}

    schedule = build_schedule(genai_start, cpcu_start, cpcu_exam)

    needs_save = False
    for day_key, events in schedule["schedule"].items():
        for ev in events:
            path = _progress_path(ev["type"], ev["label"])
            if path is None:
                continue
            cert, sub = path
            section = progress_data.get(cert, {}).get(sub, {}).get(ev["label"])
            if section is not None:
                if section.get("target") is None:
                    section["target"] = day_key
                    needs_save = True
                ev["complete"] = bool(section.get("complete", False))

    if needs_save:
        save_progress(progress_data)

    def _pct(cert: str, sub: str) -> int:
        p = progress_data.get(cert, {}).get(sub, {})
        if not p:
            return 0
        done = sum(1 for v in p.values() if isinstance(v, dict) and v.get("complete"))
        return round(done / len(p) * 100)

    return {
        "schedule_data": schedule,
        "genai_pct": _pct("genai", "sections"),
        "cpcu_pct": _pct("cpcu555", "sections"),
    }
