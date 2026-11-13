"""evaluate 진입점. 사용법: python scripts/evaluate.py --config configs/train_baseline.yaml"""
import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/train_baseline.yaml")
    args = parser.parse_args()
    raise NotImplementedError(f"evaluate: {args.config}")


if __name__ == "__main__":
    main()
