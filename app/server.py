"""결과 시각화 대시보드 (Flask). 사용법: python app/server.py [--features-dir data/processed]

범위는 app/README.md 참고: DB 없음, 모델 추론 없음, 파일을 읽어 JSON으로 돌려주기만 한다.
"""
import argparse
import json
from pathlib import Path

import pandas as pd
from flask import Flask, abort, jsonify, render_template

ROOT = Path(__file__).resolve().parents[1]
app = Flask(__name__)
app.config["FEATURES_DIR"] = ROOT / "data" / "processed"
app.config["OUTPUTS_DIR"] = ROOT / "outputs"


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/features/<domain>")
def features(domain):
    """특징 CSV(docs/feature_schema.md)를 행 리스트로 반환. domain = real | sim"""
    if domain not in ("real", "sim"):
        abort(404)
    path = Path(app.config["FEATURES_DIR"]) / f"{domain}_features.csv"
    if not path.exists():
        abort(404, f"{path} 없음")
    df = pd.read_csv(path)
    return app.response_class(df.to_json(orient="records"), mimetype="application/json")


@app.get("/api/experiments")
def experiments():
    """outputs/ 아래 metrics.json이 있는 실험 이름 목록."""
    out = Path(app.config["OUTPUTS_DIR"])
    return jsonify(sorted(p.parent.name for p in out.glob("*/metrics.json")))


@app.get("/api/experiments/<name>")
def experiment(name):
    """outputs/<name>/metrics.json 내용 (docs/interfaces.md 형식)."""
    path = Path(app.config["OUTPUTS_DIR"]) / name / "metrics.json"
    if not path.resolve().is_relative_to(Path(app.config["OUTPUTS_DIR"]).resolve()) or not path.exists():
        abort(404)
    return jsonify(json.loads(path.read_text()))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--features-dir", default=str(app.config["FEATURES_DIR"]),
                        help="가짜 데이터로 개발할 때는 data/processed/fake")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()
    app.config["FEATURES_DIR"] = Path(args.features_dir)
    app.run(port=args.port, debug=True)


if __name__ == "__main__":
    main()
