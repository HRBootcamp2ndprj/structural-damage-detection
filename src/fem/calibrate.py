"""손상 없는 FE 모델을 calibration.target_hz에 맞춘다. 실측 시나리오 0의 f₀만 목표로 쓴다 (ADR 0002)."""
import copy
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

from src.features.schema import MODES
from src.fem.model import solve
from src.fem.modes import DEFINITION, classify, identify, pick

# 보정 변수 (설정 키 경로). 각 변수가 주로 움직이는 모드: 연직 휨 → 연직1·2, 교각 횡 휨 → 횡1, 비틀림 → 비틀림·횡2
# 단부 횡 스프링도 횡1을 움직이지만 넣지 않는다. 넣으면 횡1·비틀림 목표 2개에 변수 3개라 해가 하나로 정해지지 않고,
# 같은 진동수를 내는 해들끼리 손상 반응이 달라진다.
PARAMS = (
    ("section", "Iy_vertical"),
    ("section", "J"),
    ("pier", "Iz"),
)
N_STARTS = 12
SEED = 0


@dataclass(frozen=True)
class Calibration:
    values: dict  # {"section.Iy_vertical": ..., ...}
    freqs_hz: np.ndarray  # 보정 후 MODES 순서 진동수
    families: list[str]  # 보정 후 MODES 각각으로 고른 모드의 지배 자유도
    cost: float

    @property
    def modes_ok(self) -> bool:
        """고른 모드가 모두 MODES 정의의 자유도인가. 아니면 보정값을 쓰면 안 된다."""
        return all(f == DEFINITION[m][0] for m, f in zip(MODES, self.families))


def _with(cfg: dict, values) -> dict:
    out = copy.deepcopy(cfg)
    for (group, key), v in zip(PARAMS, values):
        out[group][key] = float(v)
    return out


def calibrate(cfg: dict, n_starts: int = N_STARTS, seed: int = SEED) -> Calibration:
    """현재 설정값 ±1자리 안에서 출발점 여러 개로 최소제곱 보정하고 비용이 가장 작은 해를 고른다.

    모드 판별이 바뀌는 곳에서 잔차가 불연속이라 출발점 하나로는 국소해에 멈춘다.
    범위를 묶지 않으면 엉뚱한 모드를 고르는 해로 달아난다.
    """
    target = np.array([cfg["calibration"]["target_hz"][m] for m in MODES])
    center = np.log([cfg[g][k] for g, k in PARAMS])
    lo, hi = center - np.log(10), center + np.log(10)

    def residual(logx):
        freqs, part, _ = solve(_with(cfg, np.exp(logx)))
        picked = identify(freqs, part)
        return np.where(np.isnan(picked), 10.0, picked / target - 1.0)

    rng = np.random.default_rng(seed)
    starts = [center] + [rng.uniform(lo, hi) for _ in range(n_starts - 1)]
    best = min((least_squares(residual, x0, bounds=(lo, hi), diff_step=1e-3) for x0 in starts),
               key=lambda fit: fit.cost)

    values = np.exp(best.x)
    freqs, part, _ = solve(_with(cfg, values))
    families = classify(part)
    return Calibration(
        values={f"{g}.{k}": float(v) for (g, k), v in zip(PARAMS, values)},
        freqs_hz=identify(freqs, part),
        families=[families[i] if i >= 0 else "missing" for i in pick(part)],
        cost=float(best.cost),
    )


def write_values(path: Path, values: dict) -> None:
    """주석을 보존하려고 해당 키의 숫자만 바꾼다. 키는 "그룹.키" 형식이고 그룹 블록 안에서 찾는다.

    지수 표기에는 늘 소수점을 넣는다. PyYAML은 5e+08을 문자열로 읽는다.
    """
    text = path.read_text(encoding="utf-8")
    for dotted, v in values.items():
        group, key = dotted.split(".")
        block = re.search(rf"^{group}:.*\n((?:[ #].*\n)*)", text, flags=re.M)
        if block is None:
            raise KeyError(f"{path}: no block '{group}'")
        line = re.compile(rf"^(  {key}: *)\S+", flags=re.M)
        new_block, n = line.subn(rf"\g<1>{v:.4e}", block.group(1))
        if n != 1:
            raise KeyError(f"{path}: '{dotted}' found {n} times")
        text = text[: block.start(1)] + new_block + text[block.end(1):]
    path.write_text(text, encoding="utf-8")
