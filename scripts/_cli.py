"""Shared CLI helpers: console encoding, stable output writing, tiny formatting.

Kept separate so every script behaves the same on a Chinese Windows console
(cp936), a POSIX terminal, and a Jupyter kernel -- without each script carrying
its own encoding dance.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path


def setup_console() -> None:
    """Make printing UTF-8 safe instead of dying on a cp936 console."""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def ensure_dir(path: str | Path | None) -> Path | None:
    if path is None:
        return None
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def write_json(path: str | Path, payload) -> Path:
    p = ensure_dir(path)
    p.write_text(json.dumps(_json_safe(payload), indent=2, ensure_ascii=False), encoding="utf-8")
    return p


def write_text(path: str | Path, text: str) -> Path:
    p = ensure_dir(path)
    p.write_text(text, encoding="utf-8")
    return p


def _json_safe(obj):
    import numpy as np
    if isinstance(obj, dict):
        return {str(k): _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        v = float(obj)
        return None if (math.isnan(v) or math.isinf(v)) else v
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, float):
        return None if (math.isnan(obj) or math.isinf(obj)) else obj
    if isinstance(obj, np.ndarray):
        return [_json_safe(v) for v in obj.tolist()]
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    return obj


def md_table(headers: list[str], rows: list[list[str]], aligns: list[str] | None = None) -> str:
    """Minimal markdown table builder (keeps report code free of f-string soup)."""
    aligns = aligns or ["---"] * len(headers)
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join(aligns) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


def pct(x: float, digits: int = 1) -> str:
    if x != x:
        return "n/a"
    return f"{x:.{digits}f}%"


def p_cell(p: float) -> str:
    """APA cell value for a p column: .043, <.001 -- no leading zero, no '=' sign."""
    if p is None or p != p:
        return "n/a"
    if p < 0.001:
        return "<.001"
    return f"{p:.3f}".lstrip("0") if p < 1 else f"{p:.3f}"


def num(x: float, digits: int = 2, dash: str = "—") -> str:
    if x is None or x != x:
        return dash
    return f"{x:.{digits}f}"