import subprocess
import sys

from src.features.schema import COLUMNS, read_features


def test_fake_features_follow_schema(tmp_path):
    subprocess.run([sys.executable, "scripts/make_fake_features.py", "--out", str(tmp_path), "--n-sim", "10"],
                   check=True)
    real = read_features(tmp_path / "real_features.csv")
    sim = read_features(tmp_path / "sim_features.csv")
    assert list(real.columns) == list(COLUMNS) == list(sim.columns)
    assert len(real) == 17 * 9 * 11  # setup 행 + 구간 행
    assert real.segment.isna().sum() == 17 * 9
    # 시뮬은 시나리오·setup이 없고 그룹과 연속 손상 강도로만 정의된다
    assert sim.scenario.isna().all() and sim.setup.isna().all()
    assert set(sim.group) == {"healthy", "settlement", "local", "prestress_loss"}
    assert sim.severity.between(0, 1).all() and real.severity.isna().all()
    assert sim.settlement_mm.isna().all()
    assert set(real.settlement_mm.dropna()) == {0, 20, 40, 80, 95}
    # 실측 기준선: 시나리오 0 setup 행 진동수의 중앙값 → r 중앙값 0
    base = real[(real.scenario == 0) & real.segment.isna()]
    assert abs(base.r_vertical1.median()) < 1e-9
