from __future__ import annotations

from .models import RawState
from .sdl import hat_to_mask


def hat_mask_name(mask: int) -> str:
    if mask == 0:
        return "center"
    parts: list[str] = []
    if mask & 1:
        parts.append("up")
    if mask & 2:
        parts.append("right")
    if mask & 4:
        parts.append("down")
    if mask & 8:
        parts.append("left")
    return "+".join(parts)


def describe_input_code(code: str) -> str:
    if code.startswith("b") and code[1:].isdigit():
        return f"第 {code[1:]} 号按钮"
    axis_code = code.replace("~", "").replace("+", "").replace("-", "")
    if axis_code.startswith("a") and axis_code[1:].isdigit():
        return f"第 {axis_code[1:]} 号轴"
    if code.startswith("h"):
        return f"hat/十字键输入 {code}"
    return code


def format_all_state(state: RawState) -> list[str]:
    button_values = " ".join(
        f"b{index}={'1' if pressed else '0'}"
        for index, pressed in enumerate(state.buttons)
    )
    axis_values = " ".join(
        f"a{index}={value:+.2f}"
        for index, value in enumerate(state.axes)
    )
    hat_values = " ".join(
        f"h{index}={hat_mask_name(hat_to_mask(position))}"
        for index, position in enumerate(state.hats)
    )
    return [
        f"buttons: {button_values or '(none)'}",
        f"axes: {axis_values or '(none)'}",
        f"hats: {hat_values or '(none)'}",
    ]


def diff_raw_states(
    previous: RawState,
    current: RawState,
    *,
    axis_threshold: float = 0.05,
) -> list[str]:
    lines: list[str] = []

    max_buttons = max(len(previous.buttons), len(current.buttons))
    for index in range(max_buttons):
        before = previous.buttons[index] if index < len(previous.buttons) else False
        after = current.buttons[index] if index < len(current.buttons) else False
        if before != after:
            state = "pressed" if after else "released"
            lines.append(f"button {index} {state}")

    max_axes = max(len(previous.axes), len(current.axes))
    for index in range(max_axes):
        before = previous.axes[index] if index < len(previous.axes) else 0.0
        after = current.axes[index] if index < len(current.axes) else 0.0
        if abs(after - before) >= axis_threshold:
            lines.append(f"axis {index} = {before:+.2f} -> {after:+.2f}")

    max_hats = max(len(previous.hats), len(current.hats))
    for index in range(max_hats):
        before_pos = previous.hats[index] if index < len(previous.hats) else (0, 0)
        after_pos = current.hats[index] if index < len(current.hats) else (0, 0)
        before = hat_to_mask(before_pos)
        after = hat_to_mask(after_pos)
        if before != after:
            lines.append(f"hat {index} = {hat_mask_name(after)}")

    return lines
