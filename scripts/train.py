"""시뮬 특징(Δf/f₀)으로 손상 유무·그룹 분류기 학습 → outputs/<실험명>/"""
import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/train.yaml")
    args = parser.parse_args()
    raise NotImplementedError(f"train: {args.config}")


if __name__ == "__main__":
    main()
