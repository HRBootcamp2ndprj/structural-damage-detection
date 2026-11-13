# Z24 교량 손상 탐지 — 시뮬레이션 학습, 실측 검증

OpenSees로 Z24 교량(스위스, 3경간 14+30+14m 프리스트레스 콘크리트 박스거더)을 모델링해
손상 시나리오별 **고유진동수**를 생성하고, 이것만으로 손상 탐지 모델을 학습한 뒤
실측 Z24 상시진동 데이터(KU Leuven PDT)로 검증합니다.

용어는 [CONTEXT.md](CONTEXT.md), 주요 결정은 [docs/adr/](docs/adr/)를 참고하세요.

## 과제

1. **손상 유무 판별** (메인)
2. **손상 그룹 분류**: 침하 / 국부손상 / 프리스트레스 손실

## 파이프라인

```
[FE 모델] --고유치해석--> [시뮬 진동수] --Δf/f₀--+
                                                  +--> [분류기] --> [평가]
[실측 가속도] --전처리+FDD--> [실측 진동수] --Δf/f₀-+
```

- 특징은 각 도메인의 자기 기준선 대비 진동수 변화율 Δf/f₀ (ADR 0001)
- 실측 손상 전 데이터(라벨 0)는 FE 보정과 f₀ 산출에만 쓰고, 나머지는 전부 테스트 (ADR 0002)

## 역할

| 담당 | 범위 | 주요 경로 |
|---|---|---|
| A 데이터 생성/정형 | 실측 전처리·FDD, 시뮬 생성 실행, 특징 CSV | `src/data`, `src/features`, `src/simgen` |
| B 모델 | 분류기(손상 유무·그룹) 학습 | `src/models`, `scripts/train.py` |
| C 시뮬레이터 | OpenSees 3D spine 모델, 보정, 손상 모델링 | `src/fem`, `scripts/calibrate_fem.py` |
| D 시각화 | Streamlit 대시보드, 평가 지표, 발표 자료 | `app/`, `src/evaluation` |

공통 인터페이스는 [docs/feature_schema.md](docs/feature_schema.md)입니다.

## 디렉토리 구조

```
configs/        설정 (YAML)
  fem.yaml        형상·재료·보정 목표 진동수
  simgen.yaml     손상 시나리오·랜덤화 범위
  features.yaml   전처리·FDD·사용할 모드
  train.yaml      분류기 설정
data/           (git 제외, splits/만 커밋)
  raw/z24/        실측 inputs.npy, labels.npy
  sim/            시뮬 생성 결과
  processed/      특징 테이블 (실측·시뮬 공통 형식)
  splits/
src/
  data/           실측 로더, 라벨 매핑, 전처리
  fem/            OpenSees 모델, 손상 모델링, 보정
  simgen/         시나리오 샘플링 → 시뮬 진동수 생성
  features/       FDD 진동수 추출, Δf/f₀ 정규화
  models/         분류기 학습
  evaluation/     지표·혼동행렬
  utils/
scripts/        CLI 진입점 (아래 순서대로 실행)
app/            결과 시각화 대시보드
notebooks/      탐색용 (01_, 02_ 번호)
docs/adr/       설계 결정 기록
tests/
```

## 실행 순서

```bash
pip install -r requirements.txt
python scripts/download_z24.py            # 실측 데이터 → data/raw/z24/
python scripts/extract_real_features.py   # 실측 → 전처리 → FDD → data/processed/real_features.csv
python scripts/calibrate_fem.py           # 라벨 0 진동수에 FE 모델 보정
python scripts/generate_sim.py            # 시뮬 진동수 → data/processed/sim_features.csv
python scripts/train.py                   # 시뮬로만 학습
python scripts/evaluate.py                # 실측 테스트
streamlit run app/dashboard.py
```

## 실측 데이터

[thanglexuan/Z24-dataset-processed](https://huggingface.co/datasets/thanglexuan/Z24-dataset-processed)

- `inputs.npy` (1530, 27, 6000) float32 (README의 float64는 오류), 100Hz, 구간당 60초
- `labels.npy` (1530,) 0~16, 클래스당 90개
- 순서: `index = 시나리오*90 + setup*10 + 구간`
- HF README의 "2경간 30m×2"는 오류입니다.
- setup마다 센서 위치가 달라서 채널별 특징은 쓰지 않습니다.

## 규칙

- 노트북은 탐색용입니다. 재사용 로직은 `src/`에 둡니다.
- 실측과 시뮬은 같은 특징 함수(`src/features`)를 거칩니다.
- 실측을 나눌 때는 반드시 setup 단위로 나눕니다. 구간 단위로 나누면 누수가 생깁니다.
