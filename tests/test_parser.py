import math
from pathlib import Path

import pytest

from server.parser.scene import parse_db, parse_freq, parse_scene

EXAMPLE_CHN = Path(__file__).parent.parent / "examples" / "channel.chn"

EXAMPLE_SCN = Path(__file__).parent.parent / "examples" / "scene.scn"


# ── parse_freq ──────────────────────────────────────────────────────────────

def test_parse_freq_plain():
    assert parse_freq("164.4") == pytest.approx(164.4)

def test_parse_freq_k_notation():
    assert parse_freq("1k39") == pytest.approx(1390.0)
    assert parse_freq("10k02") == pytest.approx(10020.0)
    assert parse_freq("2k69") == pytest.approx(2690.0)
    assert parse_freq("1k00") == pytest.approx(1000.0)

def test_parse_freq_sub_khz():
    assert parse_freq("990.9") == pytest.approx(990.9)


# ── parse_db ─────────────────────────────────────────────────────────────────

def test_parse_db_neg_inf():
    result = parse_db("-oo")
    assert math.isinf(result) and result < 0

def test_parse_db_positive():
    assert parse_db("+2.1") == pytest.approx(2.1)

def test_parse_db_negative():
    assert parse_db("-3.8") == pytest.approx(-3.8)


# ── scene-level ───────────────────────────────────────────────────────────────

def test_scene_has_32_channels():
    channels = parse_scene(EXAMPLE_SCN)
    assert set(range(1, 33)).issubset(channels.keys())

def test_scene_ignores_non_channel_paths():
    channels = parse_scene(EXAMPLE_SCN)
    # auxin paths should not bleed in as channel entries
    assert all(1 <= k <= 32 for k in channels)


# ── channel 1 (Diazno) ───────────────────────────────────────────────────────

def test_ch01_config():
    ch = parse_scene(EXAMPLE_SCN)[1]
    assert ch.name == "Diazno"
    assert ch.color == "CY"
    assert ch.icon == 1

def test_ch01_eq_enabled():
    ch = parse_scene(EXAMPLE_SCN)[1]
    assert ch.eq is not None
    assert ch.eq.enabled is True

def test_ch01_eq_band1():
    band = parse_scene(EXAMPLE_SCN)[1].eq.bands[0]
    assert band.type == "PEQ"
    assert band.freq == pytest.approx(164.4)
    assert band.gain == pytest.approx(-3.75)
    assert band.q == pytest.approx(1.8)

def test_ch01_eq_band2():
    band = parse_scene(EXAMPLE_SCN)[1].eq.bands[1]
    assert band.freq == pytest.approx(463.5)
    assert band.gain == pytest.approx(-6.50)

def test_ch01_gate():
    gate = parse_scene(EXAMPLE_SCN)[1].gate
    assert gate is not None
    assert gate.enabled is True
    assert gate.type == "EXP4"
    assert gate.threshold == pytest.approx(-46.5)
    assert gate.range == pytest.approx(27.0)
    assert gate.attack == pytest.approx(20.0)
    assert gate.hold == pytest.approx(100.0)
    assert gate.release == pytest.approx(576.0)

def test_ch01_compressor():
    comp = parse_scene(EXAMPLE_SCN)[1].compressor
    assert comp is not None
    assert comp.enabled is True
    assert comp.mode == "COMP"
    assert comp.det == "PEAK"
    assert comp.env == "LIN"
    assert comp.threshold == pytest.approx(-26.0)
    assert comp.ratio == pytest.approx(3.0)
    assert comp.knee == 2
    assert comp.makeup == pytest.approx(8.0)

def test_ch01_fader_and_on():
    ch = parse_scene(EXAMPLE_SCN)[1]
    assert ch.on is True
    assert ch.fader_db == pytest.approx(2.1)


# ── k-notation in EQ ─────────────────────────────────────────────────────────

def test_k_freq_in_eq():
    # /ch/03/eq/2 PEQ 1k17 -4.00 3.5
    band = parse_scene(EXAMPLE_SCN)[3].eq.bands[1]
    assert band.freq == pytest.approx(1170.0)

def test_high_shelf_eq():
    # /ch/02/eq/4 HShv 10k02 +0.00 2.0
    band = parse_scene(EXAMPLE_SCN)[2].eq.bands[3]
    assert band.type == "HShv"
    assert band.freq == pytest.approx(10020.0)

def test_high_cut_eq():
    # /ch/03/eq/4 HCut 11k91 +0.00 2.0
    band = parse_scene(EXAMPLE_SCN)[3].eq.bands[3]
    assert band.type == "HCut"
    assert band.freq == pytest.approx(11910.0)


# ── mute / fader edge cases ───────────────────────────────────────────────────

def test_muted_channel():
    # /ch/04/mix OFF   -oo ON +0 OFF   -oo
    ch = parse_scene(EXAMPLE_SCN)[4]
    assert ch.on is False

def test_neg_inf_fader():
    ch = parse_scene(EXAMPLE_SCN)[4]
    assert math.isinf(ch.fader_db) and ch.fader_db < 0

def test_channel_with_empty_name():
    ch = parse_scene(EXAMPLE_SCN)[3]
    assert ch.name == ""


# ── eq disabled ──────────────────────────────────────────────────────────────

def test_eq_disabled():
    # /ch/13/eq OFF
    ch = parse_scene(EXAMPLE_SCN)[13]
    assert ch.eq is not None
    assert ch.eq.enabled is False
    assert len(ch.eq.bands) == 4  # bands still parsed even when eq is off


# ── preamp low-cut ───────────────────────────────────────────────────────────

def test_ch01_low_cut_off():
    # /ch/01/preamp +0.0 OFF OFF 24  79
    ch = parse_scene(EXAMPLE_SCN)[1]
    assert ch.eq.low_cut_enabled is False
    assert ch.eq.low_cut_freq == pytest.approx(79.0)

def test_ch03_low_cut_on():
    # /ch/03/preamp +0.0 OFF ON 24 132
    ch = parse_scene(EXAMPLE_SCN)[3]
    assert ch.eq.low_cut_enabled is True
    assert ch.eq.low_cut_freq == pytest.approx(132.0)


# ── .chn file parsing ────────────────────────────────────────────────────────

def test_chn_has_one_channel():
    channels = parse_scene(EXAMPLE_CHN)
    assert list(channels.keys()) == [1]

def test_chn_config():
    ch = parse_scene(EXAMPLE_CHN)[1]
    assert ch.name == "Dave"
    assert ch.color == "YE"

def test_chn_eq():
    ch = parse_scene(EXAMPLE_CHN)[1]
    assert ch.eq is not None
    assert ch.eq.enabled is True
    assert ch.eq.low_cut_enabled is True
    assert ch.eq.low_cut_freq == pytest.approx(121.0)
    assert ch.eq.bands[0].freq == pytest.approx(376.7)
    assert ch.eq.bands[0].gain == pytest.approx(-14.7)

def test_chn_compressor():
    comp = parse_scene(EXAMPLE_CHN)[1].compressor
    assert comp is not None
    assert comp.enabled is True
    assert comp.threshold == pytest.approx(-26.0)
    assert comp.ratio == pytest.approx(3.0)
    assert comp.makeup == pytest.approx(7.0)

def test_chn_gate():
    gate = parse_scene(EXAMPLE_CHN)[1].gate
    assert gate is not None
    assert gate.enabled is False
    assert gate.threshold == pytest.approx(-33.5)
    assert gate.range == pytest.approx(55.0)

def test_chn_fader():
    ch = parse_scene(EXAMPLE_CHN)[1]
    assert ch.fader_db == pytest.approx(-3.6)


# ── raw storage ───────────────────────────────────────────────────────────────

def test_raw_config_stored():
    ch = parse_scene(EXAMPLE_SCN)[1]
    assert ch.raw.get("config") == ["Diazno", "1", "CY", "1"]

def test_raw_unrecognized_paths_stored():
    ch = parse_scene(EXAMPLE_SCN)[1]
    assert "delay" in ch.raw
    assert "preamp" in ch.raw
