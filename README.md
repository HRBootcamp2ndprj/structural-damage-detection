# Structural Damage Detection

구조물 이미지에서 균열 등 손상을 탐지하는 프로젝트입니다.

## 디렉토리 구조

```
configs/        실험 설정 (YAML)
data/           데이터 (git 제외, splits/만 커밋)
  raw/          원본 데이터
  processed/    전처리 완료 데이터
  splits/       train/val/test 목록
notebooks/      EDA·실험 노트북 (01_, 02_ 번호로 순서 관리)
src/            재사용 코드 (data, models, training, evaluation, utils)
scripts/        CLI 진입점 (prepare_data, train, evaluate, predict)
models/         학습된 가중치 (git 제외)
outputs/        로그·예측 결과 (git 제외)
app/            데모 (Streamlit / FastAPI)
tests/          테스트
docs/           발표 자료, 회의록, 리포트
```

## 시작하기

```bash
pip install -r requirements.txt
python scripts/prepare_data.py
python scripts/train.py --config configs/train_baseline.yaml
```

## 데이터

데이터는 용량 문제로 git에 포함하지 않습니다. 다운로드 위치와 방법: TODO

## 규칙

- 노트북은 탐색용, 재사용 로직은 `src/`로 옮깁니다.
- 하이퍼파라미터는 `configs/`에서 관리하고, 결과는 `outputs/<실험명>/`에 저장합니다.
