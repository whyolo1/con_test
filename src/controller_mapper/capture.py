from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .constants import CONTROL_SPECS, DEFAULT_CAPTURE_TIMEOUT_SECONDS, SDL_PLATFORM_DEFAULT
from .mapping_io import create_mapping, save_mapping_files
from .models import DeviceInfo, RawState
from .monitor import describe_input_code
from .sdl import hat_to_mask, make_axis_code, make_hat_code


class MissingPygameError(RuntimeError):
    pass


def _load_pygame():
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    try:
        import pygame  # type: ignore
    except ImportError as exc:
        raise MissingPygameError(
            "没有安装 pygame。请先运行: python -m pip install -e ."
        ) from exc
    return pygame


@dataclass(frozen=True)
class Candidate:
    code: str
    score: float
    kind: str
    axis_value: float | None = None
    baseline_value: float | None = None


class PygameJoystickReader:
    def __init__(self) -> None:
        self.pygame = _load_pygame()
        self.pygame.init()
        self.pygame.joystick.init()

    def close(self) -> None:
        self.pygame.joystick.quit()
        self.pygame.quit()

    def list_devices(self) -> list[tuple[int, DeviceInfo]]:
        devices: list[tuple[int, DeviceInfo]] = []
        for index in range(self.pygame.joystick.get_count()):
            joystick = self.pygame.joystick.Joystick(index)
            devices.append((index, self._device_info(joystick)))
        return devices

    def open(self, index: int):
        return self.pygame.joystick.Joystick(index)

    def _device_info(self, joystick: Any) -> DeviceInfo:
        return DeviceInfo(
            name=str(joystick.get_name()),
            guid=str(joystick.get_guid()),
            instance_id=int(joystick.get_instance_id()),
            axes=int(joystick.get_numaxes()),
            buttons=int(joystick.get_numbuttons()),
            hats=int(joystick.get_numhats()),
        )

    def snapshot(self, joystick: Any) -> RawState:
        self.pygame.event.pump()
        return RawState(
            buttons=tuple(bool(joystick.get_button(i)) for i in range(joystick.get_numbuttons())),
            axes=tuple(float(joystick.get_axis(i)) for i in range(joystick.get_numaxes())),
            hats=tuple(tuple(int(part) for part in joystick.get_hat(i)) for i in range(joystick.get_numhats())),
        )


def action_hint(kind: str) -> str:
    if kind == "axis":
        return "推动对应摇杆到提示方向，幅度尽量推到底。"
    if kind == "trigger":
        return "把对应扳机完全按到底。"
    if kind == "dpad":
        return "按住十字键对应方向。"
    return "按一下对应按钮。"


def detect_candidates(
    baseline: RawState,
    current: RawState,
    *,
    expected_kind: str,
    threshold: float,
) -> list[Candidate]:
    candidates: list[Candidate] = []

    for index, value in enumerate(current.buttons):
        previous = baseline.buttons[index] if index < len(baseline.buttons) else False
        if value and not previous:
            candidates.append(Candidate(code=f"b{index}", score=1.0, kind="button"))

    for index, position in enumerate(current.hats):
        previous = baseline.hats[index] if index < len(baseline.hats) else (0, 0)
        mask = hat_to_mask(position)
        if position != previous and mask:
            candidates.append(Candidate(code=make_hat_code(index, mask), score=1.0, kind="hat"))

    for index, value in enumerate(current.axes):
        previous = baseline.axes[index] if index < len(baseline.axes) else 0.0
        delta = value - previous
        if abs(delta) >= threshold:
            half = None
            if expected_kind == "dpad":
                half = "+" if delta > 0 else "-"
            code = make_axis_code(index, half=half)
            candidates.append(
                Candidate(
                    code=code,
                    score=abs(delta),
                    kind="axis",
                    axis_value=value,
                    baseline_value=previous,
                )
            )

    kind_rank = {"button": 0, "hat": 1, "axis": 2}
    if expected_kind == "axis":
        kind_rank = {"axis": 0, "button": 1, "hat": 2}
    elif expected_kind == "trigger":
        kind_rank = {"axis": 0, "button": 1, "hat": 2}
    elif expected_kind == "dpad":
        kind_rank = {"hat": 0, "button": 1, "axis": 2}

    return sorted(candidates, key=lambda item: (kind_rank.get(item.kind, 9), -item.score))


def capture_one_binding(
    reader: PygameJoystickReader,
    joystick: Any,
    *,
    expected_kind: str,
    threshold: float,
    timeout_seconds: float,
) -> tuple[Candidate | None, RawState]:
    baseline = reader.snapshot(joystick)
    deadline = time.monotonic() + timeout_seconds
    best: Candidate | None = None

    while time.monotonic() < deadline:
        reader.pygame.event.pump()
        current = reader.snapshot(joystick)
        candidates = detect_candidates(
            baseline,
            current,
            expected_kind=expected_kind,
            threshold=threshold,
        )
        if candidates:
            best = candidates[0]
            return best, baseline
        time.sleep(0.02)
    return None, baseline


def choose_device(reader: PygameJoystickReader, requested_index: int | None) -> tuple[int, Any, DeviceInfo]:
    devices = reader.list_devices()
    if not devices:
        raise RuntimeError("没有检测到手柄。请先连接手柄，再重新运行命令。")

    if requested_index is None:
        print("检测到以下手柄：")
        for index, device in devices:
            print(
                f"  [{index}] {device.name}\n"
                f"      guid={device.guid}\n"
                f"      axes={device.axes} buttons={device.buttons} hats={device.hats}"
            )
        raw = input("请选择手柄编号，直接回车默认选 [0]：").strip()
        requested_index = int(raw) if raw else devices[0][0]

    valid = {index for index, _ in devices}
    if requested_index not in valid:
        raise RuntimeError(f"手柄编号 {requested_index} 不存在。")

    joystick = reader.open(requested_index)
    return requested_index, joystick, reader._device_info(joystick)


def run_mapping_wizard(
    *,
    output_dir: Path,
    device_index: int | None,
    deadzone: float,
    threshold: float,
    timeout_seconds: float = DEFAULT_CAPTURE_TIMEOUT_SECONDS,
    write_sdl: bool = False,
    platform: str = SDL_PLATFORM_DEFAULT,
) -> dict[str, Path]:
    reader = PygameJoystickReader()
    try:
        _, joystick, device = choose_device(reader, device_index)
        print(f"\n开始映射：{device.name}")
        print(f"GUID：{device.guid}")
        print(
            "\n操作方法：每一步先松开所有按键/摇杆，然后按回车开始监听；"
            "接着在限定时间内按下或推动提示的手柄控件。"
        )
        print("可输入：回车=开始采集或确认，r=重试，s=跳过当前项，q=取消整个映射。")

        controls: dict[str, str | None] = {}
        axis_directions: dict[str, int] = {}
        trigger_ranges: dict[str, dict[str, float]] = {}

        total = len(CONTROL_SPECS)
        for step, spec in enumerate(CONTROL_SPECS, start=1):
            while True:
                print("\n" + "=" * 64)
                print(f"第 {step}/{total} 项：{spec.title_zh}")
                print(f"开发字段：{spec.name}  ({spec.title})")
                print(f"现在要做：{action_hint(spec.kind)}")
                if spec.name == "guide":
                    print("提示：Windows/Xbox 手柄的 Guide/Home 键有时无法读取；读不到时输入 s 跳过。")
                command = input("按回车开始采集；输入 s 跳过；输入 q 取消：").strip().lower()
                if command == "q":
                    raise KeyboardInterrupt
                if command == "s":
                    controls[spec.name] = None
                    print(f"已跳过：{spec.name}")
                    break

                print(f"正在监听 {timeout_seconds:.0f} 秒，请现在操作手柄：{spec.title_zh} ...")
                candidate, baseline = capture_one_binding(
                    reader,
                    joystick,
                    expected_kind=spec.kind,
                    threshold=threshold,
                    timeout_seconds=timeout_seconds,
                )
                if candidate is None:
                    print("没有检测到输入。")
                    retry = input("按回车重试；输入 s 跳过；输入 q 取消：").strip().lower()
                    if retry == "q":
                        raise KeyboardInterrupt
                    if retry == "s":
                        controls[spec.name] = None
                        break
                    continue

                print(
                    f"检测到 {candidate.code}：{describe_input_code(candidate.code)} "
                    f"(变化幅度 {candidate.score:.3f})"
                )
                action = input("如果这是正确的，直接回车确认；输入 r 重试；输入 s 跳过；输入 q 取消：").strip().lower()
                if action in {"", "y", "yes"}:
                    controls[spec.name] = candidate.code
                    print(f"已记录：{spec.name} -> {candidate.code}")
                    if spec.kind == "axis" and candidate.kind == "axis" and candidate.axis_value is not None:
                        axis_directions[spec.name] = 1 if candidate.axis_value >= 0 else -1
                    if spec.kind == "trigger" and candidate.kind == "axis" and candidate.axis_value is not None:
                        trigger_ranges[spec.name] = {
                            "released": float(candidate.baseline_value or 0.0),
                            "pressed": float(candidate.axis_value),
                        }
                    break
                if action == "s":
                    controls[spec.name] = None
                    print(f"已跳过：{spec.name}")
                    break
                if action == "q":
                    raise KeyboardInterrupt
                if action in {"r", "n", "no"}:
                    continue

        mapping = create_mapping(
            device=device,
            controls=controls,
            deadzone=deadzone,
            capture_threshold=threshold,
            axis_directions=axis_directions,
            trigger_ranges=trigger_ranges,
        )
        paths = save_mapping_files(mapping, output_dir, write_sdl=write_sdl, platform=platform)
        print("\n映射完成，文件已保存：")
        print(f"  JSON 配置：{paths['json']}")
        print(f"  核对报告：{paths['markdown']}")
        if write_sdl:
            print(f"  SDL 映射：{paths['sdl']}")
        return paths
    finally:
        reader.close()
