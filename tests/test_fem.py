import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pytest
import yaml

from src.features.schema import MODES
from src.fem.api import Damage, ModalParams, run_modal
from src.fem.calibrate import write_values
from src.fem.model import load_config
from src.fem.modes import identify

V1, L1, V2, T2 = (MODES.index(m) for m in ("vertical1", "lateral1", "vertical2", "torsion_lateral2"))
DAMAGED_GROUPS = ("settlement", "local", "prestress_loss")


def test_baseline_returns_four_modes_near_target():
    cfg = load_config()
    target = np.array([cfg["calibration"]["target_hz"][m] for m in MODES])
    f0 = run_modal(ModalParams(), None).freqs_hz
    assert f0.shape == (len(MODES),)
    assert np.all(np.abs(f0 / target - 1) < 0.05), f"{f0} vs {target}: target_hz가 바뀌었으면 scripts/calibrate_fem.py를 실행"


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
    assert abs(ratio[V1] - (np.sqrt(1.02) - 1)) < 1e-3


def _ratio(damage):
    f0 = run_modal(ModalParams(), None).freqs_hz
    return run_modal(ModalParams(), damage).freqs_hz / f0 - 1


@pytest.mark.parametrize("group", DAMAGED_GROUPS)
def test_damage_lowers_vertical_modes_and_reports_loss(group):
    f0 = run_modal(ModalParams(), None).freqs_hz
    result = run_modal(ModalParams(), Damage(group, severity=1.0))
    r = result.freqs_hz / f0 - 1
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


@pytest.mark.parametrize("group", DAMAGED_GROUPS)
def test_all_modes_found_across_sampling_range(group):
    # A가 샘플링하는 범위 전체에서 NaN이 나오면 그 행의 특징이 비어 버린다
    for sev in (0.0, 0.5, 1.0):
        for loc in (0.0, 0.25, 0.5, 0.75, 1.0):
            for env in (-0.01, 0.01):
                f = run_modal(ModalParams(env_stiffness=env), Damage(group, sev, loc)).freqs_hz
                assert np.all(np.isfinite(f)), (group, sev, loc, env, f)


def test_thread_parallel_calls_match_serial():
    jobs = [(ModalParams(env_stiffness=e), Damage(g, 0.8, loc))
            for g in DAMAGED_GROUPS for loc in (0.1, 0.5, 0.9) for e in (-0.01, 0.01)]
    serial = np.array([run_modal(*j).freqs_hz for j in jobs])
    with ThreadPoolExecutor(8) as ex:
        threaded = np.array([r.freqs_hz for r in ex.map(lambda j: run_modal(*j), jobs * 4)])
    assert np.allclose(threaded, np.tile(serial, (4, 1)))


@pytest.mark.parametrize("damage", [
    Damage("settlement", severity=1.5),
    Damage("settlement", severity=0.5, location=-0.1),
    Damage("landslide", severity=0.5),
])
def test_invalid_damage_is_rejected(damage):
    with pytest.raises(ValueError):
        run_modal(ModalParams(), damage)


def test_torsion_lateral2_is_torsion_mode_even_above_lateral2():
    # 횡2(9.0)가 비틀림(10.3)보다 낮아도 비틀림 지배 모드를 고른다
    freqs = np.array([3.9, 5.0, 9.0, 9.8, 10.3])
    part = np.array([[0, 0, 1, 0], [0, 1, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0.2, 0, 0.8]], dtype=float)
    assert identify(freqs, part)[T2] == 10.3


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
    assert path.read_text(encoding="utf-8") == "section:   # 거더\n  J: 2.5000e+00   # 비틀림\npier:\n  J: 1.0\n"


def test_write_values_round_number_stays_float(tmp_path):
    # 5e+08처럼 소수점 없는 지수 표기는 PyYAML이 문자열로 읽는다
    path = tmp_path / "fem.yaml"
    path.write_text("supports:\n  k: 1.0\n", encoding="utf-8")
    write_values(path, {"supports.k": 5.0000001e8})
    assert isinstance(yaml.safe_load(path.read_text(encoding="utf-8"))["supports"]["k"], float)
