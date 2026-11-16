"""고유모드 → MODES 대응. 진동수 순서가 아니라 모드형상의 지배 자유도로 판별한다.

손상이 커지면 연직2와 비틀림·횡2의 진동수 순서가 바뀔 수 있으므로 순서로 고르면 안 된다.
"""
import numpy as np

from src.features.schema import MODES

# 참여도 열 순서: 모드 운동에너지 중 거더 절점 ux, uy, uz, rx의 몫. 행 합 = 거더 몫
FAMILIES = ("longitudinal", "lateral", "vertical", "torsion")
# 거더 몫이 이보다 작으면 교각 국부 모드로 보고 버린다
MIN_DECK_SHARE = 0.5
# MODES 각각을 (지배 자유도, 그 자유도 모드 중 몇 번째)로 정의한다.
# torsion_lateral2는 실측에서 비틀림과 횡2가 섞인 모드지만, 시뮬에서는 비틀림 지배 모드로 고정한다.
# 횡2를 고르면 비틀림 강성을 줄이는 국부손상이 이 특징에서 사라지고, 보정 출발점에 따라 둘이 뒤바뀐다.
DEFINITION = {
    "vertical1": ("vertical", 0),
    "lateral1": ("lateral", 0),
    "vertical2": ("vertical", 1),
    "torsion_lateral2": ("torsion", 0),
}


def classify(participation: np.ndarray) -> list[str]:
    """(n_modes, 4) 참여도 → 모드별 지배 자유도 이름. 교각 국부 모드는 "local"."""
    deck = participation.sum(axis=1)
    return ["local" if d < MIN_DECK_SHARE else FAMILIES[i]
            for d, i in zip(deck, np.argmax(participation, axis=1))]


def pick(participation: np.ndarray) -> np.ndarray:
    """진동수 오름차순 모드들에서 MODES 순서로 고른 모드 인덱스. 못 찾으면 -1."""
    families = classify(participation)
    out = []
    for m in MODES:
        family, rank = DEFINITION[m]
        idx = [i for i, k in enumerate(families) if k == family]
        out.append(idx[rank] if len(idx) > rank else -1)
    return np.array(out)


def identify(freqs_hz: np.ndarray, participation: np.ndarray) -> np.ndarray:
    """MODES 순서의 진동수 4개. 못 찾으면 NaN."""
    idx = pick(participation)
    return np.where(idx >= 0, np.asarray(freqs_hz, dtype=float)[idx], np.nan)
