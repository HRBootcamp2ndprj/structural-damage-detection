# 대시보드는 Flask + HTML/JS, 파일을 읽어 보여주기만 함

결과 시각화는 Streamlit 대신 Flask(JSON API) + HTML/JS(CDN Chart.js 또는 Plotly.js)로 만든다. 프론트엔드와 백엔드를 직접 구성하는 것이 D의 학습 목표이기 때문이다.

1주 일정에 맞추기 위해 범위를 제한한다.
- DB 없음. `data/processed/*.csv`와 `outputs/<실험명>/` 결과 파일만 읽는다.
- 모델 추론 API는 만들지 않는다.
- 빌드 도구(npm, 번들러)는 쓰지 않는다.

세부 범위는 `app/README.md`에 적었다.
