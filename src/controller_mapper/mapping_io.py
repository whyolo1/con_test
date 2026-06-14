from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .constants import CONTROL_SPECS, SDL_PLATFORM_DEFAULT
from .models import DeviceInfo, default_normalization, new_mapping
from .sdl import build_sdl_mapping


SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_.-]+")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sanitize_filename(value: str, *, fallback: str = "controller") -> str:
    cleaned = SAFE_NAME_RE.sub("_", value.strip())
    cleaned = cleaned.strip("._-")
    if not cleaned:
        cleaned = fallback
    return cleaned[:120]


def mapping_stem(device: DeviceInfo | dict[str, Any]) -> str:
    name = device.name if isinstance(device, DeviceInfo) else str(device.get("name") or "controller")
    guid = device.guid if isinstance(device, DeviceInfo) else str(device.get("guid") or "noguid")
    return sanitize_filename(f"{name}_{guid}")


def mapping_paths(output_dir: Path | str, device: DeviceInfo | dict[str, Any]) -> dict[str, Path]:
    root = Path(output_dir)
    stem = mapping_stem(device)
    return {
        "json": root / f"{stem}.json",
        "markdown": root / f"{stem}.md",
        "sdl": root / f"{stem}.sdl.txt",
    }


def create_mapping(
    *,
    device: DeviceInfo,
    controls: dict[str, str | None],
    deadzone: float,
    capture_threshold: float,
    axis_directions: dict[str, int] | None = None,
    trigger_ranges: dict[str, dict[str, float]] | None = None,
) -> dict[str, Any]:
    normalization = default_normalization(deadzone=deadzone, capture_threshold=capture_threshold)
    normalization["axis_directions"] = axis_directions or {}
    normalization["trigger_ranges"] = trigger_ranges or {}
    return new_mapping(
        created_at=utc_now_iso(),
        device=device,
        controls=controls,
        normalization=normalization,
    )


def load_mapping(path: Path | str) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_text_with_backup(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup = path.with_suffix(path.suffix + ".bak")
        if backup.exists():
            backup.unlink()
        path.replace(backup)
    path.write_text(text, encoding="utf-8")


def write_mapping_json(path: Path | str, mapping: dict[str, Any]) -> None:
    text = json.dumps(mapping, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    _write_text_with_backup(Path(path), text)


def render_markdown_report(mapping: dict[str, Any], *, platform: str = SDL_PLATFORM_DEFAULT) -> str:
    device = mapping.get("device", {})
    controls = mapping.get("controls", {})
    normalization = mapping.get("normalization", {})

    lines = [
        "# Controller Mapping Report",
        "",
        f"- Name: `{device.get('name', '')}`",
        f"- GUID: `{device.get('guid', '')}`",
        f"- Instance ID: `{device.get('instance_id', '')}`",
        f"- Axes: `{device.get('axes', '')}`",
        f"- Buttons: `{device.get('buttons', '')}`",
        f"- Hats: `{device.get('hats', '')}`",
        f"- Created: `{mapping.get('created_at', '')}`",
        f"- Deadzone: `{normalization.get('deadzone', '')}`",
        f"- Capture threshold: `{normalization.get('capture_threshold', '')}`",
        "",
        "## Controls",
        "",
        "| SDL name | Description | 中文说明 | Physical input | Status |",
        "| --- | --- | --- | --- | --- |",
    ]

    for spec in CONTROL_SPECS:
        code = controls.get(spec.name)
        status = "mapped" if code else "skipped"
        display_code = f"`{code}`" if code else ""
        lines.append(f"| `{spec.name}` | {spec.title} | {spec.title_zh} | {display_code} | {status} |")

    try:
        sdl_mapping = build_sdl_mapping(mapping, platform=platform)
    except ValueError as exc:
        sdl_mapping = f"Unavailable: {exc}"

    lines.extend(
        [
            "",
            "## SDL Mapping String",
            "",
            "```text",
            sdl_mapping,
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def save_mapping_files(
    mapping: dict[str, Any],
    output_dir: Path | str,
    *,
    write_sdl: bool = False,
    platform: str = SDL_PLATFORM_DEFAULT,
) -> dict[str, Path]:
    paths = mapping_paths(output_dir, mapping.get("device", {}))
    write_mapping_json(paths["json"], mapping)
    _write_text_with_backup(paths["markdown"], render_markdown_report(mapping, platform=platform))
    if write_sdl:
        _write_text_with_backup(paths["sdl"], build_sdl_mapping(mapping, platform=platform) + "\n")
    return paths
