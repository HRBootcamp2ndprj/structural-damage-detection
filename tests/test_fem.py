import sys
import time
from pathlib import Path

import numpy as np

from src.features.schema import MODES
from src.fem.api import ModalParams, run_modal
from src.fem.model import load_config, solve
from src.fem.modes import identify

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from calibrate_fem import write_values  # noqa: E402


def test_baseline_returns_four_modes_near_target():
    cfg = load_config()
    target = np.array([cfg["calibration"]["target_hz"][m] for m in MODES])
    f0 = run_modal(ModalParams(), None).freqs_hz
    assert f0.shape == (len(MODES),)
    assert np.all(np.abs(f0 / target - 1) < 0.05), f0


def test_run_modal_is_fast_enough_for_sim_generation():
    run_modal(ModalParams(), None)
    t = time.perf_counter()
    for _ in range(10):
        run_modal(ModalParams(env_stiffness=0.001), None)
    assert (time.perf_counter() - t) / 10 < 1.0


def test_env_stiffness_scales_frequencies_by_sqrt():
    f0 = run_modal(ModalParams(), None).freqs_hz
    f1 = run_modal(ModalParams(env_stiffness=0.02), None).freqs_hz
    ratio = f1 / f0 - 1
    assert np.all(ratio > 0)
    # 연직 모드는 E만으로 정해지므로 √1.02 − 1 ≈ 0.995%를 따른다 (횡은 E와 무관한 단부 스프링이 섞임)
    assert abs(ratio[MODES.index("vertical1")] - (np.sqrt(1.02) - 1)) < 1e-3


def test_softening_main_span_lowers_vertical1():
    cfg = load_config()
    freqs, part, geo = solve(cfg)
    k = np.where((geo.deck_x_mid > 20) & (geo.deck_x_mid < 38), 0.7, 1.0)
    damaged = identify(*solve(cfg, deck_stiffness=k)[:2])
    healthy = identify(freqs, part)
    assert damaged[MODES.index("vertical1")] < healthy[MODES.index("vertical1")] * 0.97


def test_identify_uses_mode_shape_not_order():
    # 손상으로 비틀림(9.5)이 연직2(10.0)보다 낮아진 경우. 6.0은 교각 국부 모드 (거더 몫 0.1)
    freqs = np.array([3.9, 5.0, 6.0, 9.5, 10.0])
    part = np.array([
        [0, 0, 1, 0],
        [0, 1, 0, 0],
        [0, 0, 0.1, 0],
        [0, 0.1, 0, 0.9],
        [0, 0, 1, 0],
    ], dtype=float)
    picked = dict(zip(MODES, identify(freqs, part)))
    assert picked == {"vertical1": 3.9, "lateral1": 5.0, "vertical2": 10.0, "torsion_lateral2": 9.5}


def test_identify_returns_nan_when_mode_missing():
    picked = identify(np.array([3.9, 5.0]), np.array([[0, 0, 1, 0], [0, 1, 0, 0]], dtype=float))
    assert np.isnan(picked[MODES.index("vertical2")])
    assert np.isnan(picked[MODES.index("torsion_lateral2")])


def test_write_values_changes_only_named_key_and_keeps_comments(tmp_path):
    path = tmp_path / "fem.yaml"
    path.write_text("section:   # 거더\n  J: 5.0   # 비틀림\npier:\n  J: 1.0\n", encoding="utf-8")
    write_values(path, {"section.J": 2.5})
    assert path.read_text(encoding="utf-8") == "section:   # 거더\n  J: 2.5   # 비틀림\npier:\n  J: 1.0\n"
