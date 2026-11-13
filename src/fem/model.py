"""Z24 3D spine 보 모델 (OpenSees). 단위: N, m, kg, s.

전역 좌표: X = 교축, Y = 횡, Z = 연직. 거더는 Z=0, 교각은 그 아래로 내려간다.
"""
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import openseespy.opensees as ops
import yaml

DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "configs" / "fem.yaml"
N_EIGEN = 12


@dataclass(frozen=True)
class Geometry:
    """거더 요소 배치. 손상 함수는 deck_x_mid로 요소 위치를 찾아 강성 배율 배열을 만든다."""

    deck_x: np.ndarray  # 거더 절점 x 좌표
    pier_x: tuple[float, float]

    @property
    def deck_x_mid(self) -> np.ndarray:
        return 0.5 * (self.deck_x[:-1] + self.deck_x[1:])


def load_config(path=DEFAULT_CONFIG) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def geometry(cfg: dict) -> Geometry:
    spans = cfg["geometry"]["spans_m"]
    per_m = cfg["geometry"]["elements_per_m"]
    edges = np.concatenate([[0.0], np.cumsum(spans)])
    pieces = [np.linspace(a, b, max(1, round((b - a) * per_m)) + 1)[:-1] for a, b in zip(edges[:-1], edges[1:])]
    deck_x = np.concatenate(pieces + [[edges[-1]]])
    return Geometry(deck_x=deck_x, pier_x=(float(edges[1]), float(edges[2])))


def solve(cfg: dict, e_scale: float = 1.0, deck_stiffness: np.ndarray | None = None):
    """고유치 해석. 반환: (진동수 오름차순 (N_EIGEN,), 거더 참여도 (N_EIGEN, 4), Geometry).

    거더 참여도: 모드 운동에너지 중 거더 절점의 ux, uy, uz, rx 몫. 행 합 = 거더 몫 (교각 국부 모드는 작다).

    e_scale: 전역 탄성계수 배율 (환경 변동).
    deck_stiffness: 거더 요소별 휨강성 배율 (len = 거더 요소 수). None이면 전부 1 (손상 없음).
    """
    geo = geometry(cfg)
    n_deck = len(geo.deck_x)
    if deck_stiffness is None:
        deck_stiffness = np.ones(n_deck - 1)
    if len(deck_stiffness) != n_deck - 1:
        raise ValueError(f"deck_stiffness length {len(deck_stiffness)} != {n_deck - 1} deck elements")

    mat, sec, pier, sup = cfg["material"], cfg["section"], cfg["pier"], cfg["supports"]
    E = mat["E"] * e_scale
    G = E / (2 * (1 + mat["nu"]))
    m, r = sec["mass_per_m"], sec["radius_of_gyration_m"]

    ops.wipe()
    ops.model("basic", "-ndm", 3, "-ndf", 6)
    # 거더 국부 y = 전역 Y, 국부 z = 전역 Z → Iy는 연직 휨, Iz는 횡 휨
    ops.geomTransf("Linear", 1, 0.0, 0.0, 1.0)
    # 교각 (Z 방향 부재): 국부 x-z 평면을 전역 X-Z에 둠
    ops.geomTransf("Linear", 2, 1.0, 0.0, 0.0)

    for i, x in enumerate(geo.deck_x):
        ops.node(i + 1, float(x), 0.0, 0.0)
    trib = np.gradient(geo.deck_x) * 1.0
    trib[0], trib[-1] = (geo.deck_x[1] - geo.deck_x[0]) / 2, (geo.deck_x[-1] - geo.deck_x[-2]) / 2
    masses = {}
    for i, L in enumerate(trib):
        mt = m * L
        masses[i + 1] = (mt, mt, mt, mt * r**2, 1e-6 * mt, 1e-6 * mt)

    for e, k in enumerate(deck_stiffness):
        ops.element("elasticBeamColumn", e + 1, e + 1, e + 2, sec["A"], E, G, sec["J"],
                    sec["Iy_vertical"] * k, sec["Iz_lateral"] * k, 1)

    # 교각: 거더와 강결, 기초 고정
    node_id, ele_id = n_deck + 1, n_deck
    n_seg, h = pier["n_elements"], pier["height_m"]
    for px in geo.pier_x:
        top = int(np.argmin(np.abs(geo.deck_x - px))) + 1
        prev = top
        for s in range(1, n_seg + 1):
            ops.node(node_id, px, 0.0, -h * s / n_seg)
            mt = pier["mass_per_m"] * h / n_seg
            masses[node_id] = (mt, mt, mt, 1e-6 * mt, 1e-6 * mt, 1e-6 * mt)
            ele_id += 1
            ops.element("elasticBeamColumn", ele_id, prev, node_id, pier["A"], E, G, pier["J"],
                        pier["Iy"], pier["Iz"], 2)
            prev, node_id = node_id, node_id + 1
        ops.fix(prev, 1, 1, 1, 1, 1, 1)
        masses.pop(prev)
    for n, mm in masses.items():
        ops.mass(n, *mm)

    # 단부: 연직·비틀림 구속, 횡은 스프링, 교축은 자유 (교각이 교축을 잡음)
    ops.uniaxialMaterial("Elastic", 1, sup["abutment_lateral_k"])
    for end in (1, n_deck):
        ground = node_id
        x = float(geo.deck_x[end - 1])
        ops.node(ground, x, 0.0, 0.0)
        ops.fix(ground, 1, 1, 1, 1, 1, 1)
        ops.fix(end, 0, 0, 1, 1, 0, 0)
        ele_id += 1
        ops.element("zeroLength", ele_id, ground, end, "-mat", 1, "-dir", 2)
        node_id += 1

    lam = np.array(ops.eigen(N_EIGEN))
    freqs = np.sqrt(lam) / (2 * np.pi)
    nodes = list(masses)
    M = np.array([masses[n] for n in nodes])
    is_deck = np.array([n <= n_deck for n in nodes])
    part = np.zeros((N_EIGEN, 4))
    for k in range(N_EIGEN):
        v = np.array([ops.nodeEigenvector(n, k + 1) for n in nodes])
        energy = M * v**2
        part[k] = energy[is_deck, :4].sum(axis=0) / energy.sum()
    ops.wipe()
    return freqs, part, geo
