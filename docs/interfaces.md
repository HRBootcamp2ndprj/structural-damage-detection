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
# Damage(group="settlement", severity=0.7)          # severity 0~1 연속
# ModalResult(freqs_hz=np.array([...4개, MODES 순서]), stiffness_loss=0.42)
```

- `damage=None`이면 손상 없음이고, 이때의 결과가 시뮬 기준선 f₀다.
- 모드 대응(MAC 또는 모드형상 판별로 연직1/횡1/연직2/비틀림·횡2 찾기)은 C가 책임진다. 대응에 실패하면 NaN을 돌려준다.
- 호출 1회는 1초 이내를 목표로 한다. 시뮬 데이터 생성은 그룹당 수백~수천 회 호출한다.
- 그룹별 손상 함수(어느 구간의 어떤 강성을 얼마나 줄이는지)는 C가 정하고 `configs/fem.yaml`에 기록한다.

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
