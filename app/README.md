# 대시보드 (Flask + HTML/JS) — 담당: D

```bash
python app/server.py --features-dir data/processed/fake   # 가짜 데이터로 개발
python app/server.py                                       # 실제 데이터 (data/processed)
```

## 범위 (이 이상 만들지 않는다)

- DB 없음. API는 `data/processed/*.csv`와 `outputs/<실험명>/` 결과 파일을 읽어 JSON으로 반환하는 것까지만 한다.
- 모델 추론 API는 만들지 않는다. 평가 결과 파일을 보여주기만 한다.
- 차트는 Chart.js 또는 Plotly.js를 CDN `<script>`로 불러온다. 빌드 도구(npm, 번들러)는 쓰지 않는다.

## API

| 경로 | 반환 |
|---|---|
| `GET /api/features/<real\|sim>` | 특징 CSV 행 리스트 ([docs/feature_schema.md](../docs/feature_schema.md)) |
| `GET /api/experiments` | `outputs/` 아래 `metrics.json`이 있는 실험 이름 목록 |
| `GET /api/experiments/<name>` | `outputs/<name>/metrics.json` ([docs/interfaces.md](../docs/interfaces.md)) |

## 화면 계획

1. 실측 vs 시뮬 Δf/f₀ 산점도: 도메인 차이가 정규화로 줄어드는지
2. 실측 시나리오별 진동수 변화: 침하 단계별 감소, 시나리오 6 회복
3. 실측 테스트 결과: 지표, 혼동행렬, 비교 실험(절대값 vs Δf/f₀, 4그룹 vs 3그룹, 미시뮬 손상 10·11)
