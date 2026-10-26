// VascuShift-GPINN Interactive Web Demonstrator
// Real-time physiological computation & Chart.js rendering

const ESA_GROUND_TRUTH = [
  { gz: 0.00, posture: 'supine', mean_area: 108.0, sd_area: 25.0, mean_p: 21.0, sd_p: 4.0, label: '0G (Supine)' },
  { gz: 0.25, posture: 'seated', mean_area: 68.0, sd_area: 22.0, mean_p: 17.5, sd_p: 3.2, label: '0.25G' },
  { gz: 0.50, posture: 'seated', mean_area: 34.0, sd_area: 11.5, mean_p: 11.2, sd_p: 2.4, label: '0.50G' },
  { gz: 0.75, posture: 'seated', mean_area: 24.0, sd_area: 9.1, mean_p: 6.8, sd_p: 1.8, label: '0.75G' },
  { gz: 1.00, posture: 'seated', mean_area: 12.0, sd_area: 4.2, mean_p: 3.5, sd_p: 1.2, label: '1.00G Seated' }
];

let hemoChart = null;
let rppgChart = null;
let bridgeChart = null;

function computePhysiology(gz, posture, modelType, noiseSigma) {
  const thetaRad = posture === 'supine' ? Math.PI / 2 : 0;
  const deltaH = 0.35; // meters
  const rho = 1060.0;  // kg/m3
  const g0 = 9.80665;  // m/s2
  const paToMmhg = 0.00750062;

  // Hydrostatic pressure drop: dP_h = rho * gz * g0 * delta_h * cos(theta) [in mmHg]
  const dPh = (rho * (gz * g0) * deltaH * Math.cos(thetaRad)) * paToMmhg;

  let area = 0;
  let pressure = 0;

  if (modelType === 'mean') {
    area = 49.2; // Training cohort mean
    pressure = 12.0;
  } else if (modelType === 'linear') {
    // OLS fit: Area = 98.4 - 88.5 * gz
    area = Math.max(5.0, 98.4 - 88.5 * (gz * Math.cos(thetaRad)));
    pressure = Math.max(0.5, 20.5 - 17.0 * (gz * Math.cos(thetaRad)));
  } else {
    // VascuShift-PINN & Mechanistic 2-Compartment Model
    const cvp = 5.5;
    const eta = 0.75;
    const effectiveGzCos = gz * Math.cos(thetaRad);
    pressure = Math.max(0.5, (cvp + 15.0 * (1.0 - Math.min(1.0, effectiveGzCos))) - dPh * eta);

    // Sigmoidal collapsible compliance law
    const A0 = 115.0;
    const Amin = 6.0;
    const k = 0.28;
    const P0 = 3.5;
    area = Amin + (A0 - Amin) / (1.0 + Math.exp(-k * (pressure - P0)));
  }

  // Add observation noise
  if (noiseSigma > 0) {
    const jitter = (Math.random() - 0.5) * 2 * noiseSigma;
    area = Math.max(3.0, area * (1.0 + jitter));
  }

  // Optical synthetic proxy feature (Module D)
  const proxy = 0.20 + 0.65 * Math.tanh(0.8 * (area / 100.0) + 0.4 * (pressure / 15.0));

  return { area, pressure, dPh, proxy };
}

function updateSimulation() {
  const gz = parseFloat(document.getElementById('gravity-slider').value);
  const posture = document.getElementById('posture-select').value;
  const modelType = document.getElementById('model-select').value;
  const noiseSigma = parseFloat(document.getElementById('noise-slider').value);

  document.getElementById('gravity-val').innerText = `${gz.toFixed(2)} G`;
  document.getElementById('noise-val').innerText = `${(noiseSigma * 100).toFixed(1)} %`;

  const state = computePhysiology(gz, posture, modelType, noiseSigma);

  document.getElementById('kpi-area').innerHTML = `${state.area.toFixed(1)} <span class="unit">mm²</span>`;
  document.getElementById('kpi-pressure').innerHTML = `${state.pressure.toFixed(1)} <span class="unit">mmHg</span>`;
  document.getElementById('kpi-hydro').innerHTML = `${state.dPh.toFixed(1)} <span class="unit">mmHg</span>`;

  // Status tag
  const areaStatus = document.getElementById('kpi-area-status');
  if (state.area > 70.0) {
    areaStatus.innerText = "Severe Venous Engorgement";
    areaStatus.style.color = "#c53030";
  } else if (state.area > 25.0) {
    areaStatus.innerText = "Moderate Venous Distension";
    areaStatus.style.color = "#dd6b20";
  } else {
    areaStatus.innerText = "Collapsed / Normal Seated Drainage";
    areaStatus.style.color = "#2f855a";
  }

  updateCharts(gz, posture, modelType, state);
}

function setGravity(val, label) {
  document.getElementById('gravity-slider').value = val;
  if (val === 0.0) {
    document.getElementById('posture-select').value = 'supine';
  } else {
    document.getElementById('posture-select').value = 'seated';
  }
  updateSimulation();
}

function initCharts() {
  const ctxHemo = document.getElementById('hemoChart').getContext('2d');
  const ctxRppg = document.getElementById('rppgChart').getContext('2d');
  const ctxBridge = document.getElementById('bridgeChart').getContext('2d');

  // Hemo chart
  hemoChart = new Chart(ctxHemo, {
    type: 'line',
    data: {
      labels: ['0.0G (Supine)', '0.25G', '0.50G', '0.75G', '1.00G Seated'],
      datasets: [
        {
          label: 'ESA PFC82 Measured Mean (±95% CI)',
          data: ESA_GROUND_TRUTH.map(d => d.mean_area),
          borderColor: '#1a365d',
          backgroundColor: 'rgba(26, 54, 93, 0.15)',
          pointRadius: 6,
          pointHoverRadius: 8,
          borderWidth: 2.5
        },
        {
          label: 'Model Prediction Curve',
          data: [108, 68, 34, 24, 12],
          borderColor: '#38a169',
          borderDash: [5, 5],
          pointRadius: 4,
          borderWidth: 2
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: { title: { display: true, text: 'IJV Area (mm²)' }, min: 0, max: 140 }
      }
    }
  });

  // rPPG waveform chart
  const rppgTime = [];
  const rppgRef = [];
  const rppgEst = [];
  for (let i = 0; i < 90; i++) {
    const t = i / 30.0;
    rppgTime.push(t.toFixed(2));
    const hrFreq = 60.0 / 60.0;
    const wave = -Math.cos(2 * Math.PI * hrFreq * t) + 0.3 * Math.cos(4 * Math.PI * hrFreq * t);
    rppgRef.push(wave);
    rppgEst.push(wave * 0.95 + 0.1 * Math.sin(2 * Math.PI * 0.2 * t));
  }

  rppgChart = new Chart(ctxRppg, {
    type: 'line',
    data: {
      labels: rppgTime,
      datasets: [
        {
          label: 'Reference Contact PPG',
          data: rppgRef,
          borderColor: '#1a202c',
          borderWidth: 2,
          pointRadius: 0
        },
        {
          label: 'POS rPPG Signal (Optical)',
          data: rppgEst,
          borderColor: '#3182ce',
          borderWidth: 1.8,
          borderDash: [4, 4],
          pointRadius: 0
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { title: { display: true, text: 'Time (s)' } },
        y: { title: { display: true, text: 'Normalized Pulse Wave' } }
      }
    }
  });

  // Bridge chart
  bridgeChart = new Chart(ctxBridge, {
    type: 'line',
    data: {
      labels: [0.0, 0.16, 0.25, 0.38, 0.50, 0.75, 1.00],
      datasets: [
        {
          label: 'Hypothetical Optical Proxy Feature (Clean)',
          data: [0.82, 0.78, 0.69, 0.58, 0.46, 0.38, 0.29],
          borderColor: '#805ad5',
          borderWidth: 2.2,
          fill: true,
          backgroundColor: 'rgba(128, 90, 213, 0.1)'
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { title: { display: true, text: 'Gravitational Condition Gz' } },
        y: { title: { display: true, text: 'Proxy Feature Value (A.U.)' }, min: 0, max: 1.0 }
      }
    }
  });
}

function updateCharts(gz, posture, modelType, state) {
  if (!hemoChart) return;

  // Recompute curve for 5 standard points
  const points = [0.0, 0.25, 0.50, 0.75, 1.00];
  const modelCurve = points.map(g => {
    const post = (g === 0.0) ? 'supine' : 'seated';
    return computePhysiology(g, post, modelType, 0.0).area;
  });

  hemoChart.data.datasets[1].data = modelCurve;
  hemoChart.update();
}

document.addEventListener('DOMContentLoaded', () => {
  initCharts();
  document.getElementById('gravity-slider').addEventListener('input', updateSimulation);
  document.getElementById('posture-select').addEventListener('change', updateSimulation);
  document.getElementById('model-select').addEventListener('change', updateSimulation);
  document.getElementById('subject-select').addEventListener('change', updateSimulation);
  document.getElementById('noise-slider').addEventListener('input', updateSimulation);
  updateSimulation();
});

