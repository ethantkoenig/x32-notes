from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EQBand:
    type: str    # PEQ, VEQ, HShv, LShv, HCut, LCut
    freq: float  # Hz
    gain: float  # dB
    q: float


@dataclass
class EQ:
    enabled: bool
    bands: list[Optional[EQBand]] = field(default_factory=list)
    low_cut_enabled: bool = False
    low_cut_freq: float = 0.0


@dataclass
class Compressor:
    enabled: bool
    mode: str      # COMP, LIMIT, EXP
    det: str       # PEAK, RMS
    env: str       # LIN, LOG
    threshold: float   # dB
    ratio: float
    knee: int
    makeup: float  # dB
    attack: float  # ms
    hold: float    # ms
    release: float # ms


@dataclass
class Gate:
    enabled: bool
    type: str      # GATE, EXP2, EXP4, DUCK
    threshold: float   # dB
    range: float   # dB
    attack: float  # ms
    hold: float    # ms
    release: float # ms


@dataclass
class Channel:
    index: int
    name: str = ""
    color: str = "WHi"
    icon: int = 1
    on: bool = True          # False = muted
    fader_db: float = float("-inf")
    eq: Optional[EQ] = None
    compressor: Optional[Compressor] = None
    gate: Optional[Gate] = None
    raw: dict[str, list[str]] = field(default_factory=dict)
