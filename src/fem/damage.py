"""손상 함수: (거더 배치, 손상 강도, 위치) → 거더 요소별 강성 배율. 수치는 configs/fem.yaml의 damage 블록.

손상 형태는 물리 지식으로 정하고 실측 진동수 변화에 맞추지 않는다 (ADR 0002, 0005).
"""
import numpy as np

from src.data.labels import HEALTHY, LOCAL, PRESTRESS_LOSS, SETTLEMENT
from src.fem.model import Geometry, StiffnessField


def _lerp(lo_hi, t: float) -> float:
    lo, hi = lo_hi
    return lo + (hi - lo) * t


def _span_center(cfg: dict, location: float) -> float:
    """구간 [a, b] 안에서 길이 length_m 구간이 다 들어가도록 중심을 location(0~1)으로 고른다."""
    a, b = cfg["region_m"]
    half = cfg["length_m"] / 2
    return _lerp((a + half, b - half), location)


def settlement(geo: Geometry, cfg: dict, severity: float, location: float) -> StiffnessField:
    """교각 침하로 생긴 교각 위 거더 균열. 교각에서 최대, 양옆으로 선형 감소. location은 균열 범위."""
    x = geo.deck_x_mid
    half = _lerp(cfg["half_width_m"], location)
    # 요소 중심이 아니라 요소에서 가장 가까운 점까지 거리를 잰다. 그래야 교각에 닿은 요소가 최대 감소를 받는다.
    # 모델이 좌우 대칭이라 어느 교각인지는 진동수에 영향이 없다
    dist = np.maximum(np.abs(x - geo.pier_x[0]) - np.diff(geo.deck_x) / 2, 0)
    shape = np.clip(1 - dist / half, 0, None)
    iy = 1 - cfg["max_loss"] * severity * shape
    return StiffnessField(iy=iy, j=np.ones_like(x))


def local(geo: Geometry, cfg: dict, severity: float, location: float) -> StiffnessField:
    """박리 패치. 박스 벽체가 떨어져 나가므로 연직 휨과 비틀림을 함께 줄인다. location은 패치 위치."""
    x = geo.deck_x_mid
    center = _span_center(cfg, location)
    inside = np.abs(x - center) <= cfg["length_m"] / 2
    k = np.where(inside, 1 - cfg["max_loss"] * severity, 1.0)
    return StiffnessField(iy=k, j=k.copy())


def prestress_loss(geo: Geometry, cfg: dict, severity: float, location: float) -> StiffnessField:
    """프리스트레스가 빠져 균열이 열리는 긴 구간의 작은 휨강성 감소. location은 구간 위치."""
    x = geo.deck_x_mid
    center = _span_center(cfg, location)
    inside = np.abs(x - center) <= cfg["length_m"] / 2
    iy = np.where(inside, 1 - cfg["max_loss"] * severity, 1.0)
    return StiffnessField(iy=iy, j=np.ones_like(x))


DAMAGE_FUNCTIONS = {
    SETTLEMENT: settlement,
    LOCAL: local,
    PRESTRESS_LOSS: prestress_loss,
}


def stiffness_field(geo: Geometry, damage_cfg: dict, group: str, severity: float, location: float) -> StiffnessField:
    if not 0.0 <= severity <= 1.0 or not 0.0 <= location <= 1.0:
        raise ValueError(f"severity, location must be in [0, 1], got {severity}, {location}")
    if group == HEALTHY:
        return StiffnessField.intact(len(geo.deck_x_mid))
    if group not in DAMAGE_FUNCTIONS:
        raise ValueError(f"unknown damage group {group!r}, expected one of {sorted(DAMAGE_FUNCTIONS)}")
    return DAMAGE_FUNCTIONS[group](geo, damage_cfg[group], severity, location)


def stiffness_loss(field: StiffnessField) -> float:
    """손상 구간의 최대 연직 휨강성 감소율 (회귀 목표)."""
    return float(1 - field.iy.min())
