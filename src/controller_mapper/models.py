from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .constants import DEFAULT_CAPTURE_THRESHOLD, DEFAULT_DEADZONE, SCHEMA_VERSION


@dataclass(frozen=True)
class DeviceInfo:
    name: str
    guid: str
    instance_id: int
    axes: int
    buttons: int
    hats: int

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RawState:
    buttons: tuple[bool, ...]
    axes: tuple[float, ...]
    hats: tuple[tuple[int, int], ...]

    @classmethod
    def from_jsonish(cls, value: dict[str, Any]) -> "RawState":
        return cls(
            buttons=tuple(bool(item) for item in value.get("buttons", ())),
            axes=tuple(float(item) for item in value.get("axes", ())),
            hats=tuple(tuple(int(part) for part in item) for item in value.get("hats", ())),
        )


def default_normalization(
    *,
    deadzone: float = DEFAULT_DEADZONE,
    capture_threshold: float = DEFAULT_CAPTURE_THRESHOLD,
) -> dict[str, Any]:
    return {
        "deadzone": deadzone,
        "capture_threshold": capture_threshold,
        "axis_directions": {},
        "trigger_ranges": {},
    }


def new_mapping(
    *,
    created_at: str,
    device: DeviceInfo,
    controls: dict[str, str | None],
    normalization: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": created_at,
        "device": device.to_json(),
        "controls": controls,
        "normalization": normalization or default_normalization(),
    }
