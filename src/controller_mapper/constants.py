from __future__ import annotations

from dataclasses import dataclass


SDL_PLATFORM_DEFAULT = "Windows"
SCHEMA_VERSION = 1
DEFAULT_DEADZONE = 0.15
DEFAULT_CAPTURE_THRESHOLD = 0.45
DEFAULT_CAPTURE_TIMEOUT_SECONDS = 12.0


@dataclass(frozen=True)
class ControlSpec:
    name: str
    title: str
    title_zh: str
    kind: str
    prompt: str


CONTROL_SPECS: tuple[ControlSpec, ...] = (
    ControlSpec("a", "A / bottom face button", "A / 下方动作键", "button", "Press the A / bottom face button."),
    ControlSpec("b", "B / right face button", "B / 右侧动作键", "button", "Press the B / right face button."),
    ControlSpec("x", "X / left face button", "X / 左侧动作键", "button", "Press the X / left face button."),
    ControlSpec("y", "Y / top face button", "Y / 上方动作键", "button", "Press the Y / top face button."),
    ControlSpec("back", "Back / select", "Back / 选择键", "button", "Press Back / Select."),
    ControlSpec("guide", "Guide / home", "Guide / Home 键", "button", "Press Guide / Home."),
    ControlSpec("start", "Start / menu", "Start / 菜单键", "button", "Press Start / Menu."),
    ControlSpec("leftstick", "Left stick press", "左摇杆按下", "button", "Press the left stick."),
    ControlSpec("rightstick", "Right stick press", "右摇杆按下", "button", "Press the right stick."),
    ControlSpec("leftshoulder", "Left shoulder", "左肩键", "button", "Press the left shoulder button."),
    ControlSpec("rightshoulder", "Right shoulder", "右肩键", "button", "Press the right shoulder button."),
    ControlSpec("lefttrigger", "Left trigger", "左扳机", "trigger", "Fully press the left trigger."),
    ControlSpec("righttrigger", "Right trigger", "右扳机", "trigger", "Fully press the right trigger."),
    ControlSpec("leftx", "Left stick X", "左摇杆 X 轴", "axis", "Move the left stick to the right."),
    ControlSpec("lefty", "Left stick Y", "左摇杆 Y 轴", "axis", "Move the left stick down."),
    ControlSpec("rightx", "Right stick X", "右摇杆 X 轴", "axis", "Move the right stick to the right."),
    ControlSpec("righty", "Right stick Y", "右摇杆 Y 轴", "axis", "Move the right stick down."),
    ControlSpec("dpup", "D-pad up", "十字键上", "dpad", "Press D-pad up."),
    ControlSpec("dpdown", "D-pad down", "十字键下", "dpad", "Press D-pad down."),
    ControlSpec("dpleft", "D-pad left", "十字键左", "dpad", "Press D-pad left."),
    ControlSpec("dpright", "D-pad right", "十字键右", "dpad", "Press D-pad right."),
)

CONTROL_NAMES = tuple(spec.name for spec in CONTROL_SPECS)
CONTROL_BY_NAME = {spec.name: spec for spec in CONTROL_SPECS}
AXIS_CONTROLS = {"leftx", "lefty", "rightx", "righty"}
TRIGGER_CONTROLS = {"lefttrigger", "righttrigger"}
DPAD_CONTROLS = {"dpup", "dpdown", "dpleft", "dpright"}
BUTTON_LIKE_CONTROLS = set(CONTROL_NAMES) - AXIS_CONTROLS - TRIGGER_CONTROLS
