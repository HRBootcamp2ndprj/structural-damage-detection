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
    assert real.loc[real.segment.isna()].shape[0] == 17 * 9
    assert sim.setup.isna().all() and set(sim.domain) == {"sim"}
    assert not ({1, 7, 10, 11} & set(sim.scenario))
    # 실측 기준선 정의: 시나리오 0 setup 행의 r 중앙값은 0
    base = real[(real.scenario == 0) & real.segment.isna()]
    assert abs(base.r_vertical1.median()) < 1e-9
