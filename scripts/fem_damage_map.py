"""손상 함수 진단: 그룹별 Δf/f₀ 분포가 얼마나 겹치는지 그림과 시뮬 내부 분류 정확도로 본다.

A의 시뮬 데이터 생성을 흉내 낸다 (severity, location, 온도 변동, σ₀ 기준 노이즈).
정확도는 시뮬 안에서의 상한일 뿐 실측 성능이 아니다. 실측 f₀·σ₀가 나오면 --sigma0로 다시 돌린다.

사용법: python scripts/fem_damage_map.py [--n 300] [--sigma0 0.003] [--out outputs/fem]
"""
import argparse
import sys
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from sklearn.ensemble import RandomForestClassifier  # noqa: E402
from sklearn.model_selection import cross_val_score  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.data.labels import GROUPS, HEALTHY  # noqa: E402
from src.features.schema import MODES  # noqa: E402
from src.fem.api import Damage, ModalParams, run_modal  # noqa: E402

COLORS = {"healthy": "#4c78a8", "settlement": "#e45756", "local": "#54a24b", "prestress_loss": "#f58518"}


def simulate(n: int, sigma0: float, env_pct: float, sev_low: float, seed: int):
    rng = np.random.default_rng(seed)
    f0 = run_modal(ModalParams(), None).freqs_hz
    r, labels = [], []
    for group in GROUPS:
        for _ in range(n):
            params = ModalParams(env_stiffness=rng.uniform(-env_pct, env_pct) / 100)
            damage = None if group == HEALTHY else Damage(group, rng.uniform(sev_low, 1.0), rng.uniform(0, 1))
            f = run_modal(params, damage).freqs_hz
            noise = rng.normal(0, 1, 4) * sigma0 * rng.uniform(0.5, 1.5)
            r.append(f / f0 - 1 + noise)
            labels.append(group)
    return np.array(r), np.array(labels)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=300, help="그룹당 샘플 수")
    parser.add_argument("--sigma0", type=float, default=0.003, help="모드별 기준 산포 (Δf/f₀). 기본값은 가짜 데이터 가정")
    parser.add_argument("--env-pct", type=float, default=1.0, help="전역 강성 변동 ±%% (simgen.yaml)")
    parser.add_argument("--sev-low", type=float, default=0.0, help="손상 그룹 severity 하한")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", default="outputs/fem")
    args = parser.parse_args()

    r, y = simulate(args.n, args.sigma0, args.env_pct, args.sev_low, args.seed)
    v1, l1, v2 = (MODES.index(m) for m in ("vertical1", "lateral1", "vertical2"))
    # 횡1은 손상에 거의 안 움직이고 온도에는 움직이므로, 빼 주면 온도 변동이 줄어든다.
    # 단부 횡 스프링은 온도에 따라 변하지 않아서 횡1이 연직보다 덜 움직이므로 완전히 상쇄되지는 않는다
    views = [
        ("raw", r[:, v1], r[:, v2], "Δf/f₀ vertical1 [%]", "Δf/f₀ vertical2 [%]"),
        ("minus lateral1", r[:, v1] - r[:, l1], r[:, v2] - r[:, l1],
         "vertical1 − lateral1 [%]", "vertical2 − lateral1 [%]"),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.5))
    for ax, (title, xs, ys, xl, yl) in zip(axes, views):
        for g in GROUPS:
            m = y == g
            ax.scatter(xs[m] * 100, ys[m] * 100, s=6, alpha=0.5, color=COLORS[g], label=g)
        ax.set(title=title, xlabel=xl, ylabel=yl)
        ax.axhline(0, color="0.8", lw=0.8)
        ax.axvline(0, color="0.8", lw=0.8)
        ax.legend(markerscale=3)
    fig.suptitle(f"Sim damage map: n={args.n}/group, σ₀={args.sigma0:.2%}, env ±{args.env_pct}%, "
                 f"severity U({args.sev_low}, 1)")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out / "damage_map.png", dpi=150)

    clf = RandomForestClassifier(n_estimators=200, random_state=0)
    acc4 = cross_val_score(clf, r, y, cv=5, scoring="balanced_accuracy").mean()
    acc2 = cross_val_score(clf, r, y != HEALTHY, cv=5, scoring="balanced_accuracy").mean()
    print(f"saved {out / 'damage_map.png'}")
    print(f"시뮬 내부 5-fold 균형 정확도 (상한, 실측 아님): 손상 유무 {acc2:.3f}, 4그룹 {acc4:.3f}")


if __name__ == "__main__":
    main()
