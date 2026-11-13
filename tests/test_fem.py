import sys
import time
from pathlib import Path

import numpy as np
import pytest

from src.features.schema import MODES
from src.fem.api import Damage, ModalParams, run_modal
from src.fem.model import load_config
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


V1, L1, V2, T2 = (MODES.index(m) for m in MODES)
DAMAGED_GROUPS = ("settlement", "local", "prestress_loss")


def _ratio(damage):
    f0 = run_modal(ModalParams(), None).freqs_hz
    return run_modal(ModalParams(), damage).freqs_hz / f0 - 1


@pytest.mark.parametrize("group", DAMAGED_GROUPS)
def test_damage_lowers_vertical_modes_and_reports_loss(group):
    result = run_modal(ModalParams(), Damage(group, severity=1.0))
    r = _ratio(Damage(group, severity=1.0))
    assert min(r[V1], r[V2]) < -0.001
    assert np.all(r <= 1e-9)
    max_loss = load_config()["damage"][group]["max_loss"]
    assert result.stiffness_loss == pytest.approx(max_loss)


@pytest.mark.parametrize("group", ("settlement", "prestress_loss"))
def test_cracking_damage_leaves_lateral1_unchanged(group):
    # 손상은 연직 휨만 줄여서 4개 모드를 함께 움직이는 온도 변동과 구분된다
    assert abs(_ratio(Damage(group, severity=1.0))[L1]) < 1e-6


@pytest.mark.parametrize("group", DAMAGED_GROUPS + ("healthy",))
def test_zero_severity_equals_healthy(group):
    assert np.allclose(_ratio(Damage(group, severity=0.0)), 0)
    assert run_modal(ModalParams(), Damage(group, severity=0.0)).stiffness_loss == 0


def test_settlement_frequency_drop_grows_with_severity():
    drops = [-_ratio(Damage("settlement", severity=s))[V1] for s in (0.25, 0.5, 1.0)]
    assert drops[0] < drops[1] < drops[2]


def test_location_moves_local_damage_signature():
    # 주경간 중앙 패치는 연직1을, 1/4점 쪽 패치는 연직2를 더 낮춘다
    mid = _ratio(Damage("local", severity=1.0, location=0.5))
    quarter = _ratio(Damage("local", severity=1.0, location=0.25))
    assert mid[V1] < mid[V2]
    assert quarter[V2] < quarter[V1]


@pytest.mark.parametrize("damage", [
    Damage("settlement", severity=1.5),
    Damage("settlement", severity=0.5, location=-0.1),
    Damage("landslide", severity=0.5),
])
def test_invalid_damage_is_rejected(damage):
    with pytest.raises(ValueError):
        run_modal(ModalParams(), damage)


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
