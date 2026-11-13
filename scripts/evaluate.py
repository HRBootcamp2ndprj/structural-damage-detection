"""학습된 분류기를 실측 특징으로 평가 (시나리오 0 제외, 10·11은 따로 보고)"""
import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/train.yaml")
    args = parser.parse_args()
    raise NotImplementedError(f"evaluate: {args.config}")


if __name__ == "__main__":
    main()
