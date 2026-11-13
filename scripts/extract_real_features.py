"""실측 → 전처리(detrend, 글리치 제거) → FDD 진동수 → data/processed/real_features.csv"""
import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/features.yaml")
    args = parser.parse_args()
    raise NotImplementedError(f"extract_real_features: {args.config}")


if __name__ == "__main__":
    main()
