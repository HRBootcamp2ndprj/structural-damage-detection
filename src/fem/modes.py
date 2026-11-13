"""고유모드 → MODES 대응. 진동수 순서가 아니라 모드형상의 지배 자유도로 판별한다.

손상이 커지면 연직2와 비틀림·횡2의 진동수 순서가 바뀔 수 있으므로 순서로 고르면 안 된다.
"""
import numpy as np

from src.features.schema import MODES

# 참여도 열 순서: 모드 운동에너지 중 거더 절점 ux, uy, uz, rx의 몫. 행 합 = 거더 몫
FAMILIES = ("longitudinal", "lateral", "vertical", "torsion")
# 거더 몫이 이보다 작으면 교각 국부 모드로 보고 버린다
MIN_DECK_SHARE = 0.5


def classify(participation: np.ndarray) -> list[str]:
    """(n_modes, 4) 참여도 → 모드별 지배 자유도 이름. 교각 국부 모드는 "local"."""
    deck = participation.sum(axis=1)
    return ["local" if d < MIN_DECK_SHARE else FAMILIES[i]
            for d, i in zip(deck, np.argmax(participation, axis=1))]


def identify(freqs_hz: np.ndarray, participation: np.ndarray) -> np.ndarray:
    """진동수 오름차순 모드들에서 MODES 순서의 진동수 4개를 고른다. 못 찾으면 NaN.

    - vertical1, vertical2: 첫째·둘째 연직 모드
    - lateral1: 첫째 횡 모드
    - torsion_lateral2: lateral1 이후 첫 횡 또는 비틀림 모드 (실측에서 둘이 섞인 모드)
    """
    families = classify(participation)
    vertical = [f for f, k in zip(freqs_hz, families) if k == "vertical"]
    side = [f for f, k in zip(freqs_hz, families) if k in ("lateral", "torsion")]
    lateral = [f for f, k in zip(freqs_hz, families) if k == "lateral"]

    lateral1 = lateral[0] if lateral else np.nan
    after_l1 = [f for f in side if f > lateral1] if lateral else []
    picked = {
        "vertical1": vertical[0] if len(vertical) > 0 else np.nan,
        "lateral1": lateral1,
        "vertical2": vertical[1] if len(vertical) > 1 else np.nan,
        "torsion_lateral2": after_l1[0] if after_l1 else np.nan,
    }
    return np.array([picked[m] for m in MODES], dtype=float)
