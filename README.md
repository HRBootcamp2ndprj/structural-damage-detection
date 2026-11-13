# Z24 교량 손상 탐지 — 시뮬레이션 학습, 실측 검증

OpenSees로 Z24 교량(스위스, 3경간 14+30+14m 프리스트레스 콘크리트 박스거더)을 모델링해
손상별 **고유진동수**를 생성하고, 이것만으로 손상 탐지 모델을 학습한 뒤
실측 Z24 상시진동 데이터(KU Leuven PDT)로 검증합니다.

- 계획, 결정 기록, 일정: [docs/project_plan.md](docs/project_plan.md)
- 용어: [CONTEXT.md](CONTEXT.md)
- 설계 결정: [docs/adr/](docs/adr/)

## 과제

1. **손상 유무 판별** (메인)
2. **손상 그룹 분류**: 손상없음 / 침하 / 국부손상 / 프리스트레스 손실. 경미 손상을 합친 3그룹 기준도 함께 보고합니다.

## 파이프라인

```
[시뮬레이터 run_modal] --> [시뮬 진동수] --Δf/f₀--+
                                                  +--> [분류기] --> [평가] --> [대시보드]
[실측 가속도] --전처리+FDD--> [실측 진동수] --Δf/f₀-+
```

- 특징은 각 도메인의 자기 기준선 대비 진동수 변화율 Δf/f₀입니다 (ADR 0001).
  - 실측 기준선 f₀는 시나리오 0의 setup별 진동수 **중앙값**입니다.
  - 실측 기준 산포 σ₀(시나리오 0의 표준편차)는 시뮬 노이즈 크기의 기준입니다.
- 실측 시나리오 0은 FE 보정, f₀, σ₀ 산출에만 쓰고, 나머지는 전부 테스트입니다 (ADR 0002).
  - 손상 모델링과 하이퍼파라미터는 실측 손상 데이터를 보지 않고 정합니다.
- 시뮬 손상 강도는 연속값으로 샘플링하고, 실측 mm에 맞추지 않습니다 (ADR 0004).

## 역할

| 담당 | 범위 | 주요 경로 |
|---|---|---|
| A 데이터 생성/정형 | 실측 전처리·FDD, 시뮬 데이터 생성, 특징 CSV | `src/data`, `src/features`, `src/simgen` |
| B 모델 | 분류기(손상 유무·그룹), 비교 실험 | `src/models`, `src/evaluation`, `scripts/train.py`, `scripts/evaluate.py` |
| C 시뮬레이터 | OpenSees 3D spine 모델, 보정, 손상 함수 | `src/fem`, `scripts/calibrate_fem.py` |
| D 대시보드 | Flask 대시보드(프론트/백엔드), 평가 시각화, 발표 자료 | `app/` |

인터페이스는 [docs/interfaces.md](docs/interfaces.md)를 따릅니다.
- **C → A**: `run_modal(params, damage) → 진동수 벡터` (`src/fem/api.py`). 월요일 11/16에 확정합니다.
- **A → B, D**: 특징 CSV ([docs/feature_schema.md](docs/feature_schema.md))
- **B → D**: `outputs/<실험명>/metrics.json`

## 위험 요소

- A의 실측 FDD는 화요일 11/17까지 끝내야 합니다(C 보정과 B·D 실데이터 연결의 선행 작업). 늦어지면 D가 지원합니다.
- 실측 결과를 보고 튜닝하지 않습니다(ADR 0002).
- 발표에서는 "시뮬 + 실측 손상 전 기준값 1세트" 가정을 명시합니다. 그리고 비교 실험을 보여줍니다: 절대값 vs Δf/f₀, 4그룹 vs 3그룹, 미시뮬 손상 10·11 별도 보고 ([docs/evaluation_protocol.md](docs/evaluation_protocol.md)).

## 디렉토리 구조

```
configs/        설정 (YAML)
  fem.yaml        형상·재료·보정 목표 진동수·손상 함수
  simgen.yaml     손상 강도·환경 변동 샘플링 범위
  features.yaml   전처리·FDD·모드 대역
  train.yaml      분류기 설정
data/           (git 제외, splits/만 커밋)
  raw/z24/        실측 inputs.npy, labels.npy
  sim/            시뮬 중간 결과
  processed/      특징 CSV (fake/ = 가짜 데이터)
  splits/
src/
  data/           실측 로더, 라벨 매핑, 전처리
  fem/            시뮬레이터: OpenSees 모델, 손상 함수, 보정, run_modal
  simgen/         시뮬 데이터 생성: 손상·환경 샘플링 → run_modal 반복 호출
  features/       특징 CSV 형식, FDD 진동수 추출, Δf/f₀ 정규화
  models/         분류기 학습
  evaluation/     지표·혼동행렬
  utils/
scripts/        CLI 진입점
app/            Flask 대시보드 (server.py, templates/, static/)
notebooks/      탐색용 (01_, 02_ 번호)
docs/           계획서, 인터페이스, 평가 프로토콜, ADR
tests/
```

## 실행 순서

```bash
pip install -r requirements.txt
python scripts/make_fake_features.py      # 가짜 특징 CSV → data/processed/fake/ (개발용)
python scripts/download_z24.py            # 실측 데이터 → data/raw/z24/
python scripts/extract_real_features.py   # 실측 → 전처리 → FDD → real_features.csv, f₀·σ₀
python scripts/calibrate_fem.py           # 실측 f₀에 FE 모델 보정
python scripts/generate_sim.py            # run_modal 반복 호출 → sim_features.csv
python scripts/train.py                   # 시뮬로만 학습
python scripts/evaluate.py                # 실측 테스트 → outputs/<실험명>/
python app/server.py                      # 대시보드 (가짜 데이터: --features-dir data/processed/fake)
pytest
```

## 실측 데이터

[thanglexuan/Z24-dataset-processed](https://huggingface.co/datasets/thanglexuan/Z24-dataset-processed)

- `inputs.npy`: (1530, 27, 6000) float32, 100Hz, 구간당 60초. HF README에는 float64로 적혀 있지만 오류입니다.
- `labels.npy`: (1530,), 값 0~16, 클래스당 90개
- 순서: `index = 시나리오*90 + setup*10 + 구간`
- HF README의 "2경간 30m×2"도 오류입니다.
- setup마다 센서 위치가 달라서 채널별 특징은 쓰지 않습니다.

## 규칙

- 노트북은 탐색용입니다. 재사용 로직은 `src/`에 둡니다.
- 실측을 나눌 때는 반드시 setup 단위로 나눕니다. 구간 단위로 나누면 누수가 생깁니다.
- 특징 CSV 형식이나 `run_modal` 시그니처를 바꿀 때는 관련 담당자와 합의하고 문서를 함께 고칩니다.
