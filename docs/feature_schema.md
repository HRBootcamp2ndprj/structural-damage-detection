# 특징 CSV 형식 (팀 공통 인터페이스)

`data/processed/real_features.csv`(A 생성)와 `data/processed/sim_features.csv`(A 생성)는 같은 열을 가진다.
코드상 정의는 `src/features/schema.py`이고, 읽을 때는 `read_features()`를 쓴다.
이 형식을 바꾸려면 4명 모두와 합의해야 한다. 바꿀 때는 이 문서, `schema.py`, `scripts/make_fake_features.py`, 테스트를 함께 고친다.

## 공통 열

| 열 | 타입 | 설명 |
|---|---|---|
| `domain` | str | `real` 또는 `sim` |
| `scenario` | int | 실측 시나리오 0~16. **시뮬은 비움** (시뮬은 시나리오가 아니라 그룹 + 손상 강도로 정의됨, ADR 0004) |
| `setup` | int | 실측 setup 0~8. 시뮬은 비움 |
| `segment` | int | 실측 구간 0~9. setup 단위 행(10개 구간 연결, 600초)이면 비움. 시뮬은 비움 |
| `group` | str | `healthy` / `settlement` / `local` / `prestress_loss`. 실측 시나리오 1은 비움 (`src/data/labels.py`) |
| `f_vertical1`, `f_lateral1`, `f_vertical2`, `f_torsion_lateral2` | float | 고유진동수 [Hz]. 추출 실패 시 비움 |
| `r_vertical1`, `r_lateral1`, `r_vertical2`, `r_torsion_lateral2` | float | Δf/f₀ = (f − f₀)/f₀, 자기 도메인 기준선 대비 |

## 시뮬 전용 열 (실측 행은 비움)

| 열 | 타입 | 설명 |
|---|---|---|
| `severity` | float | 손상 강도 0~1 연속값. 손상없음은 0 |
| `stiffness_loss` | float | 손상 구간 강성 감소율 0~1. 시뮬 회귀 목표 |
| `env_stiffness` | float | 전역 강성 상대 변동 (온도 대용). 예: −0.01 = −1% |
| `env_noise` | float | 이 행에 더한 진동수 노이즈의 표준편차 (Δf/f₀ 단위) |

## 실측 전용 열 (시뮬 행은 비움)

| 열 | 타입 | 설명 |
|---|---|---|
| `settlement_mm` | int | 침하량. 시나리오 0, 7 → 0. 시나리오 2~5 → 20/40/80/95. 그 외는 비움. **평가 전용**: 학습·튜닝에 쓰지 않는다 |

## 기준선과 노이즈

- 실측 기준선 f₀는 시나리오 0의 setup 단위 행 진동수의 **중앙값**이다(모드별).
- 실측 기준 산포 σ₀는 시나리오 0의 setup 단위 행 Δf/f₀의 표준편차다(모드별). 시뮬 노이즈 크기(`env_noise`)는 σ₀를 기준으로 랜덤화한다.
- 시뮬 기준선 f₀는 손상 전 보정 모델(`run_modal(ModalParams(), None)`)의 진동수다.
- 실측 평가의 기본 단위는 setup 단위 행이다(주파수 해상도 우선). 구간 단위 행은 보조로 쓴다.

## 가짜 데이터

`python scripts/make_fake_features.py`를 실행하면 `data/processed/fake/`에 같은 형식의 CSV가 만들어진다. 진동수 변화량은 가정값이므로 결과 해석에 쓰지 않는다.
