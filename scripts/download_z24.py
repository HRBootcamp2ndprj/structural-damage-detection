"""실측 Z24 데이터 다운로드. 사용법: python scripts/download_z24.py [--out data/raw/z24]"""
import argparse
import shutil
import urllib.request
from pathlib import Path

BASE = "https://huggingface.co/datasets/thanglexuan/Z24-dataset-processed/resolve/main/"
FILES = {"labels.npy": 12_368, "inputs.npy": 991_440_128}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/raw/z24")
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, size in FILES.items():
        dest = out / name
        if dest.exists() and dest.stat().st_size == size:
            print(f"skip {name} (already downloaded)")
            continue
        print(f"downloading {name} ({size / 1e6:.0f} MB) ...")
        tmp = dest.with_suffix(".part")
        with urllib.request.urlopen(BASE + name) as r, open(tmp, "wb") as f:
            shutil.copyfileobj(r, f, length=1 << 20)
        if tmp.stat().st_size != size:
            raise RuntimeError(f"{name}: size mismatch {tmp.stat().st_size} != {size}")
        tmp.rename(dest)
    print("done:", out)


if __name__ == "__main__":
    main()
