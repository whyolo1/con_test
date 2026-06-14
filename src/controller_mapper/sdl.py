from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .constants import CONTROL_NAMES, SDL_PLATFORM_DEFAULT


BUTTON_RE = re.compile(r"^b(?P<index>\d+)$")
AXIS_RE = re.compile(r"^(?P<invert>~)?(?P<half>[+-])?a(?P<index>\d+)$")
HAT_RE = re.compile(r"^h(?P<index>\d+)\.(?P<mask>[1248])$")


@dataclass(frozen=True)
class InputCode:
    kind: str
    index: int
    half: str | None = None
    inverted: bool = False
    hat_mask: int | None = None


def parse_input_code(code: str) -> InputCode:
    if not isinstance(code, str) or not code:
        raise ValueError("input code must be a non-empty string")

    if match := BUTTON_RE.match(code):
        return InputCode(kind="button", index=int(match.group("index")))
    if match := AXIS_RE.match(code):
        return InputCode(
            kind="axis",
            index=int(match.group("index")),
            half=match.group("half"),
            inverted=bool(match.group("invert")),
        )
    if match := HAT_RE.match(code):
        return InputCode(kind="hat", index=int(match.group("index")), hat_mask=int(match.group("mask")))
    raise ValueError(f"unsupported input code: {code}")


def hat_to_mask(position: tuple[int, int]) -> int:
    x, y = position
    mask = 0
    if y > 0:
        mask |= 1
    if x > 0:
        mask |= 2
    if y < 0:
        mask |= 4
    if x < 0:
        mask |= 8
    return mask


def make_axis_code(index: int, *, half: str | None = None, inverted: bool = False) -> str:
    prefix = "~" if inverted else ""
    if half:
        prefix += half
    return f"{prefix}a{index}"


def make_hat_code(index: int, mask: int) -> str:
    if mask not in {1, 2, 4, 8}:
        raise ValueError(f"unsupported hat mask: {mask}")
    return f"h{index}.{mask}"


def input_code_to_sdl(control: str, code: str, normalization: dict[str, Any] | None = None) -> str:
    parsed = parse_input_code(code)
    if parsed.kind != "axis":
        return code

    axis_directions = (normalization or {}).get("axis_directions", {})
    direction = int(axis_directions.get(control, 1))
    if direction < 0 and not parsed.inverted:
        return make_axis_code(parsed.index, half=parsed.half, inverted=True)
    return code


def build_sdl_mapping(
    mapping: dict[str, Any],
    *,
    platform: str = SDL_PLATFORM_DEFAULT,
    include_unmapped: bool = False,
) -> str:
    device = mapping.get("device", {})
    guid = str(device.get("guid") or "").strip()
    name = str(device.get("name") or "Unknown Controller").replace(",", " ").strip()
    if not guid:
        raise ValueError("mapping device.guid is required for SDL export")

    normalization = mapping.get("normalization", {})
    controls = mapping.get("controls", {})
    parts = [guid, name]
    for control in CONTROL_NAMES:
        code = controls.get(control)
        if code:
            parts.append(f"{control}:{input_code_to_sdl(control, code, normalization)}")
        elif include_unmapped:
            parts.append(f"{control}:")
    parts.append(f"platform:{platform}")
    return ",".join(parts) + ","
