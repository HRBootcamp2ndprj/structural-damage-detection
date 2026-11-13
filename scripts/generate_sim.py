"""시나리오 샘플링 + 고유치 해석 → data/processed/sim_features.csv"""
import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/simgen.yaml")
    args = parser.parse_args()
    raise NotImplementedError(f"generate_sim: {args.config}")


if __name__ == "__main__":
    main()
