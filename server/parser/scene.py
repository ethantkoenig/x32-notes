from __future__ import annotations

import logging
import re
import shlex
from pathlib import Path

from .parameters import Channel, Compressor, EQ, EQBand, Gate

logger = logging.getLogger(__name__)

_CH_RE  = re.compile(r"^/ch/(\d{2})/(.+)$")
_CHN_RE = re.compile(r"^/(.+)$")


def parse_freq(s: str) -> float:
    """Parse X32 frequency notation: '1k39' → 1390.0, '164.4' → 164.4."""
    if "k" in s:
        left, right = s.split("k", 1)
        return float(f"{left}.{right}") * 1000
    return float(s)


def parse_db(s: str) -> float:
    """Parse dB value: '-oo' → -inf."""
    return float("-inf") if s == "-oo" else float(s)


def parse_scene(path: Path) -> dict[int, Channel]:
    """Parse a .scn (or .snp / .chn) file. Returns channel index → Channel."""
    channels: dict[int, Channel] = {}
    is_chn = path.suffix == ".chn"
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        logger.error("Cannot read %s: %s", path, exc)
        return channels

    for lineno, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            _process_line(line, channels, is_chn)
        except Exception as exc:
            logger.warning(
                "Skipping line %d in %s: %s — %r", lineno, path.name, exc, line
            )

    return channels


def _process_line(line: str, channels: dict[int, Channel], is_chn: bool = False) -> None:
    m = _CH_RE.match(line)
    if m:
        ch_idx = int(m.group(1))
        remainder = m.group(2)
    elif is_chn:
        m2 = _CHN_RE.match(line)
        if not m2:
            return
        ch_idx = 1
        remainder = m2.group(1)
    else:
        return

    tokens = shlex.split(remainder)
    if not tokens:
        return

    subpath, values = tokens[0], tokens[1:]
    ch = channels.setdefault(ch_idx, Channel(index=ch_idx))
    ch.raw[subpath] = values

    match subpath:
        case "config":
            _config(ch, values)
        case "eq":
            _eq_enable(ch, values)
        case s if s.startswith("eq/"):
            _eq_band(ch, s, values)
        case "dyn":
            _dyn(ch, values)
        case "gate":
            _gate(ch, values)
        case "preamp":
            _preamp(ch, values)
        case "mix":
            _mix(ch, values)


def _config(ch: Channel, v: list[str]) -> None:
    if len(v) > 0:
        ch.name = v[0]
    if len(v) > 1:
        ch.icon = int(v[1])
    if len(v) > 2:
        ch.color = v[2]


def _eq_enable(ch: Channel, v: list[str]) -> None:
    enabled = v[0].upper() == "ON" if v else True
    if ch.eq is None:
        ch.eq = EQ(enabled=enabled)
    else:
        ch.eq.enabled = enabled


def _eq_band(ch: Channel, subpath: str, v: list[str]) -> None:
    if len(v) < 4:
        return
    band_num = int(subpath.split("/")[1])
    band = EQBand(type=v[0], freq=parse_freq(v[1]), gain=float(v[2]), q=float(v[3]))
    if ch.eq is None:
        ch.eq = EQ(enabled=True)
    while len(ch.eq.bands) < band_num:
        ch.eq.bands.append(None)
    ch.eq.bands[band_num - 1] = band


def _dyn(ch: Channel, v: list[str]) -> None:
    if len(v) < 11:
        return
    ch.compressor = Compressor(
        enabled=v[0].upper() == "ON",
        mode=v[1],
        det=v[2],
        env=v[3],
        threshold=float(v[4]),
        ratio=float(v[5]),
        knee=int(v[6]),
        makeup=float(v[7]),
        attack=float(v[8]),
        hold=float(v[9]),
        release=float(v[10]),
    )


def _gate(ch: Channel, v: list[str]) -> None:
    if len(v) < 7:
        return
    ch.gate = Gate(
        enabled=v[0].upper() == "ON",
        type=v[1],
        threshold=float(v[2]),
        range=float(v[3]),
        attack=float(v[4]),
        hold=float(v[5]),
        release=float(v[6]),
    )


def _preamp(ch: Channel, v: list[str]) -> None:
    if len(v) < 5:
        return
    if ch.eq is None:
        ch.eq = EQ(enabled=True)
    ch.eq.low_cut_enabled = v[2].upper() == "ON"
    ch.eq.low_cut_freq = parse_freq(v[4])


def _mix(ch: Channel, v: list[str]) -> None:
    if len(v) > 0:
        ch.on = v[0].upper() == "ON"
    if len(v) > 1:
        ch.fader_db = parse_db(v[1])
