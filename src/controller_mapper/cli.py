from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from .capture import MissingPygameError, PygameJoystickReader, run_mapping_wizard
from .constants import DEFAULT_CAPTURE_THRESHOLD, DEFAULT_CAPTURE_TIMEOUT_SECONDS, DEFAULT_DEADZONE, SDL_PLATFORM_DEFAULT
from .mapping_io import load_mapping
from .monitor import diff_raw_states, format_all_state
from .normalize import normalize_state
from .sdl import build_sdl_mapping


def _print_missing_pygame(exc: MissingPygameError) -> int:
    print(str(exc))
    return 2


def command_list(_: argparse.Namespace) -> int:
    try:
        reader = PygameJoystickReader()
    except MissingPygameError as exc:
        return _print_missing_pygame(exc)
    try:
        devices = reader.list_devices()
        if not devices:
            print("没有检测到手柄。请先连接手柄，再重新运行命令。")
            return 1
        print("检测到以下手柄：")
        for index, device in devices:
            print(
                f"[{index}] {device.name}\n"
                f"    guid={device.guid}\n"
                f"    instance_id={device.instance_id} axes={device.axes} "
                f"buttons={device.buttons} hats={device.hats}"
            )
        return 0
    finally:
        reader.close()


def command_monitor(args: argparse.Namespace) -> int:
    try:
        reader = PygameJoystickReader()
    except MissingPygameError as exc:
        return _print_missing_pygame(exc)

    try:
        devices = reader.list_devices()
        if not devices:
            print("没有检测到手柄。请先连接手柄，再重新运行命令。")
            return 1

        selected_index = args.device if args.device is not None else devices[0][0]
        available = {index for index, _ in devices}
        if selected_index not in available:
            print(f"手柄编号 {selected_index} 不存在。可用编号：{sorted(available)}")
            return 1

        joystick = reader.open(selected_index)
        device = next(device for index, device in devices if index == selected_index)
        print(f"正在监视手柄 [{selected_index}] {device.name}")
        print("随便按手柄按键、推动摇杆或按十字键，这里会显示原始输入编号。")
        print("按 Ctrl+C 退出。")

        previous = reader.snapshot(joystick)
        if args.all:
            for line in format_all_state(previous):
                print(line)

        while True:
            current = reader.snapshot(joystick)
            if args.all:
                print("-" * 48)
                for line in format_all_state(current):
                    print(line)
            else:
                for line in diff_raw_states(previous, current, axis_threshold=args.axis_threshold):
                    print(line)
            previous = current
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n已退出监视。")
        return 0
    finally:
        reader.close()


def command_map(args: argparse.Namespace) -> int:
    try:
        run_mapping_wizard(
            output_dir=Path(args.output_dir),
            device_index=args.device,
            deadzone=args.deadzone,
            threshold=args.threshold,
            timeout_seconds=args.timeout,
            write_sdl=args.write_sdl,
            platform=args.platform,
        )
        return 0
    except MissingPygameError as exc:
        return _print_missing_pygame(exc)
    except KeyboardInterrupt:
        print("\n已取消映射，没有写入半成品文件。")
        return 130
    except Exception as exc:
        print(f"映射失败：{exc}")
        return 1


def command_gui(args: argparse.Namespace) -> int:
    try:
        from .gui import run_gui

        return run_gui(
            device_index=args.device,
            mapping_file=Path(args.mapping) if args.mapping else None,
            output_dir=Path(args.output_dir),
        )
    except MissingPygameError as exc:
        return _print_missing_pygame(exc)
    except Exception as exc:
        print(f"GUI 启动失败：{exc}")
        return 1


def _state_from_joystick(reader: PygameJoystickReader, joystick: Any) -> dict[str, Any]:
    state = reader.snapshot(joystick)
    return {
        "buttons": list(state.buttons),
        "axes": list(state.axes),
        "hats": [list(item) for item in state.hats],
    }


def command_validate(args: argparse.Namespace) -> int:
    mapping = load_mapping(args.mapping)
    target_guid = str(mapping.get("device", {}).get("guid") or "")
    try:
        reader = PygameJoystickReader()
    except MissingPygameError as exc:
        return _print_missing_pygame(exc)

    try:
        devices = reader.list_devices()
        if not devices:
            print("没有检测到手柄。请先连接手柄，再重新运行命令。")
            return 1

        selected_index = args.device
        if selected_index is None and target_guid:
            for index, device in devices:
                if device.guid == target_guid:
                    selected_index = index
                    break
        if selected_index is None:
            selected_index = devices[0][0]

        joystick = reader.open(selected_index)
        print("正在验证映射。按 Ctrl+C 退出。")
        while True:
            raw = _state_from_joystick(reader, joystick)
            normalized = normalize_state(raw, mapping)
            if args.json:
                print(json.dumps(normalized, ensure_ascii=False, sort_keys=True))
            else:
                active = {
                    key: value
                    for key, value in normalized.items()
                    if value not in (False, 0.0, None)
                }
                print(active or "没有活跃的已映射控件")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n已退出验证。")
        return 0
    finally:
        reader.close()


def command_export_sdl(args: argparse.Namespace) -> int:
    try:
        mapping = load_mapping(args.mapping)
        text = build_sdl_mapping(mapping, platform=args.platform)
        if args.output:
            Path(args.output).write_text(text + "\n", encoding="utf-8")
            print(f"Wrote {args.output}")
        print(text)
        return 0
    except Exception as exc:
        print(f"SDL 导出失败：{exc}")
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="controller-mapper", description="手柄原始输入监视与 SDL 风格映射采集工具。")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="列出已连接手柄。")
    list_parser.set_defaults(func=command_list)

    monitor_parser = subparsers.add_parser("monitor", help="实时显示原始手柄输入变化。")
    monitor_parser.add_argument("--device", type=int, default=None, help="要监视的手柄编号，默认使用第一个。")
    monitor_parser.add_argument("--interval", type=float, default=0.05, help="监视刷新间隔，单位秒。")
    monitor_parser.add_argument("--axis-threshold", type=float, default=0.05, help="轴变化超过该阈值才打印。")
    monitor_parser.add_argument("--all", action="store_true", help="每次刷新都打印全部输入状态。")
    monitor_parser.set_defaults(func=command_monitor)

    map_parser = subparsers.add_parser("map", help="启动交互式映射向导。")
    map_parser.add_argument("--output-dir", default="mappings", help="映射文件输出目录。")
    map_parser.add_argument("--device", type=int, default=None, help="要映射的手柄编号。")
    map_parser.add_argument("--deadzone", type=float, default=DEFAULT_DEADZONE, help="摇杆死区。")
    map_parser.add_argument("--threshold", type=float, default=DEFAULT_CAPTURE_THRESHOLD, help="采集输入变化阈值。")
    map_parser.add_argument("--timeout", type=float, default=DEFAULT_CAPTURE_TIMEOUT_SECONDS, help="每项监听秒数。")
    map_parser.add_argument("--write-sdl", action="store_true", help="同时写出 .sdl.txt 文件。")
    map_parser.add_argument("--platform", default=SDL_PLATFORM_DEFAULT, help="SDL mapping string 的 platform 字段。")
    map_parser.set_defaults(func=command_map)

    gui_parser = subparsers.add_parser("gui", help="打开可视化手柄测试与校准界面。")
    gui_parser.add_argument("--device", type=int, default=None, help="要测试/校准的手柄编号，默认使用第一个。")
    gui_parser.add_argument("--mapping", default=None, help="可选：要加载的 JSON 映射文件。")
    gui_parser.add_argument("--output-dir", default="mappings", help="保存映射文件的输出目录。")
    gui_parser.set_defaults(func=command_gui)

    validate_parser = subparsers.add_parser("validate", help="用真实手柄验证已保存映射。")
    validate_parser.add_argument("--mapping", required=True, help="要验证的 JSON 映射文件。")
    validate_parser.add_argument("--device", type=int, default=None, help="要验证的手柄编号，默认按 GUID 匹配。")
    validate_parser.add_argument("--interval", type=float, default=0.25, help="刷新间隔，单位秒。")
    validate_parser.add_argument("--json", action="store_true", help="每次都输出完整 JSON 状态。")
    validate_parser.set_defaults(func=command_validate)

    export_parser = subparsers.add_parser("export-sdl", help="从 JSON 导出 SDL mapping string。")
    export_parser.add_argument("--mapping", required=True, help="JSON 映射文件。")
    export_parser.add_argument("--output", default=None, help="可选输出文件。")
    export_parser.add_argument("--platform", default=SDL_PLATFORM_DEFAULT, help="SDL mapping string 的 platform 字段。")
    export_parser.set_defaults(func=command_export_sdl)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))
