"""손상 없는 FE 모델을 calibration.target_hz(실측 시나리오 0의 f₀)에 맞추고 configs/fem.yaml 값을 갱신한다."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.features.schema import MODES  # noqa: E402
from src.fem.calibrate import calibrate, write_values  # noqa: E402
from src.fem.model import load_config  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/fem.yaml")
    parser.add_argument("--dry-run", action="store_true", help="fem.yaml을 고치지 않고 결과만 출력")
    args = parser.parse_args()

    cfg = load_config(args.config)
    result = calibrate(cfg)
    for m, f, fam in zip(MODES, result.freqs_hz, result.families):
        t = cfg["calibration"]["target_hz"][m]
        print(f"{m:18s} target {t:6.2f} Hz  model {f:6.2f} Hz  ({(f / t - 1) * 100:+.1f}%)  mode={fam}")
    for k, v in result.values.items():
        print(f"{k} = {v:.4g}")
    print(f"cost = {result.cost:.3e}")
    if not result.modes_ok:
        sys.exit("고른 모드가 MODES 정의(src/fem/modes.py DEFINITION)와 다르다. fem.yaml을 고치지 않는다.")
    if not args.dry_run:
        write_values(Path(args.config), result.values)
        print(f"updated {args.config}")

if __name__ == "__main__":
    main()
