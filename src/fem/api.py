"""시뮬레이터(C) → 시뮬 데이터 생성(A) 인터페이스. 시그니처는 월요일(11/16)에 확정한다.

A는 이 함수만 반복 호출하고, OpenSees 내부 구현에는 의존하지 않는다.
"""
from dataclasses import dataclass, field
from functools import cache

import numpy as np

from src.fem.damage import stiffness_field, stiffness_loss
from src.fem.model import geometry, load_config, solve
from src.fem.modes import identify


@dataclass(frozen=True)
class Damage:
    """손상 함수 입력. group은 src/data/labels.py의 GROUPS 중 하나."""

    group: str
    severity: float  # 0~1 연속값. 실측 mm·시나리오에 맞추지 않는다 (ADR 0004)
    location: float = 0.5  # 0~1, 그룹별 허용 구간 안의 상대 위치·범위. A가 균등 샘플링 (ADR 0005)


@dataclass(frozen=True)
class ModalParams:
    """보정된 기준 모델 대비 환경 변동."""

    env_stiffness: float = 0.0  # 전역 탄성계수 상대 변동 (온도 대용), 예: -0.01 = E × 0.99
    extra: dict = field(default_factory=dict)  # C가 필요하면 추가 (감쇠 등)


@dataclass(frozen=True)
class ModalResult:
    freqs_hz: np.ndarray  # shape (len(MODES),), MODES 순서. 모드 대응 실패 시 NaN
    stiffness_loss: float  # 손상 구간 강성 감소율 0~1 (회귀 목표)


@cache
def _config() -> dict:
    return load_config()


def run_modal(params: ModalParams, damage: Damage | None) -> ModalResult:
    """고유치 해석 1회. damage=None이면 손상 없음 (시뮬 기준선 f₀).

    호출당 수 ms라 직렬로 충분하다. 병렬화하려면 프로세스 병렬을 쓴다. 스레드 병렬은 잠금 때문에 빨라지지 않는다.
    """
    cfg = _config()
    stiffness = None if damage is None else stiffness_field(
        geometry(cfg), cfg["damage"], damage.group, damage.severity, damage.location)
    freqs, participation, _ = solve(cfg, e_scale=1.0 + params.env_stiffness, field=stiffness)
    loss = 0.0 if stiffness is None else stiffness_loss(stiffness)
    return ModalResult(freqs_hz=identify(freqs, participation), stiffness_loss=loss)
