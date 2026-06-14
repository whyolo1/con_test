"""SDL-style game controller mapping tools."""

from .mapping_io import load_mapping
from .normalize import normalize_state
from .sdl import build_sdl_mapping

__all__ = ["build_sdl_mapping", "load_mapping", "normalize_state"]

__version__ = "0.1.0"
