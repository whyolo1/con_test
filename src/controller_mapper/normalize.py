from __future__ import annotations

from typing import Any

from .constants import AXIS_CONTROLS, BUTTON_LIKE_CONTROLS, CONTROL_NAMES, DPAD_CONTROLS, TRIGGER_CONTROLS
from .models import RawState
from .sdl import hat_to_mask, parse_input_code


def _clip(value: float, low: float, high: float) -> float:
    return min(high, max(low, value))


def _axis_value(state: RawState, index: int) -> float:
    if index < 0 or index >= len(state.axes):
        return 0.0
    return _clip(float(state.axes[index]), -1.0, 1.0)


def _button_value(state: RawState, index: int) -> bool:
    if index < 0 or index >= len(state.buttons):
        return False
    return bool(state.buttons[index])


def _hat_value(state: RawState, index: int) -> int:
    if index < 0 or index >= len(state.hats):
        return 0
    return hat_to_mask(state.hats[index])


def _apply_deadzone(value: float, deadzone: float) -> float:
    if abs(value) < deadzone:
        return 0.0
    return _clip(value, -1.0, 1.0)


def _axis_active(value: float, half: str | None, threshold: float) -> bool:
    if half == "+":
        return value >= threshold
    if half == "-":
        return value <= -threshold
    return abs(value) >= threshold


def _normalize_trigger_axis(value: float, control: str, normalization: dict[str, Any]) -> float:
    trigger_ranges = normalization.get("trigger_ranges", {})
    range_info = trigger_ranges.get(control)
    if isinstance(range_info, dict) and "released" in range_info and "pressed" in range_info:
        released = float(range_info["released"])
        pressed = float(range_info["pressed"])
        if pressed == released:
            return 0.0
        return _clip((value - released) / (pressed - released), 0.0, 1.0)
    return _clip((value + 1.0) / 2.0, 0.0, 1.0)


def _read_bool_from_code(code: str, state: RawState, threshold: float) -> bool:
    parsed = parse_input_code(code)
    if parsed.kind == "button":
        return _button_value(state, parsed.index)
    if parsed.kind == "hat":
        return bool(_hat_value(state, parsed.index) & int(parsed.hat_mask or 0))
    if parsed.kind == "axis":
        value = _axis_value(state, parsed.index)
        if parsed.inverted:
            value = -value
        return _axis_active(value, parsed.half, threshold)
    return False


def _read_axis_from_code(code: str, state: RawState, control: str, normalization: dict[str, Any]) -> float:
    parsed = parse_input_code(code)
    deadzone = float(normalization.get("deadzone", 0.15))
    if parsed.kind == "axis":
        value = _axis_value(state, parsed.index)
        if parsed.inverted:
            value = -value
        direction = int(normalization.get("axis_directions", {}).get(control, 1))
        return _apply_deadzone(value * direction, deadzone)
    if parsed.kind == "button":
        return 1.0 if _button_value(state, parsed.index) else 0.0
    if parsed.kind == "hat":
        return 1.0 if (_hat_value(state, parsed.index) & int(parsed.hat_mask or 0)) else 0.0
    return 0.0


def _read_trigger_from_code(code: str, state: RawState, control: str, normalization: dict[str, Any]) -> float:
    parsed = parse_input_code(code)
    if parsed.kind == "button":
        return 1.0 if _button_value(state, parsed.index) else 0.0
    if parsed.kind == "hat":
        return 1.0 if (_hat_value(state, parsed.index) & int(parsed.hat_mask or 0)) else 0.0
    if parsed.kind == "axis":
        value = _axis_value(state, parsed.index)
        if parsed.inverted:
            value = -value
        if parsed.half == "+":
            return _clip(value, 0.0, 1.0)
        if parsed.half == "-":
            return _clip(-value, 0.0, 1.0)
        return _normalize_trigger_axis(value, control, normalization)
    return 0.0


def normalize_state(raw_state: RawState | dict[str, Any], mapping: dict[str, Any]) -> dict[str, bool | float | None]:
    state = raw_state if isinstance(raw_state, RawState) else RawState.from_jsonish(raw_state)
    controls = mapping.get("controls", {})
    normalization = mapping.get("normalization", {})
    threshold = float(normalization.get("capture_threshold", 0.45))

    result: dict[str, bool | float | None] = {}
    for control in CONTROL_NAMES:
        code = controls.get(control)
        if not code:
            result[control] = None
        elif control in AXIS_CONTROLS:
            result[control] = _read_axis_from_code(code, state, control, normalization)
        elif control in TRIGGER_CONTROLS:
            result[control] = _read_trigger_from_code(code, state, control, normalization)
        elif control in DPAD_CONTROLS or control in BUTTON_LIKE_CONTROLS:
            result[control] = _read_bool_from_code(code, state, threshold)
        else:
            result[control] = None
    return result
