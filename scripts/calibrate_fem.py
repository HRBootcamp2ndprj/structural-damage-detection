"""실측 시나리오 0 진동수에 FE 모델 강성·질량·스프링 보정 → configs/fem.yaml 갱신"""
import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/fem.yaml")
    args = parser.parse_args()
    raise NotImplementedError(f"calibrate_fem: {args.config}")


if __name__ == "__main__":
    main()
