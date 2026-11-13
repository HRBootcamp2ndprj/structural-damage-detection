# 특징 CSV 형식 (팀 공통 인터페이스)

`data/processed/real_features.csv`, `data/processed/sim_features.csv`는 같은 열을 가진다.
이 형식을 바꾸려면 4명 모두와 합의해야 한다.

| 열 | 타입 | 설명 |
|---|---|---|
| `domain` | str | `real` 또는 `sim` |
| `scenario` | int | 실측 시나리오 번호 0~16. 시뮬은 대응하는 실측 시나리오 번호 |
| `setup` | int | 실측 setup 0~8. 시뮬은 비움 |
| `segment` | int | 실측 구간 0~9. setup 단위 행(10개 구간 연결, 600초)이면 비움. 시뮬은 비움 |
| `group` | str | `healthy` / `settlement` / `local` / `prestress_loss` (`src/data/labels.py`) |
| `f_vertical1`, `f_lateral1`, `f_vertical2`, `f_torsion_lateral2` | float | 고유진동수 [Hz]. 추출에 실패하면 비움 |
| `r_vertical1`, `r_lateral1`, `r_vertical2`, `r_torsion_lateral2` | float | Δf/f₀ = (f − f₀)/f₀, 자기 도메인 기준선 대비 |

- 실측 기준선 f₀는 시나리오 0의 setup 단위 진동수 중앙값이다.
- 시뮬 기준선 f₀는 손상 전 보정 모델의 진동수다.
- 실측 평가의 기본 단위는 setup 단위 행이다(주파수 해상도 우선). 구간 단위 행은 보조로 쓴다.
