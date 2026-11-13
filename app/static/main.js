// 대시보드 프론트엔드 — 담당: D. API는 app/server.py 참고.

async function getJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url}: ${res.status}`);
  return res.json();
}

async function drawRatioScatter() {
  const [real, sim] = await Promise.all([getJSON("/api/features/real"), getJSON("/api/features/sim")]);
  const realSetup = real.filter((r) => r.segment === null);
  const pts = (rows) => rows.map((r) => ({ x: r.r_vertical1, y: r.r_vertical2 }));
  new Chart(document.getElementById("ratio-scatter"), {
    type: "scatter",
    data: { datasets: [
      { label: "sim", data: pts(sim), pointRadius: 2 },
      { label: "real (setup)", data: pts(realSetup), pointRadius: 4 },
    ] },
    options: { scales: { x: { title: { display: true, text: "r_vertical1" } },
                         y: { title: { display: true, text: "r_vertical2" } } } },
  });
  // TODO(D): 시나리오별 진동수 변화 차트 (scenario-shift)
}

async function loadExperiments() {
  const names = await getJSON("/api/experiments");
  const select = document.getElementById("experiment");
  select.innerHTML = names.map((n) => `<option>${n}</option>`).join("");
  // TODO(D): 선택 시 /api/experiments/<name> → 지표·혼동행렬 표시
}

drawRatioScatter().catch(console.error);
loadExperiments().catch(console.error);
