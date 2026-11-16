# 역할 간 인터페이스

```
C 시뮬레이터 ──run_modal()──> A 시뮬 데이터 생성 ──sim_features.csv──┐
                              A 실측 전처리·FDD ──real_features.csv──┼──> B 모델 ──outputs/<실험>/──> D 대시보드
                                                    (σ₀, f₀) ───> C 보정 ┘                          (특징 CSV도 직접 읽음)
```

## 1. C → A: `run_modal` (월요일 11/16 확정)

`src/fem/api.py`

```python
run_modal(params: ModalParams, damage: Damage | None) -> ModalResult
# ModalParams(env_stiffness=0.0, extra={})
# Damage(group="settlement", severity=0.7, location=0.3)  # severity, location 모두 0~1 연속
# ModalResult(freqs_hz=np.array([...4개, MODES 순서]), stiffness_loss=0.42)
```

- `damage=None`이면 손상 없음이고, 이때의 결과가 시뮬 기준선 f₀다.
- 모드 대응은 C가 책임진다. 진동수 순서가 아니라 모드형상의 지배 자유도로 고른다 (`src/fem/modes.py`). 대응에 실패하면 NaN을 돌려준다.
  - 시뮬의 `torsion_lateral2`는 비틀림 지배 모드다. 실측에서는 비틀림과 횡2가 섞인 모드지만, 시뮬에서 횡2를 고르면 비틀림 강성을 줄이는 국부손상이 이 특징에서 사라진다.
- 호출 1회는 약 4ms다. 직렬로 돌려도 4000회에 20초 안팎이다.
  - 병렬화하려면 프로세스 병렬(`ProcessPoolExecutor`, joblib 기본 백엔드)을 쓴다. OpenSees는 프로세스에 모델이 하나뿐이라 스레드 병렬은 잠금 때문에 빨라지지 않는다.
- 그룹별 손상 함수(어느 구간의 어떤 강성을 얼마나 줄이는지)는 C가 정하고 `configs/fem.yaml`의 `damage` 블록에 기록한다 (ADR 0005).
- `location`은 그룹별 허용 구간 안의 상대 위치·범위다. 생략하면 0.5. A는 severity처럼 U(0, 1)로 샘플링한다. 위치를 하나로 고정하면 분류기가 한 가지 패턴만 외운다.
- `Damage(group="healthy", ...)`는 손상 없음과 같다. `stiffness_loss`는 손상 구간의 최대 연직 휨강성 감소율 = 그룹별 `max_loss` × severity다.

## 2. A → C: 보정 목표값 (화요일 11/17까지)

- 실측 시나리오 0의 모드별 f₀(중앙값)과 σ₀를 `configs/fem.yaml`의 `calibration.target_hz`에 기록한다.
- 그 전까지 C는 문헌값(3.9 / 5.0 / 9.8 / 10.3Hz)으로 작업한다.

## 3. A → B, D: 특징 CSV

[feature_schema.md](feature_schema.md) 참고. 실제 CSV가 나오기 전에는 `data/processed/fake/`를 쓴다.

## 4. B → D: 실험 결과 `outputs/<실험명>/`

| 파일 | 내용 |
|---|---|
| `metrics.json` | 아래 형식 |
| `predictions.csv` | 실측 테스트 행별 예측: `scenario, setup, segment, group, task, y_true, y_pred, score` |

```json
{
  "experiment": "ratio_rf",
  "config": "configs/train.yaml",
  "features": "ratio",
  "tasks": {
    "binary": {"balanced_accuracy": 0.86, "f1": 0.9, "auc": 0.93,
               "labels": ["healthy", "damaged"], "confusion": [[9, 0], [12, 114]]},
    "group4": {"balanced_accuracy": 0.69, "labels": ["healthy", "settlement", "local", "prestress_loss"],
               "confusion": [[...]]},
    "group3": {"balanced_accuracy": 0.8, "labels": ["healthy", "settlement", "minor"], "confusion": [[...]]}
  },
  "unsimulated": {"10": {"detected_rate": 0.7}, "11": {"detected_rate": 0.9}},
  "settlement_rank_corr": 0.95
}
```

D의 대시보드는 이 형식만 보고 그린다. 키를 추가하는 것은 자유지만, 이름 변경이나 삭제는 B와 D가 합의해서 한다.

## 5. D → 브라우저: Flask API

[app/README.md](../app/README.md) 참고.
