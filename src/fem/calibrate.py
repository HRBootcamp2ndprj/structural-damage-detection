"""손상 없는 FE 모델을 calibration.target_hz에 맞춘다. 실측 시나리오 0의 f₀만 목표로 쓴다 (ADR 0002)."""
import copy

import numpy as np
from scipy.optimize import least_squares

from src.features.schema import MODES
from src.fem.model import solve
from src.fem.modes import identify

# 보정 변수 (설정 키 경로). 각 변수가 주로 움직이는 모드: 연직 휨 → 연직1·2, 교각 횡 휨·단부 스프링 → 횡1, 비틀림 → 비틀림·횡2
PARAMS = (
    ("section", "Iy_vertical"),
    ("section", "J"),
    ("pier", "Iz"),
    ("supports", "abutment_lateral_k"),
)


def _with(cfg: dict, values) -> dict:
    out = copy.deepcopy(cfg)
    for (group, key), v in zip(PARAMS, values):
        out[group][key] = float(v)
    return out


def calibrate(cfg: dict) -> tuple[dict, np.ndarray]:
    """반환: (보정된 값 {"section.Iy_vertical": ..., ...}, 보정 후 MODES 순서 진동수)."""
    target = np.array([cfg["calibration"]["target_hz"][m] for m in MODES])
    x0 = np.log([cfg[g][k] for g, k in PARAMS])

    def residual(logx):
        freqs, part, _ = solve(_with(cfg, np.exp(logx)))
        picked = identify(freqs, part)
        return np.where(np.isnan(picked), 10.0, picked / target - 1.0)

    # 모드 판별이 바뀌면 잔차가 불연속이라 무한정 찾게 두면 엉뚱한 해로 간다. 초기값 ±1자리로 묶는다.
    fit = least_squares(residual, x0, bounds=(x0 - np.log(10), x0 + np.log(10)), diff_step=1e-3)
    values = np.exp(fit.x)
    freqs, part, _ = solve(_with(cfg, values))
    return {f"{g}.{k}": float(v) for (g, k), v in zip(PARAMS, values)}, identify(freqs, part)
