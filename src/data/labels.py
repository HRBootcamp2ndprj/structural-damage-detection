"""Z24 PDT 시나리오 라벨과 손상 그룹 매핑. 용어는 CONTEXT.md 참고."""

N_SCENARIOS = 17
N_SETUPS = 9
N_SEGMENTS = 10

SCENARIO_NAMES = {
    0: "기준상태1",
    1: "하강장치 설치",
    2: "교각 침하 20mm",
    3: "교각 침하 40mm",
    4: "교각 침하 80mm",
    5: "교각 침하 95mm",
    6: "기초 기울어짐",
    7: "기준상태2",
    8: "박리 12㎡",
    9: "박리 24㎡",
    10: "산사태",
    11: "콘크리트 힌지 파괴",
    12: "앵커헤드 2개 파괴",
    13: "앵커헤드 4개 파괴",
    14: "텐던 2개 파단",
    15: "텐던 4개 파단",
    16: "텐던 6개 파단",
}

HEALTHY = "healthy"
SETTLEMENT = "settlement"
LOCAL = "local"
PRESTRESS_LOSS = "prestress_loss"
GROUPS = (HEALTHY, SETTLEMENT, LOCAL, PRESTRESS_LOSS)

# 시나리오 1은 어느 그룹에도 속하지 않음 (None → 제외)
SCENARIO_GROUP = {
    0: HEALTHY, 1: None,
    2: SETTLEMENT, 3: SETTLEMENT, 4: SETTLEMENT, 5: SETTLEMENT, 6: SETTLEMENT,
    7: HEALTHY,
    8: LOCAL, 9: LOCAL, 10: LOCAL, 11: LOCAL,
    12: PRESTRESS_LOSS, 13: PRESTRESS_LOSS, 14: PRESTRESS_LOSS,
    15: PRESTRESS_LOSS, 16: PRESTRESS_LOSS,
}

# 실측에는 있지만 시뮬 학습에는 넣지 않는 시나리오
UNSIMULATED = frozenset({10, 11})

# 실측 시나리오 0은 보정·기준선 전용, 테스트에서는 제외 (ADR 0002)
CALIBRATION_SCENARIOS = frozenset({0})


def decode_index(index: int) -> tuple[int, int, int]:
    """inputs.npy 행 번호 → (시나리오, setup, 구간)."""
    scenario, rest = divmod(index, N_SETUPS * N_SEGMENTS)
    setup, segment = divmod(rest, N_SEGMENTS)
    return scenario, setup, segment


def is_damaged(scenario: int) -> bool | None:
    group = SCENARIO_GROUP[scenario]
    return None if group is None else group != HEALTHY
