"""특징 CSV 열 정의. docs/feature_schema.md와 같아야 한다."""

MODES = ("vertical1", "lateral1", "vertical2", "torsion_lateral2")
FREQ_COLS = tuple(f"f_{m}" for m in MODES)
RATIO_COLS = tuple(f"r_{m}" for m in MODES)
ID_COLS = ("domain", "scenario", "setup", "segment", "group")
COLUMNS = ID_COLS + FREQ_COLS + RATIO_COLS

# 정수 열 (비어 있을 수 있으므로 pandas nullable Int64로 읽는다)
INT_COLS = ("scenario", "setup", "segment")


def read_features(path):
    """특징 CSV를 열 순서·타입을 맞춰 읽는다."""
    import pandas as pd

    df = pd.read_csv(path)
    missing = set(COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"{path}: missing columns {sorted(missing)}")
    df = df[list(COLUMNS)]
    for c in INT_COLS:
        df[c] = df[c].astype("Int64")
    return df
