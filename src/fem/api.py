"""시뮬레이터(C) → 시뮬 데이터 생성(A) 인터페이스. 시그니처는 월요일(11/16)에 확정한다.

A는 이 함수만 반복 호출하고, OpenSees 내부 구현에는 의존하지 않는다.
"""
from dataclasses import dataclass, field

import numpy as np

from src.features.schema import MODES


@dataclass(frozen=True)
class Damage:
    """손상 함수 입력. group은 src/data/labels.py의 GROUPS 중 하나."""

    group: str
    severity: float  # 0~1 연속값. 실측 mm·시나리오에 맞추지 않는다 (ADR 0004)


@dataclass(frozen=True)
class ModalParams:
    """보정된 기준 모델 대비 환경 변동."""

    env_stiffness: float = 0.0  # 전역 강성 상대 변동 (온도 대용), 예: -0.01 = -1%
    extra: dict = field(default_factory=dict)  # C가 필요하면 추가 (감쇠 등)


@dataclass(frozen=True)
class ModalResult:
    freqs_hz: np.ndarray  # shape (len(MODES),), MODES 순서. 모드 대응 실패 시 NaN
    stiffness_loss: float  # 손상 구간 강성 감소율 0~1 (회귀 목표)


def run_modal(params: ModalParams, damage: Damage | None) -> ModalResult:
    """고유치 해석 1회. damage=None이면 손상 없음 (시뮬 기준선 f₀)."""
    raise NotImplementedError(f"run_modal: C 담당 — MODES={MODES}")
