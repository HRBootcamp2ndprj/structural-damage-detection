"""손상 없는 FE 모델을 calibration.target_hz(실측 시나리오 0의 f₀)에 맞추고 configs/fem.yaml 값을 갱신한다."""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.features.schema import MODES  # noqa: E402
from src.fem.calibrate import calibrate  # noqa: E402
from src.fem.model import load_config  # noqa: E402


def write_values(path: Path, values: dict) -> None:
    """주석을 보존하려고 해당 키의 숫자만 바꾼다. 키는 "그룹.키" 형식이고 그룹 블록 안에서 찾는다."""
    text = path.read_text(encoding="utf-8")
    for dotted, v in values.items():
        group, key = dotted.split(".")
        block = re.search(rf"^{group}:.*\n((?:[ #].*\n)*)", text, flags=re.M)
        if block is None:
            raise KeyError(f"{path}: no block '{group}'")
        line = re.compile(rf"^(  {key}: *)\S+", flags=re.M)
        new_block, n = line.subn(rf"\g<1>{v:.4g}", block.group(1))
        if n != 1:
            raise KeyError(f"{path}: '{dotted}' found {n} times")
        text = text[: block.start(1)] + new_block + text[block.end(1):]
    path.write_text(text, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/fem.yaml")
    parser.add_argument("--dry-run", action="store_true", help="fem.yaml을 고치지 않고 결과만 출력")
    args = parser.parse_args()

    cfg = load_config(args.config)
    values, freqs = calibrate(cfg)
    for m, f in zip(MODES, freqs):
        t = cfg["calibration"]["target_hz"][m]
        print(f"{m:18s} target {t:6.2f} Hz  model {f:6.2f} Hz  ({(f / t - 1) * 100:+.1f}%)")
    for k, v in values.items():
        print(f"{k} = {v:.4g}")
    if not args.dry_run:
        write_values(Path(args.config), values)
        print(f"updated {args.config}")


if __name__ == "__main__":
    main()
