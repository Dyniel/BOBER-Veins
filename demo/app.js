// VascuShift pipeline dashboard.
// Reads window.VASCU_PUBLIC (demo/data/public/dashboard_data.js) and, if present, window.VASCU_LOCAL
// (demo/data/local/dashboard_local.js, git-ignored). Both are written by `python -m vascushift.cli pipeline`.
// No measured value is hard-coded here.
"use strict";

const P = window.VASCU_PUBLIC || null;
const L = window.VASCU_LOCAL || null;

const css = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const T = () => ({
  s1: css("--s1"), s2: css("--s2"), s3: css("--s3"), ink: css("--ink"), ink2: css("--ink2"),
  muted: css("--muted"), grid: css("--grid"), axis: css("--axis"), surface: css("--surface"),
  model: css("--model"), internal: css("--internal"),
});
const METHOD = { pos: { label: "POS", c: "s1" }, chrom: { label: "CHROM", c: "s2" }, green: { label: "Green", c: "s3" } };
const ENV = {
  ground: { label: "Ground, 1 G", c: "ink2" },
  parabolic_flight: { label: "Parabolic flight, < 1 G", c: "s2" },
  iss: { label: "ISS, 0 G", c: "s3" },
};
const STUDY = {
  lee2020_partial_gravity: { label: "Lee 2020", style: "circle" },
  marshall_goebel2019_iss_ijv: { label: "Marshall-Goebel 2019", style: "rect" },
  martin2016_parabolic_ijvp: { label: "Martin 2016", style: "rectRot" },
};
const VAR = {
  ijv_area: { label: "IJV cross-sectional area [mm²]", log: true, unit: "mm²" },
  ijv_pressure: { label: "IJV pressure [mmHg]", log: false, unit: "mmHg" },
};

const $ = (id) => document.getElementById(id);
const fmt = (v, d = 1) => (v === null || v === undefined || Number.isNaN(Number(v)) ? "–" : Number(v).toFixed(d));
const sign = (v, d = 1) => (v === null || v === undefined ? "–" : (v > 0 ? "+" : "") + Number(v).toFixed(d));
function alpha(color, a) {
  const c = color.replace("#", "");
  if (c.length !== 6) return color;
  const n = parseInt(c, 16);
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${a})`;
}

// ---------------------------------------------------------------- Chart.js setup
const charts = {};
function chart(id, cfg) {
  if (charts[id]) charts[id].destroy();
  charts[id] = new Chart($(id), cfg);
  return charts[id];
}
// vertical whiskers for datasets with `whiskers: true` and points {x, y, lo, hi}
const whiskerPlugin = {
  id: "whiskers",
  afterDatasetsDraw(c) {
    const { ctx } = c;
    c.data.datasets.forEach((ds, i) => {
      if (!ds.whiskers || !c.isDatasetVisible(i)) return;
      const meta = c.getDatasetMeta(i);
      const ys = c.scales[ds.yAxisID || "y"];
      ctx.save();
      ctx.strokeStyle = ds.whiskerColor || ds.borderColor;
      ctx.lineWidth = 2;
      ds.data.forEach((p, j) => {
        if (p == null || p.lo == null || p.hi == null) return;
        const el = meta.data[j];
        if (!el) return;
        const lo = ys.type === "logarithmic" ? Math.max(p.lo, ys.min || 1) : p.lo;
        ctx.beginPath();
        ctx.moveTo(el.x, ys.getPixelForValue(lo));
        ctx.lineTo(el.x, ys.getPixelForValue(p.hi));
        ctx.stroke();
      });
      ctx.restore();
    });
  },
};
function baseOptions(extra = {}) {
  const t = T();
  Chart.defaults.color = t.ink2;
  Chart.defaults.font.family = 'system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif';
  Chart.defaults.font.size = 12;
  return Object.assign({
    responsive: true, maintainAspectRatio: false, animation: false,
    interaction: { mode: "nearest", intersect: false },
    plugins: {
      legend: { position: "bottom", labels: { usePointStyle: true, boxWidth: 8, boxHeight: 8, color: t.ink2 } },
      tooltip: { backgroundColor: t.surface, titleColor: t.ink, bodyColor: t.ink2, borderColor: t.axis, borderWidth: 1 },
    },
  }, extra);
}
function axis(title, extra = {}) {
  const t = T();
  return Object.assign({
    title: { display: !!title, text: title, color: t.ink2 },
    grid: { color: t.grid, drawTicks: false }, border: { color: t.axis }, ticks: { color: t.ink2, padding: 6 },
  }, extra);
}
const gzTicks = { min: -0.8, max: 1.1, ticks: { stepSize: 0.05, autoSkip: false, callback: (v) => (Math.abs(v * 4 - Math.round(v * 4)) < 1e-6 ? v : null) } };
const logTicks = { callback: (v) => ([2, 5, 10, 20, 50, 100, 200, 400].includes(v) ? v : null) };

// ---------------------------------------------------------------- header + overview
function renderHeader() {
  const n = P.rppg.sessions.length;
  const pills = [
    ["real", "REAL", `Optical layer · UBFC-rPPG · ${n} recordings`],
    ["real", "REAL", "Physiology layer · tilt (n = 12) + PRCP (n = 10)"],
    ["pub", "PUBLISHED", "Partial gravity + ISS · group means"],
    ["model", "MODEL", "Bridge · compartment model, not validated end-to-end"],
  ];
  $("layer-pills").innerHTML = pills
    .map(([cls, b, txt]) => `<div class="pill"><span class="badge ${cls}">${b}</span>${txt}</div>`).join("");
  $("footer").innerHTML =
    `Generated ${P.generated_utc} · commit ${(P.git_commit || "unknown").slice(0, 10)} · ` +
    `local bundle ${L ? "loaded (waveforms + internal data)" : "not present (public metrics only)"} · ${P.rule}`;
}

function kpi(label, value, unit, sub, badge) {
  return `<div class="kpi"><span class="label">${label}</span>` +
    `<span class="value">${value}<span class="unit">${unit || ""}</span></span>` +
    `<span class="sub">${sub}</span><span><span class="badge ${badge[0]}">${badge[1]}</span></span></div>`;
}

function renderKpis() {
  const s = P.rppg.summary.find((r) => r.subset === "DATASET_2" && r.protocol === "w10s2" && r.method === "pos");
  const slope = P.physiology.tilt_slopes.find((r) => r.variable === "ijv_area" && r.family === "supine" && !r.plausible_only);
  const ratio = P.physiology.paired_ratios.find((r) => r.variable === "ijv_area" && r.a === "supine_tilt_-45");
  const hr = P.physiology.paired_ratios.find((r) => r.variable === "heart_rate" && r.a === "hut75");
  const an = P.physiology.literature_anchors;
  const iss = an.find((r) => r.condition === "iss_fd50" && r.base === "ijv_area");
  const sup = an.find((r) => r.condition === "preflight_supine" && r.base === "ijv_area");
  const html = [];
  if (s) html.push(kpi("Heart rate from face video · POS error", fmt(s.mae_bpm, 2), " bpm",
    `MAE, 10 s windows · 95 % CI ${fmt(s.mae_ci_low, 2)}–${fmt(s.mae_ci_high, 2)} · ${s.n_sessions} people, ${s.n_windows} windows`, ["real", "REAL"]));
  if (s) html.push(kpi("Windows within ±5 bpm of the finger sensor", fmt(s.acc_within_5bpm_pct, 1), " %",
    `UBFC-rPPG DATASET 2 · POS · bias ${sign(s.bias_bpm, 2)} bpm`, ["real", "REAL"]));
  if (slope) html.push(kpi("Jugular vein area per +0.5 g head-to-foot", sign(slope.pct_change_per_0p5g, 0), " %",
    `supine tilt · 95 % CI ${fmt(slope.pct_ci_low, 0)} to ${fmt(slope.pct_ci_high, 0)} % · ${Math.round(slope.fraction_negative * 100)} % of ${slope.n_subjects} people decrease`, ["real", "REAL"]));
  if (ratio) html.push(kpi("Area 45° head-down vs 45° head-up", fmt(ratio.median_ratio, 1), "×",
    `within-person ratio · 95 % CI ${fmt(ratio.ci_low, 1)}–${fmt(ratio.ci_high, 1)} · n = ${ratio.n_subjects}`, ["real", "REAL"]));
  if (hr) html.push(kpi("Heart rate at 75° head-up tilt vs supine", sign((hr.median_ratio - 1) * 100, 0), " %",
    `PhysioNet PRCP · 95 % CI ${sign((hr.ci_low - 1) * 100, 0)} to ${sign((hr.ci_high - 1) * 100, 0)} % · n = ${hr.n_subjects}`, ["real", "REAL"]));
  if (iss && sup) html.push(kpi("0 G is not lying down · IJV area", `${fmt(iss.value, 0)} vs ${fmt(sup.value, 0)}`, " mm²",
    `ISS flight day 50 vs pre-flight supine, same crew (Marshall-Goebel 2019)`, ["pub", "PUBLISHED"]));
  $("kpis").innerHTML = html.join("");
}

// ---------------------------------------------------------------- optical
function renderOptical() {
  const t = T();
  const subset = $("f-subset").value;
  const proto = $("f-protocol").value;
  $("rppg-protocol").textContent = P.rppg.protocol;
  const rows = ["pos", "chrom", "green"]
    .map((m) => P.rppg.summary.find((r) => r.subset === subset && r.protocol === proto && r.method === m))
    .filter(Boolean);
  chart("c-mae", {
    type: "bar",
    data: {
      labels: rows.map((r) => METHOD[r.method].label),
      datasets: [{
        label: "MAE [bpm]", data: rows.map((r) => r.mae_bpm),
        backgroundColor: rows.map((r) => t[METHOD[r.method].c]), borderRadius: 4, borderSkipped: "start",
        maxBarThickness: 24, borderWidth: 0,
      }, {
        type: "scatter", label: "95 % CI", whiskers: true, whiskerColor: t.ink2, pointRadius: 0,
        data: rows.map((r, i) => ({ x: i, y: r.mae_bpm, lo: r.mae_ci_low, hi: r.mae_ci_high })),
      }],
    },
    options: baseOptions({
      indexAxis: "x",
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: (c) => { const r = rows[c.dataIndex]; return `MAE ${fmt(r.mae_bpm, 2)} bpm (95 % CI ${fmt(r.mae_ci_low, 2)}–${fmt(r.mae_ci_high, 2)})`; } } },
      },
      scales: { x: axis(""), y: axis("Mean absolute error [bpm]", { beginAtZero: true }) },
    }),
    plugins: [whiskerPlugin],
  });
  const head = "<tr><th>Method</th><th class='num'>MAE (95 % CI)</th><th class='num'>RMSE</th><th class='num'>r</th><th class='num'>Bias [LoA]</th><th class='num'>±5 bpm</th><th class='num'>Windows</th></tr>";
  $("t-methods").innerHTML = head + rows.map((r) =>
    `<tr><td><span class="swatch" style="background:${t[METHOD[r.method].c]}"></span>${METHOD[r.method].label}</td>` +
    `<td class="num">${fmt(r.mae_bpm, 2)} (${fmt(r.mae_ci_low, 2)}–${fmt(r.mae_ci_high, 2)})</td>` +
    `<td class="num">${fmt(r.rmse_bpm, 2)}</td><td class="num">${fmt(r.pearson_r, 3)}</td>` +
    `<td class="num">${sign(r.bias_bpm, 2)} [${sign(r.loa_low_bpm, 1)}, ${sign(r.loa_high_bpm, 1)}]</td>` +
    `<td class="num">${fmt(r.acc_within_5bpm_pct, 1)} %</td><td class="num">${r.n_windows}${r.n_excluded ? ` (−${r.n_excluded})` : ""}</td></tr>`).join("");
  fillSessions(subset);
  renderAllSessions();
}

function renderAllSessions() {
  const t = T();
  const clip = (v) => (v === null || v === undefined ? null : Math.max(-30, Math.min(30, v)));
  const ds = ["pos", "chrom", "green"].map((m) => ({
    label: METHOD[m].label,
    data: P.rppg.sessions.filter((s) => s.whole_error_bpm && s.whole_error_bpm[m] !== null && s.whole_error_bpm[m] !== undefined)
      .map((s) => ({ x: s.ref_hr_bpm, y: clip(s.whole_error_bpm[m]), raw: s.whole_error_bpm[m], id: s.session_id, subset: s.subset })),
    borderColor: t.surface, backgroundColor: t[METHOD[m].c], pointRadius: 5, pointHoverRadius: 8, pointBorderWidth: 1.5,
    pointStyle: m === "pos" ? "circle" : (m === "chrom" ? "rect" : "triangle"), hidden: m === "green",
  }));
  chart("c-all-sessions", {
    type: "scatter", data: { datasets: ds },
    options: baseOptions({
      interaction: { mode: "nearest", intersect: true },
      onClick: (evt, els, c) => {
        if (!els.length) return;
        const pt = c.data.datasets[els[0].datasetIndex].data[els[0].index];
        if ($("f-subset").value !== pt.subset) { $("f-subset").value = pt.subset; renderOptical(); }
        $("f-session").value = pt.id; renderSession();
        $("session-card").scrollIntoView({ behavior: "smooth", block: "start" });
      },
      plugins: { ...baseOptions().plugins, tooltip: { ...baseOptions().plugins.tooltip, callbacks: {
        label: (c) => `${c.raw.id.replace("ubfc-", "")} · ${c.dataset.label} ${sign(c.raw.raw, 1)} bpm (ref ${fmt(c.raw.x, 0)} bpm)` } } },
      scales: { x: axis("Reference heart rate of the recording [bpm]"), y: axis("rPPG − reference [bpm]", { min: -32, max: 32 }) },
    }),
  });
}

function fillSessions(subset) {
  const sel = $("f-session");
  const prev = sel.value;
  const ss = P.rppg.sessions.filter((s) => s.subset === subset);
  sel.innerHTML = ss.map((s) => {
    const e = s.whole_error_bpm && s.whole_error_bpm.pos;
    return `<option value="${s.session_id}">${s.session_id.replace("ubfc-", "")} · ref ${fmt(s.ref_hr_bpm, 0)} bpm · POS ${sign(e, 1)}</option>`;
  }).join("");
  const want = new URLSearchParams(location.search).get("session");
  if (!prev && want && ss.some((s) => s.session_id === want)) sel.value = want;
  else if (ss.some((s) => s.session_id === prev)) sel.value = prev;
  renderSession();
}

function renderSession() {
  const t = T();
  const s = P.rppg.sessions.find((x) => x.session_id === $("f-session").value);
  if (!s) return;
  $("session-meta").innerHTML = [
    ["Recording", `${fmt(s.duration_s, 0)} s`], ["Mean frame rate", `${fmt(s.fps_video_mean, 2)} fps`],
    ["Longest frame gap", `${fmt(s.max_frame_step_s, 2)} s`], ["Measured samples", `${fmt(s.fraction_valid * 100, 1)} %`],
    ["Reference HR", `${fmt(s.ref_hr_bpm, 1)} bpm`],
    ["Whole-recording error", ["pos", "chrom", "green"].map((m) => `${METHOD[m].label} ${sign(s.whole_error_bpm[m], 1)}`).join(" · ")],
  ].map(([k, v]) => `<span>${k}: <b>${v}</b></span>`).join("") + (s.no_face_display ? `<span class="badge local">no face images allowed</span>` : "");
  const w = s.w10s2;
  const pts = (arr) => w.t_mid_s.map((x, i) => ({ x, y: w.included[i] ? arr[i] : null }));
  const ds = [{ label: "Finger PPG (reference)", data: pts(w.hr_ref), borderColor: t.ink, backgroundColor: t.ink, borderWidth: 2, pointRadius: 0, showLine: true }];
  ["pos", "chrom", "green"].forEach((m) => {
    if (w[`hr_${m}`]) ds.push({ label: METHOD[m].label, data: pts(w[`hr_${m}`]), borderColor: t[METHOD[m].c], backgroundColor: t[METHOD[m].c], borderWidth: 2, pointRadius: 0, showLine: true, hidden: m === "green" });
  });
  const wi = s.w10s2_improved;
  if (wi && wi.hr && wi.hr.length) {
    ds.push({ label: "Improved POS (experimental, tracked)", data: wi.t_mid_s.map((x, i) => ({ x, y: wi.included[i] ? wi.hr[i] : null })),
      borderColor: t.model, backgroundColor: t.model, borderWidth: 2.5, borderDash: [6, 3], pointRadius: 0, showLine: true, order: -1 });
    ds.push({ label: "low confidence (abstain)", data: wi.t_mid_s.map((x, i) => (wi.included[i] && wi.abstain[i] ? { x, y: wi.hr[i] } : null)).filter(Boolean),
      borderColor: t.model, backgroundColor: t.surface, borderWidth: 1.5, pointRadius: 3.5, showLine: false, order: -2 });
  }
  chart("c-session-hr", {
    type: "scatter", data: { datasets: ds },
    options: baseOptions({
      interaction: { mode: "index", intersect: false },
      plugins: { ...baseOptions().plugins, tooltip: { ...baseOptions().plugins.tooltip, callbacks: { label: (c) => `${c.dataset.label}: ${fmt(c.parsed.y, 1)} bpm` } } },
      scales: { x: axis("Window centre [s]"), y: axis("Heart rate [bpm]") },
    }),
  });
  const wf = L && L.waveforms ? L.waveforms[s.session_id] : null;
  if (!wf) {
    if (charts["c-wave"]) { charts["c-wave"].destroy(); delete charts["c-wave"]; }
    $("wave-note").textContent = "Waveforms are not part of the public bundle (UBFC dataset agreement). Run the pipeline locally to see them.";
    return;
  }
  $("wave-note").textContent = "z-scored; reference = finger PPG band-passed with the same 0.7–3.5 Hz filter as the rPPG signal.";
  const xs = wf.ref.map((_, i) => wf.t0_s + i / wf.fs);
  chart("c-wave", {
    type: "scatter",
    data: { datasets: [
      { label: "Finger PPG", data: xs.map((x, i) => ({ x, y: wf.ref[i] })), borderColor: t.ink, borderWidth: 1.5, pointRadius: 0, showLine: true },
      { label: "POS (face video)", data: xs.map((x, i) => ({ x, y: wf.pos[i] })), borderColor: t.s1, borderWidth: 1.5, pointRadius: 0, showLine: true },
    ] },
    options: baseOptions({ interaction: { mode: "nearest", intersect: false }, plugins: { ...baseOptions().plugins, tooltip: { enabled: false } },
      scales: { x: axis("Time in recording [s]"), y: axis("z-score") } }),
  });
}

// ---------------------------------------------------------------- physiology
function condRows(dataset, variable, family) {
  return P.physiology.condition_stats
    .filter((r) => r.dataset === dataset && r.variable === variable && r.family === family && !r.lbnp_mmHg)
    .sort((a, b) => a.gz_body - b.gz_body);
}
function bandDatasets(rows, color, label, dash, style = "circle") {
  return [
    { label: `${label} Q1`, data: rows.map((r) => ({ x: r.gz_body, y: r.q1 })), borderWidth: 0, pointRadius: 0, showLine: true, fill: false, legendHide: true },
    { label: `${label} Q3`, data: rows.map((r) => ({ x: r.gz_body, y: r.q3 })), borderWidth: 0, pointRadius: 0, showLine: true, fill: "-1", backgroundColor: alpha(color, 0.10), legendHide: true },
    { label: `${label}, median`, data: rows.map((r) => ({ x: r.gz_body, y: r.median, n: r.n_subjects, q1: r.q1, q3: r.q3 })), borderColor: color, backgroundColor: color, borderWidth: 2, borderDash: dash, pointStyle: style, pointRadius: style === "circle" ? 4 : 5, pointBorderColor: T().surface, pointBorderWidth: 2, showLine: true },
  ];
}
function physScales(v) {
  const y = VAR[v].log ? axis(VAR[v].label, { type: "logarithmic", min: 2, max: 400, ticks: { ...logTicks, color: T().ink2 } }) : axis(VAR[v].label, { min: 0 });
  return { x: axis("gz_body [g]  (− head-down · + head-up)", gzTicks), y };
}
const hideBand = { labels: { usePointStyle: true, boxWidth: 8, filter: (item, data) => !data.datasets[item.datasetIndex].legendHide } };

function renderPhysiology() {
  const t = T();
  const v = $("f-var").value;
  const sup = condRows("bhp_carotid_jugular", v, "supine");
  const pro = condRows("bhp_carotid_jugular", v, "prone");
  const seated = condRows("bhp_carotid_jugular", v, "seated")[0];
  const ds = [...bandDatasets(sup, t.s1, "Supine tilt", []), ...bandDatasets(pro, t.s1, "Prone tilt", [6, 4], "rectRot")];
  if (seated) ds.push({ label: `Seated, median (n = ${seated.n_subjects})`, data: [{ x: seated.gz_body, y: seated.median, lo: seated.q1, hi: seated.q3, n: seated.n_subjects }], borderColor: t.s1, backgroundColor: t.surface, pointRadius: 6, pointBorderWidth: 2, whiskers: true });
  chart("c-tilt", {
    type: "scatter", data: { datasets: ds },
    options: baseOptions({
      plugins: { legend: { position: "bottom", ...hideBand }, tooltip: { ...baseOptions().plugins.tooltip, filter: (i) => !i.dataset.legendHide,
        callbacks: { label: (c) => { const p = c.raw; return `${c.dataset.label}: ${fmt(p.y, 1)} ${VAR[v].unit} (IQR ${fmt(p.q1 ?? p.lo, 1)}–${fmt(p.q3 ?? p.hi, 1)}, n = ${p.n})`; } } } },
      scales: physScales(v),
    }),
    plugins: [whiskerPlugin],
  });

  // published anchors: colour = environment, marker = study
  const an = P.physiology.literature_anchors.filter((r) => r.base === v && !r.lbnp_mmHg && r.value !== null);
  const envOf = (r) => (String(r.environment).startsWith("iss") ? "iss" : (r.environment === "parabolic_flight" && r.gz_platform < 1 ? "parabolic_flight" : "ground"));
  const jit = { lee2020_partial_gravity: -0.02, marshall_goebel2019_iss_ijv: 0.02, martin2016_parabolic_ijvp: 0 };
  const groups = {};
  an.forEach((r) => {
    const key = `${envOf(r)}|${r.dataset}`;
    (groups[key] = groups[key] || []).push(r);
  });
  const ads = Object.entries(groups).map(([key, rows]) => {
    const [env, study] = key.split("|");
    const col = t[ENV[env].c];
    return {
      label: `${ENV[env].label} · ${STUDY[study] ? STUDY[study].label : study}`,
      data: rows.map((r) => {
        const lo = r.stat === "mean_sd" ? r.value - r.sd : r.ci_low;
        const hi = r.stat === "mean_sd" ? r.value + r.sd : r.ci_high;
        return { x: r.gz_body + (jit[r.dataset] || 0) + (r.condition === "iss_fd150" ? 0.035 : 0), y: r.value, lo, hi, cond: r.condition, stat: r.stat, n: r.n };
      }),
      borderColor: col, backgroundColor: col, pointStyle: STUDY[study] ? STUDY[study].style : "circle",
      pointRadius: 6, pointBorderColor: t.surface, pointBorderWidth: 2, whiskers: true, whiskerColor: col,
    };
  });
  chart("c-anchors", {
    type: "scatter", data: { datasets: ads },
    options: baseOptions({
      plugins: { ...baseOptions().plugins, tooltip: { ...baseOptions().plugins.tooltip, callbacks: { label: (c) => {
        const p = c.raw; const what = p.stat === "mean_sd" ? "±SD" : "95 % CI";
        return `${p.cond}: ${fmt(p.y, 1)} ${VAR[v].unit} (${what} ${fmt(p.lo, 1)}–${fmt(p.hi, 1)}${p.n ? `, n = ${p.n}` : ""})`;
      } } } },
      scales: physScales(v),
    }),
    plugins: [whiskerPlugin],
  });

  // slopes table
  const sl = P.physiology.tilt_slopes.filter((r) => !r.plausible_only);
  $("t-slopes").innerHTML = "<tr><th>Variable</th><th>Posture</th><th class='num'>n</th><th class='num'>Median slope per g (95 % CI)</th><th class='num'>Change per +0.5 g</th></tr>" +
    sl.map((r) => `<tr><td>${r.variable.replace("_", " ")}</td><td>${r.family}</td><td class="num">${r.n_subjects}</td>` +
      `<td class="num">${fmt(r.median_slope, 2)} (${fmt(r.ci_low, 2)} … ${fmt(r.ci_high, 2)})${r.scale === "ln" ? " ln-units" : " mmHg"}</td>` +
      `<td class="num">${r.pct_change_per_0p5g !== null && r.pct_change_per_0p5g !== undefined ? sign(r.pct_change_per_0p5g, 0) + " %" : sign(r.median_slope / 2, 1) + " mmHg"}</td></tr>`).join("");

  // table views (accessibility: every chart value is also readable as text)
  const unit = VAR[v].unit;
  $("t-tilt").innerHTML = "<tr><th>Condition</th><th class='num'>gz_body</th><th class='num'>n</th><th class='num'>Median</th><th class='num'>IQR</th><th class='num'>Flagged</th></tr>" +
    [...sup, ...pro, ...(seated ? [seated] : [])].map((r) => `<tr><td>${r.condition}</td><td class="num">${fmt(r.gz_body, 2)}</td><td class="num">${r.n_subjects}</td>` +
      `<td class="num">${fmt(r.median, 1)} ${unit}</td><td class="num">${fmt(r.q1, 1)}–${fmt(r.q3, 1)}</td><td class="num">${r.n_implausible || 0}</td></tr>`).join("");
  $("t-anchors").innerHTML = "<tr><th>Study · condition</th><th class='num'>gz_body</th><th class='num'>Value</th><th class='num'>Interval</th><th class='num'>n</th></tr>" +
    an.map((r) => {
      const lo = r.stat === "mean_sd" ? r.value - r.sd : r.ci_low; const hi = r.stat === "mean_sd" ? r.value + r.sd : r.ci_high;
      return `<tr><td>${STUDY[r.dataset] ? STUDY[r.dataset].label : r.dataset} · ${r.condition}</td><td class="num">${fmt(r.gz_body, 2)}</td>` +
        `<td class="num">${fmt(r.value, 1)} ${unit}</td><td class="num">${fmt(lo, 1)}–${fmt(hi, 1)} (${r.stat === "mean_sd" ? "±SD" : "95 % CI"})</td><td class="num">${r.n ?? ""}</td></tr>`;
    }).join("");

  renderPrcp();
  renderInternal();
}

function renderImproved() {
  const I = P.rppg_improved;
  const card = $("improved-card");
  if (!I || !I.available) { card.classList.add("hidden"); return; }
  card.classList.remove("hidden");
  const c = I.config || {};
  $("improved-note").textContent = `ROI: face box interpolated between detections, whole box with skin mask · pulse: ${String(c.method || "").toUpperCase()} · ` +
    `HR: Viterbi tracking (σ ${c.sigma_bpm} bpm per step) · abstain below quality ${I.abstain_quality_threshold}. The frozen baseline above is unchanged.`;
  const label = { "split=holdout": "Held-out half (29 recordings)", "holdout,subset=DATASET_2": "Held-out · DATASET 2 (21 people)",
    "holdout,subset=DATASET_1": "Held-out · DATASET 1 (8 recordings)", "split=tune": "Tuning half (21 people)" };
  const base = Object.fromEntries((I.baseline_pos_summary || []).map((r) => [r.group, r]));
  const rows = (I.summary || []).filter((r) => label[r.group]).sort((a, b) => Object.keys(label).indexOf(a.group) - Object.keys(label).indexOf(b.group));
  $("t-improved").innerHTML = "<tr><th>Group</th><th class='num'>Baseline MAE</th><th class='num'>Improved MAE</th><th class='num'>+ abstain MAE</th>" +
    "<th class='num'>Kept</th><th class='num'>> 10 bpm: base → impr. → abst.</th></tr>" +
    rows.map((r) => { const b0 = base[r.group] || {};
      return `<tr><td>${label[r.group]}</td><td class="num">${fmt(b0.mae_bpm, 2)}</td><td class="num"><b>${fmt(r.mae_bpm, 2)}</b></td>` +
        `<td class="num">${fmt(r.abstain_mae_bpm, 2)}</td><td class="num">${fmt(r.abstain_kept_pct, 0)} %</td>` +
        `<td class="num">${fmt(b0.gross10_pct, 1)} → ${fmt(r.gross10_pct, 1)} → ${fmt(r.abstain_gross10_pct, 1)} %</td></tr>`; }).join("");
}

function renderPipeline() {
  const q = P.pipeline || {};
  const st = q.stages_seconds || {};
  const h = q.hreda_headward_fluid_shift;
  $("pipeline-card").innerHTML =
    `<strong>Reproduce:</strong> <code>${q.command || "python -m vascushift.cli pipeline"}</code> · commit ` +
    `<code>${(q.git_commit || P.git_commit || "unknown").slice(0, 10)}</code>${q.git_dirty ? " (uncommitted changes)" : ""} · generated ${P.generated_utc}` +
    (h ? ` · ESA HREDA HeadwardFluidShift: <b>${h.data_available ? "DATA AVAILABLE" : "no data released"}</b> (${h.n_files} files, checked live)` : "") +
    `<div class="stage-row">${Object.entries(st).map(([k, v]) => `<span class="stage">${k} ${fmt(v, 1)} s</span>`).join("")}</div>`;
}

function renderQuality() {
  const Q = P.quality;
  if (!Q) return;
  const u = Q.ubfc;
  const ex = (u.excluded_windows || []).filter((r) => r.n_excluded).map((r) => `${r.subset.replace("DATASET_", "D")} ${r.protocol}: ${r.n_excluded}`).join(", ") || "none";
  $("q-ubfc").innerHTML = [
    `Frame rate is not constant: DATASET 2 recordings run at <b>${fmt(u.fps_min, 1)}–${fmt(u.fps_max, 1)} fps</b>; the pipeline uses the real per-frame clock and resamples to 30 Hz.`,
    `<b>${u.sessions_with_frame_holes_over_0p25s}</b> of ${u.n_sessions} recordings drop frames for more than 0.25 s (longest <b>${fmt(u.longest_frame_hole_s, 2)} s</b>); those samples are marked invalid.`,
    `Windows excluded because &lt; 90 % of samples are measured: <b>${ex}</b>.`,
    `Finger-sensor HR column has dropouts in <b>${u.sessions_with_sensor_hr_dropouts}</b> recordings → reference HR is computed from the PPG waveform instead.`,
    `Faces may never be shown for: <b>${(u.no_face_display_sessions || []).join(", ") || "–"}</b> (this page shows signals only).`,
  ].map((x) => `<li>${x}</li>`).join("");
  const ph = Q.physiology;
  const fl = (ph.flagged_conditions || []).map((r) => `${r.variable} ${r.condition}: ${r.n_implausible}/${r.n_subjects}`).join("; ");
  $("q-phys").innerHTML = [
    `<b>${ph.n_implausible_values ?? "–"}</b> implausible values flagged in the public tables${fl ? ` (${fl})` : ""}; medians are robust to them and slopes are also reported without them.`,
    ...(ph.notes || []),
  ].map((x) => `<li>${x}</li>`).join("");
}

function initTheme() {
  let saved = null;
  try { saved = localStorage.getItem("vascu-theme"); } catch (e) { saved = null; }
  if (saved === "light" || saved === "dark") document.documentElement.setAttribute("data-theme", saved);
  $("theme-toggle").addEventListener("click", () => {
    const cur = document.documentElement.getAttribute("data-theme") ||
      (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    const next = cur === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    try { localStorage.setItem("vascu-theme", next); } catch (e) { /* storage blocked: theme still switches */ }
    renderAll();
  });
}

function renderPrcp() {
  const t = T();
  const order = ["supine", "hut75", "standing"];
  const rows = P.physiology.prcp_subjects.filter((r) => r.variable === "heart_rate");
  const subs = [...new Set(rows.map((r) => r.subject_id))];
  const ds = subs.map((s) => ({
    label: s, data: order.map((c, i) => { const r = rows.find((x) => x.subject_id === s && x.condition === c); return r ? { x: i, y: r.value } : null; }),
    borderColor: t.grid, borderWidth: 1.2, pointRadius: 0, showLine: true, legendHide: true,
  }));
  const med = order.map((c, i) => { const v = rows.filter((r) => r.condition === c).map((r) => r.value).sort((a, b) => a - b); const m = v.length % 2 ? v[(v.length - 1) / 2] : (v[v.length / 2 - 1] + v[v.length / 2]) / 2; return { x: i, y: m }; });
  ds.push({ label: "Median", data: med, borderColor: t.s1, backgroundColor: t.s1, borderWidth: 2, pointRadius: 5, pointBorderColor: t.surface, pointBorderWidth: 2, showLine: true });
  chart("c-prcp", {
    type: "scatter", data: { datasets: ds },
    options: baseOptions({
      plugins: { legend: { display: false }, tooltip: { ...baseOptions().plugins.tooltip, filter: (i) => !i.dataset.legendHide, callbacks: { label: (c) => `median ${fmt(c.parsed.y, 1)} bpm` } } },
      scales: { x: axis("", { min: -0.2, max: 2.2, ticks: { stepSize: 1, callback: (v) => ["Supine", "75° tilt", "Standing"][v] ?? "" } }), y: axis("Heart rate [bpm]") },
    }),
  });
}

function renderInternal() {
  const card = $("internal-card");
  const I = L && L.physiology_internal;
  if (!I) { card.classList.add("hidden"); return; }
  card.classList.remove("hidden");
  const t = T();
  const lb = I.condition_stats.filter((r) => r.dataset === "bhp_lbnp_dose_response" && r.variable === "ijv_area");
  const series = (pref) => lb.filter((r) => r.condition.startsWith(pref + "_lbnp")).sort((a, b) => b.lbnp_mmHg - a.lbnp_mmHg)
    .map((r) => ({ x: -r.lbnp_mmHg, y: r.median, q1: r.q1, q3: r.q3, n: r.n_subjects }));
  chart("c-lbnp", {
    type: "scatter",
    data: { datasets: [
      { label: "Supine", data: series("supine"), borderColor: t.s1, backgroundColor: t.s1, borderWidth: 2, pointRadius: 4, showLine: true },
      { label: "15° head-down", data: series("hdt15"), borderColor: t.s1, backgroundColor: t.s1, borderWidth: 2, borderDash: [6, 4], pointStyle: "rectRot", pointRadius: 5, showLine: true },
    ] },
    options: baseOptions({ plugins: { ...baseOptions().plugins, tooltip: { ...baseOptions().plugins.tooltip, callbacks: { label: (c) => `${c.dataset.label}: ${fmt(c.raw.y, 1)} mm² (IQR ${fmt(c.raw.q1, 1)}–${fmt(c.raw.q3, 1)}, n = ${c.raw.n})` } } },
      scales: { x: axis("Lower-body negative pressure [−mmHg]"), y: axis("IJV area [mm²], median", { min: 0 }) } }),
  });
  const iop = I.condition_stats.filter((r) => r.dataset === "bhp_tilt_dose_response" && r.variable === "iop");
  const fam = (f) => iop.filter((r) => r.family === f && !r.lbnp_mmHg).sort((a, b) => a.gz_body - b.gz_body).map((r) => ({ x: r.gz_body, y: r.median, n: r.n_subjects }));
  chart("c-iop", {
    type: "scatter",
    data: { datasets: [
      { label: "Supine tilt", data: fam("supine"), borderColor: t.s1, backgroundColor: t.s1, borderWidth: 2, pointRadius: 4, showLine: true },
      { label: "Prone tilt", data: fam("prone"), borderColor: t.s1, backgroundColor: t.s1, borderWidth: 2, borderDash: [6, 4], pointStyle: "rectRot", pointRadius: 5, showLine: true },
    ] },
    options: baseOptions({ scales: { x: axis("gz_body [g]", gzTicks), y: axis("Intraocular pressure [mmHg], median") } }),
  });
}

// ---------------------------------------------------------------- model bridge
function interp(xs, ys, x) {
  if (x <= xs[0]) return ys[0];
  if (x >= xs[xs.length - 1]) return ys[ys.length - 1];
  for (let i = 1; i < xs.length; i++) if (x <= xs[i]) { const f = (x - xs[i - 1]) / (xs[i] - xs[i - 1]); return ys[i - 1] + f * (ys[i] - ys[i - 1]); }
  return null;
}
function renderBridge() {
  const t = T();
  const gz = parseFloat($("gz").value);
  $("gz-val").textContent = `${gz.toFixed(2)} g`;
  const M = P.model;
  const realA = condRows("bhp_carotid_jugular", "ijv_area", "supine");
  const realP = condRows("bhp_carotid_jugular", "ijv_pressure", "supine");
  const inRange = gz >= -0.71 && gz <= 0.71;
  const rA = inRange ? interp(realA.map((r) => r.gz_body), realA.map((r) => r.median), gz) : null;
  const rP = inRange ? interp(realP.map((r) => r.gz_body), realP.map((r) => r.median), gz) : null;
  let mA = null, mP = null;
  if (M && M.available) {
    const xs = M.tilt_equivalent.map((r) => r.gz_body);
    mA = interp(xs, M.tilt_equivalent.map((r) => r.ijv_area), gz);
    mP = interp(xs, M.tilt_equivalent.map((r) => r.ijv_pressure), gz);
  }
  $("compare").innerHTML =
    kpi("Model · IJV area", fmt(mA, 0), " mm²", "default parameters, not fitted", ["model", "MODEL"]) +
    kpi("Real tilt · median IJV area", fmt(rA, 0), " mm²", inRange ? "supine tilt, interpolated between levels" : "outside the measured ±45° range", ["real", "REAL"]) +
    kpi("Model · IJV pressure", fmt(mP, 1), " mmHg", "default parameters, not fitted", ["model", "MODEL"]) +
    kpi("Real tilt · median IJV pressure", fmt(rP, 1), " mmHg", inRange ? "compression sonography" : "outside the measured range", ["real", "REAL"]);
  const ds = [];
  if (M && M.available) ds.push({ label: M.label, data: M.tilt_equivalent.map((r) => ({ x: r.gz_body, y: r.ijv_area })), borderColor: t.model, borderDash: [6, 4], borderWidth: 2, pointRadius: 0, showLine: true });
  ds.push({ label: "Real supine tilt, median (n ≤ 11)", data: realA.map((r) => ({ x: r.gz_body, y: r.median })), borderColor: t.s1, backgroundColor: t.s1, pointRadius: 5, pointBorderColor: t.surface, pointBorderWidth: 2, showLine: false });
  const iss = P.physiology.literature_anchors.filter((r) => r.base === "ijv_area" && String(r.environment).startsWith("iss") && !r.lbnp_mmHg);
  if (iss.length) ds.push({ label: "ISS 0 G, mean (published)", data: iss.map((r, i) => ({ x: 0.03 * (i + 1), y: r.value, lo: r.ci_low, hi: r.ci_high })), borderColor: t.s3, backgroundColor: t.s3, pointStyle: "rect", pointRadius: 6, whiskers: true });
  ds.push({ label: "selected gz_body", data: [{ x: gz, y: 2 }, { x: gz, y: 400 }], borderColor: t.axis, borderWidth: 1, pointRadius: 0, showLine: true, legendHide: true });
  chart("c-model", {
    type: "scatter", data: { datasets: ds },
    options: baseOptions({ plugins: { legend: { position: "bottom", ...hideBand }, tooltip: { ...baseOptions().plugins.tooltip, filter: (i) => !i.dataset.legendHide } },
      scales: physScales("ijv_area") }),
    plugins: [whiskerPlugin],
  });
}

// ---------------------------------------------------------------- data sources
function renderData() {
  const cls = { downloaded: "real", transcribed: "pub", synthetic: "model", metadata_only: "local", login_required: "local", request_required: "local" };
  $("t-data").innerHTML = "<tr><th>Dataset</th><th>Layer</th><th>Status</th><th>People</th><th>Licence / access</th></tr>" +
    P.datasets.map((d) => `<tr><td>${d.url ? `<a href="${d.url}" target="_blank" rel="noopener">${d.name}</a>` : d.name}</td><td>${d.layer || ""}</td>` +
      `<td><span class="badge ${cls[d.status] || "pub"}">${(d.status || "").replace("_", " ")}</span></td>` +
      `<td>${d.subjects ?? ""}</td><td>${[d.license, d.access].filter(Boolean).join(" · ")}</td></tr>`).join("");
}

// ---------------------------------------------------------------- boot
function renderAll() {
  renderHeader(); renderKpis(); renderPipeline(); renderOptical(); renderImproved(); renderPhysiology(); renderBridge(); renderQuality(); renderData();
}
document.addEventListener("DOMContentLoaded", () => {
  if (!P) { $("no-data").classList.remove("hidden"); return; }
  initTheme();
  // deep link: index.html?session=ubfc-d2-subject41 preselects a recording in the session explorer
  const want = new URLSearchParams(location.search).get("session");
  const hit = want && P.rppg.sessions.find((s) => s.session_id === want);
  if (hit) $("f-subset").value = hit.subset;
  $("f-subset").addEventListener("change", renderOptical);
  $("f-protocol").addEventListener("change", renderOptical);
  $("f-session").addEventListener("change", renderSession);
  $("f-var").addEventListener("change", renderPhysiology);
  $("gz").addEventListener("input", renderBridge);
  document.querySelectorAll(".presets button").forEach((b) => b.addEventListener("click", () => { $("gz").value = b.dataset.gz; renderBridge(); }));
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", renderAll);
  renderAll();
});
