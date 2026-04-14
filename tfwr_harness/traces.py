"""Normalized trace models and recording helpers.

``TraceEvent`` should stay close to observable game behavior: ticks, elapsed
time, action category, and structured payload. Recorder helpers are harness-only
convenience for tests and debugging.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
import math
import shlex
from typing import Any


@dataclass(slots=True, frozen=True)
class TraceEvent:
    """A normalized event emitted during harness execution."""

    tick: int
    seconds: float
    category: str
    name: str
    payload: dict[str, Any] = field(default_factory=dict)
    source: str = "runtime"

    def to_dict(self) -> dict[str, Any]:
        """Return a stable serialization shape for logs and golden traces."""
        return {
            "tick": self.tick,
            "seconds": normalize_trace_value(self.seconds),
            "category": self.category,
            "name": self.name,
            "payload": normalize_trace_value(self.payload),
            "source": self.source,
        }


@dataclass(slots=True)
class TraceRecorder:
    """Collects normalized trace events during a run."""

    events: list[TraceEvent] = field(default_factory=list)

    def record(
        self,
        *,
        tick: int,
        seconds: float,
        category: str,
        name: str,
        payload: dict[str, Any] | None = None,
        source: str = "runtime",
    ) -> TraceEvent:
        """Append and return a normalized event."""
        event = TraceEvent(
            tick=tick,
            seconds=seconds,
            category=category,
            name=name,
            payload={} if payload is None else dict(payload),
            source=source,
        )
        self.events.append(event)
        return event


def normalize_trace_value(value: Any) -> Any:
    """Normalize runtime values into stable JSON-friendly forms."""
    if value is None or isinstance(value, bool | int | str):
        return value
    if isinstance(value, float):
        if math.isnan(value):
            return "nan"
        if math.isinf(value):
            return "inf" if value > 0 else "-inf"
        rounded = round(value, 6)
        if rounded.is_integer():
            return int(rounded)
        return rounded
    if isinstance(value, list | tuple):
        return [normalize_trace_value(item) for item in value]
    if isinstance(value, set):
        normalized = [normalize_trace_value(item) for item in value]
        return sorted(normalized, key=repr)
    if isinstance(value, dict):
        keys = sorted(value, key=lambda item: str(item))
        return {str(key): normalize_trace_value(value[key]) for key in keys}
    enum_value = getattr(value, "value", None)
    if isinstance(enum_value, str):
        return enum_value
    return str(value)


def normalize_trace_event(
    event: TraceEvent | dict[str, Any],
    *,
    comparison_mode: bool = False,
) -> dict[str, Any]:
    """Return a stable trace-event dict for golden files and comparisons."""
    if isinstance(event, TraceEvent):
        normalized = event.to_dict()
    else:
        normalized = {
            "tick": None if event.get("tick") is None else int(event["tick"]),
            "seconds": normalize_trace_value(event.get("seconds")),
            "category": str(event.get("category", "output")),
            "name": str(event.get("name", "quick_print")),
            "payload": normalize_trace_value(event.get("payload", {})),
            "source": str(event.get("source", "runtime")),
        }

    if (
        comparison_mode
        and normalized["category"] == "output"
        and isinstance(normalized["payload"], dict)
    ):
        normalized["payload"].pop("text", None)

    return normalized


def normalize_trace_events(
    events: list[TraceEvent] | list[dict[str, Any]],
    *,
    comparison_mode: bool = False,
) -> list[dict[str, Any]]:
    """Normalize a full trace into a stable comparison-friendly shape."""
    return [
        normalize_trace_event(event, comparison_mode=comparison_mode)
        for event in events
    ]


def normalize_output_capture_text(text: str) -> list[dict[str, Any]]:
    """Normalize raw captured output lines into structured output events.

    Supported capture lines:
    - plain quick-print style text, optionally prefixed with a numeric tick
    - one JSON object per line with trace-event fields
    """
    normalized_events: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped:
            continue

        if stripped.startswith("{"):
            parsed = json.loads(stripped)
            event = normalize_trace_event(
                {
                    "tick": parsed.get("tick"),
                    "seconds": parsed.get("seconds"),
                    "category": parsed.get("category", "output"),
                    "name": parsed.get("name", "quick_print"),
                    "payload": parsed.get("payload", {}),
                    "source": parsed.get("source", "capture"),
                },
                comparison_mode=True,
            )
            event["line"] = line_number
            normalized_events.append(event)
            continue

        tokens = shlex.split(stripped)
        tick = None
        values = tokens
        if tokens and _looks_like_int(tokens[0]):
            tick = int(tokens[0])
            values = tokens[1:]

        normalized_values = [normalize_trace_value(_parse_capture_token(token)) for token in values]
        normalized_events.append(
            {
                "line": line_number,
                "tick": tick,
                "seconds": None,
                "category": "output",
                "name": "quick_print",
                "payload": {
                    "values": normalized_values,
                },
                "source": "capture",
            }
        )

    return normalized_events


def _looks_like_int(value: str) -> bool:
    if not value:
        return False
    if value[0] in "+-":
        return value[1:].isdigit()
    return value.isdigit()


def _parse_capture_token(token: str) -> Any:
    lowered = token.lower()
    if lowered == "none":
        return None
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if _looks_like_int(token):
        return int(token)
    try:
        return float(token)
    except ValueError:
        return token
