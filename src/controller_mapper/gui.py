from __future__ import annotations

from pathlib import Path
from typing import Any

from .capture import MissingPygameError, PygameJoystickReader, detect_candidates
from .constants import CONTROL_BY_NAME, DEFAULT_CAPTURE_THRESHOLD, SDL_PLATFORM_DEFAULT
from .gui_model import (
    VISUAL_CONTROLS,
    GuiState,
    HitBox,
    active_controls_for_state,
    control_at,
    load_mapping_for_gui,
    stick_values_for_display,
)
from .mapping_io import save_mapping_files
from .monitor import diff_raw_states
from .models import DeviceInfo, RawState


WINDOW_WIDTH = 1040
WINDOW_HEIGHT = 680
SAVE_BUTTON = HitBox(870, 88, 112, 38)
QUIT_BUTTON = HitBox(870, 132, 112, 38)


COLORS = {
    "background": (28, 31, 36),
    "panel": (39, 44, 51),
    "body": (64, 70, 78),
    "body_edge": (92, 101, 112),
    "button": (90, 99, 110),
    "button_edge": (148, 158, 170),
    "active": (70, 210, 132),
    "active_edge": (170, 255, 205),
    "waiting": (255, 200, 74),
    "text": (238, 241, 245),
    "muted": (170, 178, 188),
    "danger": (238, 112, 112),
    "save": (68, 139, 255),
}


def _font(pygame: Any, size: int, *, bold: bool = False):
    # List of common Chinese fonts across Windows, macOS, and Linux (e.g. Ubuntu)
    font_names = [
        "microsoft yahei",
        "microsoftyahei",
        "pingfang sc",
        "pingfangsc",
        "noto sans cjk sc",
        "notosanscjksc",
        "noto sans cjk",
        "notosanscjk",
        "wenquanyi micro hei",
        "wenquanyimicrohei",
        "wqy-microhei",
        "wqy-zenhei",
        "droid sans fallback",
        "droidsansfallback",
        "sans-serif",
        "sans",
        "arial",
    ]
    for name in font_names:
        path = pygame.font.match_font(name, bold=bold)
        if path:
            try:
                return pygame.font.Font(path, size)
            except Exception:
                continue
    return pygame.font.SysFont(None, size, bold=bold)



def _draw_text(
    surface: Any,
    font: Any,
    text: str,
    pos: tuple[int, int],
    color: tuple[int, int, int] = COLORS["text"],
) -> None:
    surface.blit(font.render(text, True, color), pos)


def _draw_button(
    pygame: Any,
    surface: Any,
    box: HitBox,
    label: str,
    *,
    fill: tuple[int, int, int],
    edge: tuple[int, int, int],
    text_color: tuple[int, int, int] = COLORS["text"],
    radius: int = 8,
) -> None:
    rect = pygame.Rect(box.x, box.y, box.width, box.height)
    pygame.draw.rect(surface, fill, rect, border_radius=radius)
    pygame.draw.rect(surface, edge, rect, width=2, border_radius=radius)
    font = _font(pygame, 16, bold=True)
    text = font.render(label, True, text_color)
    surface.blit(text, text.get_rect(center=rect.center))


def _shift_box(box: HitBox, *, dx: int = 0, dy: int = 0) -> HitBox:
    return HitBox(box.x + dx, box.y + dy, box.width, box.height)


def _darken(color: tuple[int, int, int], amount: int = 32) -> tuple[int, int, int]:
    return tuple(max(0, channel - amount) for channel in color)


def _draw_header_button(
    pygame: Any,
    surface: Any,
    box: HitBox,
    label: str,
    *,
    fill: tuple[int, int, int],
    edge: tuple[int, int, int],
    pressed: bool,
) -> None:
    draw_box = _shift_box(box, dy=2) if pressed else box
    _draw_button(
        pygame,
        surface,
        draw_box,
        label,
        fill=_darken(fill, 42) if pressed else fill,
        edge=_darken(edge, 26) if pressed else edge,
        text_color=(210, 216, 224) if pressed else COLORS["text"],
    )


def _draw_circle_control(
    pygame: Any,
    surface: Any,
    control_box: HitBox,
    label: str,
    *,
    active: bool,
    waiting: bool,
) -> None:
    center = control_box.center
    radius = min(control_box.width, control_box.height) // 2
    fill = COLORS["waiting"] if waiting else COLORS["active"] if active else COLORS["button"]
    edge = COLORS["active_edge"] if active or waiting else COLORS["button_edge"]
    pygame.draw.circle(surface, fill, center, radius)
    pygame.draw.circle(surface, edge, center, radius, width=3)
    font = _font(pygame, 18, bold=True)
    text = font.render(label, True, (20, 24, 28) if active or waiting else COLORS["text"])
    surface.blit(text, text.get_rect(center=center))


def _draw_rect_control(
    pygame: Any,
    surface: Any,
    control_box: HitBox,
    label: str,
    *,
    active: bool,
    waiting: bool,
) -> None:
    fill = COLORS["waiting"] if waiting else COLORS["active"] if active else COLORS["button"]
    edge = COLORS["active_edge"] if active or waiting else COLORS["button_edge"]
    _draw_button(
        pygame,
        surface,
        control_box,
        label,
        fill=fill,
        edge=edge,
        text_color=(20, 24, 28) if active or waiting else COLORS["text"],
    )


def _draw_axis_control(
    pygame: Any,
    surface: Any,
    box: HitBox,
    *,
    label: str,
    x_value: float,
    y_value: float,
    active: bool,
    waiting: bool = False,
) -> None:
    center = box.center
    radius = min(box.width, box.height) // 2
    pygame.draw.circle(surface, (50, 55, 63), center, radius + 12)
    pygame.draw.circle(surface, COLORS["button_edge"], center, radius + 12, width=2)
    knob = (
        int(center[0] + max(-1.0, min(1.0, x_value)) * 22),
        int(center[1] + max(-1.0, min(1.0, y_value)) * 22),
    )
    fill = COLORS["waiting"] if waiting else COLORS["active"] if active else COLORS["button"]
    pygame.draw.circle(surface, fill, knob, radius - 8)
    pygame.draw.circle(surface, COLORS["active_edge"] if active or waiting else COLORS["button_edge"], knob, radius - 8, width=3)
    font = _font(pygame, 16, bold=True)
    text = font.render(label, True, (20, 24, 28) if active or waiting else COLORS["text"])
    surface.blit(text, text.get_rect(center=knob))


def _normalized_float(active_controls: dict[str, bool | float], name: str) -> float:
    value = active_controls.get(name, 0.0)
    if isinstance(value, bool):
        return 0.0
    return float(value)


def _draw_controller(
    pygame: Any,
    surface: Any,
    state: GuiState,
    raw_state: RawState,
) -> None:
    active_controls = active_controls_for_state(state.mapping, raw_state)
    stick_values = stick_values_for_display(state.mapping, raw_state)
    body_rect = pygame.Rect(190, 205, 660, 340)
    pygame.draw.rect(surface, COLORS["body"], body_rect, border_radius=120)
    pygame.draw.rect(surface, COLORS["body_edge"], body_rect, width=3, border_radius=120)
    pygame.draw.circle(surface, COLORS["body"], (310, 380), 145)
    pygame.draw.circle(surface, COLORS["body"], (730, 380), 145)

    _draw_axis_control(
        pygame,
        surface,
        HitBox(250, 430, 96, 96),
        label="LS",
        x_value=stick_values["leftx"],
        y_value=stick_values["lefty"],
        active=bool(
            abs(stick_values["leftx"]) >= 0.2
            or abs(stick_values["lefty"]) >= 0.2
            or active_controls.get("leftstick")
        ),
        waiting=state.waiting_for == "leftstick",
    )
    _draw_axis_control(
        pygame,
        surface,
        HitBox(610, 430, 96, 96),
        label="RS",
        x_value=stick_values["rightx"],
        y_value=stick_values["righty"],
        active=bool(
            abs(stick_values["rightx"]) >= 0.2
            or abs(stick_values["righty"]) >= 0.2
            or active_controls.get("rightstick")
        ),
        waiting=state.waiting_for == "rightstick",
    )

    for control in VISUAL_CONTROLS:
        if control.name in {"leftstick", "rightstick"}:
            continue
        active = bool(active_controls.get(control.name))
        waiting = state.waiting_for == control.name
        if control.shape == "circle":
            _draw_circle_control(pygame, surface, control.box, control.label, active=active, waiting=waiting)
        else:
            _draw_rect_control(pygame, surface, control.box, control.label, active=active, waiting=waiting)

    small = _font(pygame, 14)
    controls = state.mapping.get("controls", {})
    for control in VISUAL_CONTROLS:
        if control.name in {"leftstick", "rightstick"}:
            continue
        code = controls.get(control.name)
        if code:
            x, y = control.box.center
            _draw_text(surface, small, str(code), (x - 18, control.box.y + control.box.height + 4), COLORS["muted"])


def _draw_header(
    pygame: Any,
    surface: Any,
    *,
    device_index: int,
    device: DeviceInfo,
    state: GuiState,
    pressed_button: str | None = None,
) -> None:
    title = _font(pygame, 25, bold=True)
    medium = _font(pygame, 18)
    small = _font(pygame, 15)

    pygame.draw.rect(surface, COLORS["panel"], pygame.Rect(24, 24, 992, 158), border_radius=12)
    _draw_text(surface, title, "手柄测试与校准", (48, 44))
    _draw_text(surface, medium, f"[{device_index}] {device.name}", (48, 84))
    _draw_text(surface, small, f"GUID: {device.guid}", (48, 114), COLORS["muted"])
    _draw_text(surface, small, state.mapping_status(), (48, 142), COLORS["muted"])

    _draw_header_button(
        pygame,
        surface,
        SAVE_BUTTON,
        "保存 S",
        fill=COLORS["save"],
        edge=(145, 190, 255),
        pressed=pressed_button == "save",
    )
    _draw_header_button(
        pygame,
        surface,
        QUIT_BUTTON,
        "退出 Esc",
        fill=(86, 92, 104),
        edge=COLORS["button_edge"],
        pressed=pressed_button == "quit",
    )


def _draw_footer(pygame: Any, surface: Any, state: GuiState) -> None:
    pygame.draw.rect(surface, COLORS["panel"], pygame.Rect(24, 574, 992, 82), border_radius=12)
    medium = _font(pygame, 18)
    small = _font(pygame, 15)
    status_color = COLORS["waiting"] if state.waiting_for else COLORS["text"]
    _draw_text(surface, medium, state.status, (48, 594), status_color)
    _draw_text(surface, small, state.last_raw, (48, 626), COLORS["muted"])
    _draw_text(surface, small, "操作：按手柄查看高亮；点击按钮后按真实物理输入重绑；S 保存；Esc 取消/退出。", (470, 626), COLORS["muted"])


def _save_gui_mapping(state: GuiState, output_dir: Path) -> None:
    paths = save_mapping_files(state.mapping, output_dir, write_sdl=True, platform=SDL_PLATFORM_DEFAULT)
    state.mapping_path = paths["json"]
    state.saved_path = paths["json"]
    state.dirty = False
    state.status = f"已保存：{paths['json']}"


def _select_device(reader: PygameJoystickReader, requested_index: int | None) -> tuple[int, Any, DeviceInfo]:
    devices = reader.list_devices()
    if not devices:
        raise RuntimeError("没有检测到手柄。请先连接手柄，再重新运行 GUI。")
    selected = requested_index if requested_index is not None else devices[0][0]
    available = {index for index, _ in devices}
    if selected not in available:
        raise RuntimeError(f"手柄编号 {selected} 不存在。可用编号：{sorted(available)}")
    joystick = reader.open(selected)
    device = next(device for index, device in devices if index == selected)
    return selected, joystick, device


def run_gui(
    *,
    device_index: int | None,
    mapping_file: Path | None,
    output_dir: Path,
) -> int:
    reader = PygameJoystickReader()
    pygame = reader.pygame
    try:
        selected_index, joystick, device = _select_device(reader, device_index)
        mapping, resolved_mapping_path = load_mapping_for_gui(
            device,
            mapping_file=mapping_file,
            output_dir=output_dir,
        )
        state = GuiState.from_device(device, mapping=mapping, mapping_path=resolved_mapping_path)

        pygame.display.set_caption("Controller Mapper GUI")
        screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        clock = pygame.time.Clock()
        baseline_for_binding = reader.snapshot(joystick)
        previous = baseline_for_binding
        pressed_button: str | None = None
        previous_mouse_down = False
        previous_escape_down = False
        previous_save_down = False

        running = True
        while running:
            pygame.event.pump()
            if pygame.event.peek(pygame.QUIT):
                running = False

            keys = pygame.key.get_pressed()
            escape_down = bool(keys[pygame.K_ESCAPE])
            save_down = bool(keys[pygame.K_s])
            if escape_down and not previous_escape_down:
                if state.waiting_for:
                    state.cancel_rebind()
                else:
                    running = False
            if save_down and not previous_save_down:
                _save_gui_mapping(state, output_dir)
            previous_escape_down = escape_down
            previous_save_down = save_down

            mouse_down = bool(pygame.mouse.get_pressed()[0])
            point = tuple(pygame.mouse.get_pos())
            if mouse_down and not previous_mouse_down:
                if SAVE_BUTTON.contains(point):
                    pressed_button = "save"
                elif QUIT_BUTTON.contains(point):
                    pressed_button = "quit"
                else:
                    selected_control = control_at(point)
                    if selected_control:
                        state.begin_rebind(selected_control)
                        baseline_for_binding = reader.snapshot(joystick)
            elif not mouse_down and previous_mouse_down:
                if pressed_button == "save" and SAVE_BUTTON.contains(point):
                    _save_gui_mapping(state, output_dir)
                elif pressed_button == "quit" and QUIT_BUTTON.contains(point):
                    running = False
                pressed_button = None
            elif mouse_down and pressed_button is not None:
                if pressed_button == "save" and not SAVE_BUTTON.contains(point):
                    pressed_button = None
                elif pressed_button == "quit" and not QUIT_BUTTON.contains(point):
                    pressed_button = None
            previous_mouse_down = mouse_down

            current = reader.snapshot(joystick)
            diffs = diff_raw_states(previous, current, axis_threshold=0.05)
            if diffs:
                state.last_raw = "raw: " + " | ".join(diffs[-3:])

            if state.waiting_for:
                spec = CONTROL_BY_NAME[state.waiting_for]
                candidates = detect_candidates(
                    baseline_for_binding,
                    current,
                    expected_kind=spec.kind,
                    threshold=DEFAULT_CAPTURE_THRESHOLD,
                )
                if candidates:
                    candidate = candidates[0]
                    state.last_raw = f"raw: {candidate.code}"
                    state.apply_candidate(candidate)
                    baseline_for_binding = current

            screen.fill(COLORS["background"])
            _draw_header(
                pygame,
                screen,
                device_index=selected_index,
                device=device,
                state=state,
                pressed_button=pressed_button,
            )
            _draw_controller(pygame, screen, state, current)
            _draw_footer(pygame, screen, state)
            pygame.display.flip()
            previous = current
            clock.tick(60)

        return 0
    finally:
        reader.close()
