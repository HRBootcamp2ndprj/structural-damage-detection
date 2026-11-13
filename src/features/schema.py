"""특징 CSV 열 정의. docs/feature_schema.md와 같아야 한다."""

MODES = ("vertical1", "lateral1", "vertical2", "torsion_lateral2")
FREQ_COLS = tuple(f"f_{m}" for m in MODES)
RATIO_COLS = tuple(f"r_{m}" for m in MODES)
ID_COLS = ("domain", "scenario", "setup", "segment", "group")
# 시뮬 전용 메타데이터 (실측 행은 비움)
SIM_META_COLS = ("severity", "stiffness_loss", "env_stiffness", "env_noise")
# 실측 전용 메타데이터 (시뮬 행은 비움, 평가 전용 — 학습·튜닝에 쓰지 않음)
REAL_META_COLS = ("settlement_mm",)
COLUMNS = ID_COLS + FREQ_COLS + RATIO_COLS + SIM_META_COLS + REAL_META_COLS

# 정수 열 (비어 있을 수 있으므로 pandas nullable Int64로 읽는다)
INT_COLS = ("scenario", "setup", "segment", "settlement_mm")


def read_features(path):
    """특징 CSV를 열 순서·타입을 맞춰 읽는다."""
    import pandas as pd

    df = pd.read_csv(path)
    missing = set(COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"{path}: missing columns {sorted(missing)}")
    return to_schema(df)


def to_schema(df):
    """열 순서와 정수 열 타입을 스키마에 맞춘다. 없는 열은 빈 값으로 채운다."""
    df = df.reindex(columns=list(COLUMNS))
    for c in INT_COLS:
        df[c] = df[c].astype("Int64")
    return df
