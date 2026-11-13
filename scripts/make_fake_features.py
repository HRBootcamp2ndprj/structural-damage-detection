"""가짜 특징 CSV 생성 — 실제 CSV가 나오기 전에 B(모델)·D(시각화)가 바로 개발하도록.

사용법: python scripts/make_fake_features.py [--out data/processed/fake] [--n-sim 200]

docs/feature_schema.md 형식 그대로 real_features.csv, sim_features.csv를 만든다.
진동수 변화량은 그럴듯하게 정한 가정값일 뿐 실측·시뮬 결과가 아니다.
반영한 성질:
  - 침하는 연직 모드가 크게 감소 (시나리오 5에서 약 -6%), 기울어짐(6)은 회복
  - 국부손상·프리스트레스 손실은 1% 미만 변화 → 구분 어려움
  - 시뮬 f₀는 실측 f₀와 수 % 어긋남 (보정 오차) → Δf/f₀로 상쇄되는지 확인용
  - 실측은 구간 단위가 setup 단위보다 노이즈가 큼, 일부 모드 추출 실패(빈 값)
  - 시뮬은 전역 강성 변동(온도 대용)으로 모든 모드가 같이 움직임
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.data.labels import (  # noqa: E402
    HEALTHY, LOCAL, N_SETUPS, N_SEGMENTS, PRESTRESS_LOSS, SCENARIO_GROUP, SETTLEMENT, UNSIMULATED,
)
from src.features.schema import COLUMNS, MODES  # noqa: E402

REAL_F0 = np.array([3.88, 5.03, 9.80, 10.30])
SIM_F0 = np.array([3.95, 4.90, 10.10, 10.60])  # 보정 오차 모사

# 시나리오별 기준 변화량(연직1 기준, 비율) — 가정값
SEVERITY = {
    0: 0.0, 1: -0.002, 2: -0.003, 3: -0.010, 4: -0.036, 5: -0.062, 6: -0.005,
    7: 0.002, 8: -0.003, 9: -0.005, 10: -0.004, 11: -0.008,
    12: -0.002, 13: -0.003, 14: -0.004, 15: -0.006, 16: -0.008,
}
# 그룹별 모드 민감도 (vertical1, lateral1, vertical2, torsion_lateral2)
MODE_WEIGHT = {
    HEALTHY: np.ones(4),
    None: np.ones(4),
    SETTLEMENT: np.array([1.0, 0.3, 0.8, 0.4]),
    LOCAL: np.array([1.0, 0.8, 1.2, 1.5]),
    PRESTRESS_LOSS: np.array([1.0, 0.2, 1.4, 0.6]),
}


def _rows(domain, scenario, ratios, f0, setup=None, segment=None):
    group = SCENARIO_GROUP[scenario]
    rows = []
    for r in ratios:
        row = {"domain": domain, "scenario": scenario, "setup": setup, "segment": segment, "group": group}
        for m, ri, f0i in zip(MODES, r, f0):
            row[f"f_{m}"] = f0i * (1 + ri)
            row[f"r_{m}"] = ri
        rows.append(row)
    return rows


def make_real(rng):
    rows = []
    for s in range(17):
        mean = SEVERITY[s] * MODE_WEIGHT[SCENARIO_GROUP[s]]
        for u in range(N_SETUPS):
            setup_r = mean + rng.normal(0, 0.003, 4)  # setup 간 변동 (환경·측정)
            rows += _rows("real", s, [setup_r], REAL_F0, setup=u)
            seg_r = setup_r + rng.normal(0, 0.006, (N_SEGMENTS, 4))
            for g in range(N_SEGMENTS):
                rows += _rows("real", s, seg_r[g:g + 1], REAL_F0, setup=u, segment=g)
    df = pd.DataFrame(rows)
    # 실측 기준선은 시나리오 0의 setup 단위 진동수 중앙값 → 그 기준으로 r 재계산
    base = df[(df.scenario == 0) & df.segment.isna()]
    for m in MODES:
        f0 = base[f"f_{m}"].median()
        df[f"r_{m}"] = (df[f"f_{m}"] - f0) / f0
    # 추출 실패: 구간 단위에서 고차 모드 일부를 빈 값으로
    for m, p in zip(MODES, (0.0, 0.02, 0.05, 0.10)):
        miss = df.segment.notna() & (rng.random(len(df)) < p)
        df.loc[miss, [f"f_{m}", f"r_{m}"]] = np.nan
    return df


def make_sim(rng, n):
    scenarios = [s for s, g in SCENARIO_GROUP.items() if g is not None and s not in UNSIMULATED and s != 7]
    rows = []
    for s in scenarios:
        w = MODE_WEIGHT[SCENARIO_GROUP[s]]
        # 손상 크기를 시나리오 주변에서 랜덤화
        sev = SEVERITY[s] * rng.uniform(0.6, 1.4, (n, 1))
        global_k = rng.uniform(-0.03, 0.03, (n, 1)) / 2  # 강성 ±3% → 진동수 약 ±1.5%
        r = sev * w + global_k + rng.normal(0, 0.005, (n, 4))
        rows += _rows("sim", s, r, SIM_F0)
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/processed/fake")
    parser.add_argument("--n-sim", type=int, default=200, help="시뮬 시나리오당 샘플 수")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    rng = np.random.default_rng(args.seed)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, df in (("real_features.csv", make_real(rng)), ("sim_features.csv", make_sim(rng, args.n_sim))):
        df = df[list(COLUMNS)]
        for c in ("scenario", "setup", "segment"):
            df[c] = df[c].astype("Int64")
        df.to_csv(out / name, index=False, float_format="%.6g")
        print(f"{out / name}: {len(df)} rows")


if __name__ == "__main__":
    main()
