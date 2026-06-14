from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .capture import Candidate
from .constants import (
    AXIS_CONTROLS,
    CONTROL_BY_NAME,
    CONTROL_NAMES,
    DEFAULT_CAPTURE_THRESHOLD,
    DEFAULT_DEADZONE,
    DPAD_CONTROLS,
    TRIGGER_CONTROLS,
)
from .mapping_io import create_mapping, load_mapping, mapping_paths
from .models import DeviceInfo, RawState
from .normalize import normalize_state


WINDOW_SIZE = (1040, 680)


@dataclass(frozen=True)
class HitBox:
    x: int
    y: int
    width: int
    height: int

    def contains(self, point: tuple[int, int]) -> bool:
        px, py = point
        return self.x <= px <= self.x + self.width and self.y <= py <= self.y + self.height

    @property
    def center(self) -> tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)


@dataclass(frozen=True)
class VisualControl:
    name: str
    label: str
    shape: str
    box: HitBox


VISUAL_CONTROLS: tuple[VisualControl, ...] = (
    VisualControl("lefttrigger", "LT", "rect", HitBox(230, 214, 110, 34)),
    VisualControl("righttrigger", "RT", "rect", HitBox(700, 214, 110, 34)),
    VisualControl("leftshoulder", "LB", "rect", HitBox(240, 258, 120, 38)),
    VisualControl("rightshoulder", "RB", "rect", HitBox(680, 258, 120, 38)),
    VisualControl("dpup", "↑", "rect", HitBox(375, 300, 44, 42)),
    VisualControl("dpdown", "↓", "rect", HitBox(375, 388, 44, 42)),
    VisualControl("dpleft", "←", "rect", HitBox(329, 344, 48, 42)),
    VisualControl("dpright", "→", "rect", HitBox(417, 344, 54, 42)),
    VisualControl("leftstick", "LS", "circle", HitBox(250, 430, 96, 96)),
    VisualControl("rightstick", "RS", "circle", HitBox(610, 430, 96, 96)),
    VisualControl("y", "Y", "circle", HitBox(760, 292, 56, 56)),
    VisualControl("x", "X", "circle", HitBox(702, 350, 56, 56)),
    VisualControl("b", "B", "circle", HitBox(818, 350, 56, 56)),
    VisualControl("a", "A", "circle", HitBox(760, 408, 56, 56)),
)

CLICKABLE_CONTROLS = tuple(control for control in VISUAL_CONTROLS if control.name in CONTROL_NAMES)


@dataclass
class GuiState:
    device: DeviceInfo
    mapping: dict[str, Any]
    mapping_path: Path | None = None
    waiting_for: str | None = None
    dirty: bool = False
    status: str = "测试模式：按手柄按钮查看高亮；点击界面按钮后可重新绑定。"
    last_raw: str = "raw: --"
    saved_path: Path | None = None

    @classmethod
    def from_device(
        cls,
        device: DeviceInfo,
        *,
        mapping: dict[str, Any] | None = None,
        mapping_path: Path | None = None,
    ) -> "GuiState":
        if mapping is None:
            mapping = create_mapping(
                device=device,
                controls={name: None for name in CONTROL_NAMES},
                deadzone=DEFAULT_DEADZONE,
                capture_threshold=DEFAULT_CAPTURE_THRESHOLD,
            )
        return cls(device=device, mapping=ensure_mapping_defaults(mapping, device), mapping_path=mapping_path)

    def begin_rebind(self, control_name: str) -> None:
        if control_name not in CONTROL_BY_NAME:
            raise ValueError(f"unknown control: {control_name}")
        self.waiting_for = control_name
        title = CONTROL_BY_NAME[control_name].title_zh
        self.status = f"正在校准 {title}：请按下实际对应的物理按钮/摇杆/扳机。"

    def cancel_rebind(self) -> None:
        self.waiting_for = None
        self.status = "已取消当前校准。"

    def apply_candidate(self, candidate: Candidate) -> None:
        if self.waiting_for is None:
            return
        control_name = self.waiting_for
        controls = self.mapping.setdefault("controls", {})
        normalization = self.mapping.setdefault("normalization", {})
        controls[control_name] = candidate.code

        if control_name in AXIS_CONTROLS and candidate.kind == "axis" and candidate.axis_value is not None:
            axis_directions = normalization.setdefault("axis_directions", {})
            axis_directions[control_name] = 1 if candidate.axis_value >= 0 else -1
        if control_name in TRIGGER_CONTROLS and candidate.kind == "axis" and candidate.axis_value is not None:
            trigger_ranges = normalization.setdefault("trigger_ranges", {})
            trigger_ranges[control_name] = {
                "released": float(candidate.baseline_value or 0.0),
                "pressed": float(candidate.axis_value),
            }

        self.dirty = True
        self.waiting_for = None
        title = CONTROL_BY_NAME[control_name].title_zh
        self.status = f"已绑定 {title} -> {candidate.code}。按 S 或点击保存写入文件。"

    def active_controls(self, raw_state: RawState) -> dict[str, bool | float]:
        return active_controls_for_state(self.mapping, raw_state)

    def mapping_status(self) -> str:
        if self.mapping_path is None:
            source = "未加载映射文件"
        else:
            source = f"映射：{self.mapping_path.name}"
        if self.dirty:
            return f"{source}（有未保存修改）"
        return source


def ensure_mapping_defaults(mapping: dict[str, Any], device: DeviceInfo) -> dict[str, Any]:
    mapping.setdefault("schema_version", 1)
    mapping["device"] = device.to_json()
    controls = mapping.setdefault("controls", {})
    for name in CONTROL_NAMES:
        controls.setdefault(name, None)
    normalization = mapping.setdefault("normalization", {})
    normalization.setdefault("deadzone", DEFAULT_DEADZONE)
    normalization.setdefault("capture_threshold", DEFAULT_CAPTURE_THRESHOLD)
    normalization.setdefault("axis_directions", {})
    normalization.setdefault("trigger_ranges", {})
    return mapping


def load_mapping_for_gui(
    device: DeviceInfo,
    *,
    mapping_file: Path | None,
    output_dir: Path,
) -> tuple[dict[str, Any] | None, Path | None]:
    if mapping_file is not None:
        return load_mapping(mapping_file), mapping_file

    default_path = mapping_paths(output_dir, device)["json"]
    if default_path.exists():
        return load_mapping(default_path), default_path
    return None, None


def control_at(point: tuple[int, int]) -> str | None:
    for control in reversed(CLICKABLE_CONTROLS):
        if control.box.contains(point):
            return control.name
    return None


def active_controls_for_state(mapping: dict[str, Any], raw_state: RawState) -> dict[str, bool | float]:
    normalized = normalize_state(raw_state, mapping)
    active: dict[str, bool | float] = {}
    for name, value in normalized.items():
        if value is True:
            active[name] = True
        elif name in AXIS_CONTROLS and isinstance(value, (float, int)) and abs(float(value)) >= 0.2:
            active[name] = float(value)
        elif name in TRIGGER_CONTROLS and isinstance(value, (float, int)) and float(value) >= 0.15:
            active[name] = float(value)
        elif name in DPAD_CONTROLS and value is True:
            active[name] = True
    return active


def raw_axis_value(raw_state: RawState, index: int) -> float:
    if index < 0 or index >= len(raw_state.axes):
        return 0.0
    return max(-1.0, min(1.0, float(raw_state.axes[index])))


def stick_values_for_display(mapping: dict[str, Any], raw_state: RawState) -> dict[str, float]:
    normalized = normalize_state(raw_state, mapping)

    def _get_val(name: str, fallback_axis: int) -> float:
        val = normalized.get(name)
        if val is not None:
            return float(val)
        return raw_axis_value(raw_state, fallback_axis)

    return {
        "leftx": _get_val("leftx", 0),
        "lefty": _get_val("lefty", 1),
        "rightx": _get_val("rightx", 2),
        "righty": _get_val("righty", 3),
    }

