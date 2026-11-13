"""가짜 특징 CSV 생성 — 실제 CSV가 나오기 전에 B(모델)·D(대시보드)가 바로 개발하도록.

사용법: python scripts/make_fake_features.py [--out data/processed/fake] [--n-sim 300]

docs/feature_schema.md 형식 그대로 real_features.csv, sim_features.csv를 만든다.
진동수 변화량은 그럴듯하게 정한 가정값일 뿐 실측·시뮬 결과가 아니다.
실제 파이프라인과 같은 순서를 흉내 낸다:
  1. 실측: 시나리오 0의 setup 단위 진동수 중앙값 = f₀, 표준편차 = σ₀
  2. 시뮬: 손상 강도 severity를 그룹별 연속값으로 샘플링 (시나리오·mm에 맞추지 않음),
     노이즈 크기는 σ₀ 기준으로 랜덤화
반영한 성질:
  - 침하는 연직 모드가 크게 감소, 국부손상·프리스트레스 손실은 1% 미만
  - 시뮬 f₀는 실측 f₀와 수 % 어긋남 (보정 오차) → Δf/f₀로 상쇄되는지 확인용
  - 실측 구간 단위 행은 setup 단위보다 노이즈가 크고, 고차 모드 일부가 빈 값
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.data.labels import (  # noqa: E402
    GROUPS, HEALTHY, LOCAL, N_SEGMENTS, N_SETUPS, PRESTRESS_LOSS, SCENARIO_GROUP, SETTLEMENT,
)
from src.features.schema import MODES, to_schema  # noqa: E402

REAL_F0 = np.array([3.88, 5.03, 9.80, 10.30])
SIM_F0 = np.array([3.95, 4.90, 10.10, 10.60])  # 보정 오차 모사

# 실측 시나리오별 연직1 변화율 — 가정값
REAL_SHIFT = {
    0: 0.0, 1: -0.002, 2: -0.003, 3: -0.010, 4: -0.036, 5: -0.062, 6: -0.005,
    7: 0.002, 8: -0.003, 9: -0.005, 10: -0.004, 11: -0.008,
    12: -0.002, 13: -0.003, 14: -0.004, 15: -0.006, 16: -0.008,
}
SETTLEMENT_MM = {0: 0, 7: 0, 2: 20, 3: 40, 4: 80, 5: 95}

# 그룹별 모드 민감도 (vertical1, lateral1, vertical2, torsion_lateral2)
MODE_WEIGHT = {
    HEALTHY: np.ones(4),
    None: np.ones(4),
    SETTLEMENT: np.array([1.0, 0.3, 0.8, 0.4]),
    LOCAL: np.array([1.0, 0.8, 1.2, 1.5]),
    PRESTRESS_LOSS: np.array([1.0, 0.2, 1.4, 0.6]),
}
# 시뮬: severity=1일 때 연직1 변화율, 손상 구간 강성 감소율 — 가정값
SIM_MAX_SHIFT = {HEALTHY: 0.0, SETTLEMENT: -0.07, LOCAL: -0.006, PRESTRESS_LOSS: -0.009}
SIM_MAX_LOSS = {HEALTHY: 0.0, SETTLEMENT: 0.6, LOCAL: 0.3, PRESTRESS_LOSS: 0.2}
ENV_STIFFNESS = 0.006  # 전역 강성 변동 ±0.6% (온도 대용) → 진동수 약 ±0.3%


def make_real(rng):
    rows = []
    for s in range(17):
        mean = REAL_SHIFT[s] * MODE_WEIGHT[SCENARIO_GROUP[s]]
        for u in range(N_SETUPS):
            setup_r = mean + rng.normal(0, 0.003, 4)  # setup 간 변동 (환경·측정)
            seg_r = setup_r + rng.normal(0, 0.006, (N_SEGMENTS, 4))
            for g, r in [(None, setup_r)] + list(enumerate(seg_r)):
                row = {"domain": "real", "scenario": s, "setup": u, "segment": g,
                       "group": SCENARIO_GROUP[s], "settlement_mm": SETTLEMENT_MM.get(s)}
                row.update({f"f_{m}": f0 * (1 + ri) for m, f0, ri in zip(MODES, REAL_F0, r)})
                rows.append(row)
    df = pd.DataFrame(rows)
    # 추출 실패: 구간 단위에서 고차 모드 일부를 빈 값으로
    for m, p in zip(MODES, (0.0, 0.02, 0.05, 0.10)):
        df.loc[df.segment.notna() & (rng.random(len(df)) < p), f"f_{m}"] = np.nan
    # 기준선: 시나리오 0의 setup 단위 진동수 중앙값, 산포 σ₀ = 그 r의 표준편차
    base = df[(df.scenario == 0) & df.segment.isna()]
    sigma0 = []
    for m in MODES:
        f0 = base[f"f_{m}"].median()
        df[f"r_{m}"] = (df[f"f_{m}"] - f0) / f0
        sigma0.append(((base[f"f_{m}"] - f0) / f0).std())
    return df, np.array(sigma0)


def make_sim(rng, n, sigma0):
    frames = []
    for group in GROUPS:
        sev = np.zeros(n) if group == HEALTHY else rng.uniform(0.0, 1.0, n)
        env_k = rng.uniform(-ENV_STIFFNESS, ENV_STIFFNESS, n)
        env_noise = rng.uniform(0.5, 1.5, n)  # σ₀ 대비 배율
        r = (SIM_MAX_SHIFT[group] * sev[:, None] * MODE_WEIGHT[group]
             + env_k[:, None] / 2
             + rng.normal(0, 1, (n, 4)) * sigma0 * env_noise[:, None])
        df = pd.DataFrame({"domain": "sim", "group": group, "severity": sev,
                           "stiffness_loss": sev * SIM_MAX_LOSS[group],
                           "env_stiffness": env_k, "env_noise": env_noise * sigma0.mean()})
        for i, m in enumerate(MODES):
            df[f"r_{m}"] = r[:, i]
            df[f"f_{m}"] = SIM_F0[i] * (1 + r[:, i])
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/processed/fake")
    parser.add_argument("--n-sim", type=int, default=300, help="시뮬 손상 그룹당 샘플 수")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    rng = np.random.default_rng(args.seed)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    real, sigma0 = make_real(rng)
    sim = make_sim(rng, args.n_sim, sigma0)
    for name, df in (("real_features.csv", real), ("sim_features.csv", sim)):
        to_schema(df).to_csv(out / name, index=False, float_format="%.6g")
        print(f"{out / name}: {len(df)} rows")
    print("σ₀ (scenario 0, setup rows):", np.round(sigma0, 4))


if __name__ == "__main__":
    main()
