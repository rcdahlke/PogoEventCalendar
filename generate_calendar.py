#!/usr/bin/env python3
"""Build a personalized iCalendar feed from ScrapedDuck's events.json."""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:  # Python 3.8
    from backports.zoneinfo import ZoneInfo, ZoneInfoNotFoundError


ROOT = Path(__file__).resolve().parent


def escape_ical(value: str) -> str:
    return (value.replace("\\", "\\\\").replace(";", "\\;")
            .replace(",", "\\,").replace("\r\n", "\\n")
            .replace("\n", "\\n").replace("\r", "\\n"))


def fold_line(line: str) -> str:
    """Fold UTF-8 lines at the RFC 5545 75-octet limit."""
    chunks: list[str] = []
    current = ""
    limit = 75
    for char in line:
        if len((current + char).encode("utf-8")) > limit:
            chunks.append(current)
            current = " " + char
            limit = 75
        else:
            current += char
    chunks.append(current)
    return "\r\n".join(chunks)


def parse_datetime(value: str, local_zone: ZoneInfo) -> datetime:
    # ScrapedDuck timestamps ending in Z are absolute UTC times. Naive
    # timestamps are already expressed in the configured local time zone.
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=local_zone)
    return parsed.astimezone(timezone.utc)


def utc_stamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_events(config: dict, source_path: Path | None) -> list[dict]:
    if source_path:
        payload = json.loads(source_path.read_text(encoding="utf-8"))
    else:
        request = urllib.request.Request(
            config["source_url"], headers={"User-Agent": "pokemon-go-calendar/1.0"}
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.load(response)
    if not isinstance(payload, list):
        raise ValueError("ScrapedDuck response must be a JSON array")
    return payload


def make_calendar(events: list[dict], config: dict) -> tuple[str, int, int]:
    try:
        local_zone = ZoneInfo(config["timezone"])
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Unknown timezone: {config['timezone']}") from exc

    allowed = set(config["included_event_types"])
    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Personal Pokemon GO Calendar//EN",
        "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
        f"X-WR-CALNAME:{escape_ical(config['calendar_name'])}",
        f"X-WR-TIMEZONE:{config['timezone']}",
    ]
    included = skipped = 0
    for event in events:
        if event.get("eventType") not in allowed:
            continue
        start_text, end_text = event.get("start"), event.get("end")
        name, link = event.get("name"), event.get("link")
        if not (start_text and end_text and name and link):
            skipped += 1
            continue
        try:
            start = parse_datetime(start_text, local_zone)
            end = parse_datetime(end_text, local_zone)
        except (ValueError, TypeError):
            skipped += 1
            continue
        if end <= start:
            skipped += 1
            continue

        uid = event.get("eventID") or link.rstrip("/").rsplit("/", 1)[-1]
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{escape_ical(str(uid))}@pokemon-go-calendar",
            f"DTSTAMP:{utc_stamp(datetime.now(timezone.utc))}",
            f"DTSTART:{utc_stamp(start)}",
            f"DTEND:{utc_stamp(end)}",
            f"SUMMARY:{escape_ical(str(name))}",
            f"URL:{link}",
            f"DESCRIPTION:{escape_ical(str(link))}",
            "END:VEVENT",
        ])
        included += 1
    lines.append("END:VCALENDAR")
    return "\r\n".join(fold_line(line) for line in lines) + "\r\n", included, skipped


def main() -> int:
    config_path = ROOT / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    source_arg = os.environ.get("EVENTS_JSON")
    source_path = Path(source_arg).resolve() if source_arg else None
    events = load_events(config, source_path)
    calendar, included, skipped = make_calendar(events, config)
    output = ROOT / config["output_file"]
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as output_file:
        output_file.write(calendar)
    print(f"Wrote {output.relative_to(ROOT)}: {included} events included, {skipped} incomplete or invalid dates skipped")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
