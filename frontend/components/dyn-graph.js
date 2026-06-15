/* Compressor and gate transfer-curve renderers. */

function _dynSetup(canvas) {
  const dpr  = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width  = Math.round(rect.width  * dpr);
  canvas.height = Math.round(rect.height * dpr);
  const ctx = canvas.getContext('2d');
  ctx.scale(dpr, dpr);
  return { ctx, W: rect.width, H: rect.height };
}

function _dynPlot(ctx, W, H) {
  const ML = 30, MB = 22, MR = 8, MT = 8;
  return { ML, MB, MR, MT, PW: W - ML - MR, PH: H - MT - MB };
}

function _dynGrid(ctx, W, H, { ML, MB, MR, MT, PW, PH }, xMin, xMax, yMin, yMax, gridStep) {
  ctx.font = '9px "SF Mono", Menlo, monospace';

  for (let v = Math.ceil(xMin / gridStep) * gridStep; v <= xMax; v += gridStep) {
    const x = ML + PW * (v - xMin) / (xMax - xMin);
    ctx.strokeStyle = v === 0 ? '#2a2a2a' : '#1a1a1a';
    ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(x, MT); ctx.lineTo(x, H - MB); ctx.stroke();
    if (v > xMin && v <= xMax) {
      ctx.fillStyle = v === 0 ? '#555' : '#3a3a3a';
      ctx.textAlign = 'center'; ctx.textBaseline = 'top';
      ctx.fillText(v, x, H - MB + 3);
    }
  }
  for (let v = Math.ceil(yMin / gridStep) * gridStep; v <= yMax; v += gridStep) {
    const y = MT + PH * (1 - (v - yMin) / (yMax - yMin));
    ctx.strokeStyle = v === 0 ? '#2a2a2a' : '#1a1a1a';
    ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(ML, y); ctx.lineTo(W - MR, y); ctx.stroke();
    ctx.fillStyle = v === 0 ? '#555' : '#3a3a3a';
    ctx.textAlign = 'right'; ctx.textBaseline = 'middle';
    ctx.fillText(v, ML - 3, y);
  }
}

// ── Compressor ────────────────────────────────────────────────────────────────

function drawCompressor(canvas, comp) {
  const { ctx, W, H } = _dynSetup(canvas);
  const p = _dynPlot(ctx, W, H);
  const { ML, MB, MR, MT, PW, PH } = p;

  const IN_MIN = -60, IN_MAX = 0;
  const OUT_MIN = -60, OUT_MAX = 0;

  const inX  = db => ML + PW * (db - IN_MIN) / (IN_MAX - IN_MIN);
  const outY = db => MT + PH * (1 - (Math.max(OUT_MIN, Math.min(OUT_MAX, db)) - OUT_MIN) / (OUT_MAX - OUT_MIN));

  ctx.fillStyle = '#0d0d0d';
  ctx.fillRect(0, 0, W, H);

  _dynGrid(ctx, W, H, p, IN_MIN, IN_MAX, OUT_MIN, OUT_MAX, 12);

  const T = comp.threshold;
  const R = comp.ratio;
  const G = comp.makeup;
  const kneeW = comp.knee * 3; // approximate knee width in dB

  function compOutput(input) {
    let out;
    if (kneeW > 0) {
      const excess = input - T;
      if (excess < -kneeW / 2) {
        out = input;
      } else if (excess > kneeW / 2) {
        out = T + excess / R;
      } else {
        // Quadratic soft knee (RBJ formula)
        out = input + (1 / R - 1) * Math.pow(excess + kneeW / 2, 2) / (2 * kneeW);
      }
    } else {
      out = input < T ? input : T + (input - T) / R;
    }
    return out + G;
  }

  // 1:1 reference (dashed)
  ctx.strokeStyle = '#282828';
  ctx.lineWidth = 1;
  ctx.setLineDash([3, 3]);
  ctx.beginPath();
  ctx.moveTo(inX(IN_MIN), outY(IN_MIN));
  ctx.lineTo(inX(IN_MAX), outY(IN_MAX));
  ctx.stroke();
  ctx.setLineDash([]);

  // Threshold line (dashed)
  const tx = inX(T);
  ctx.strokeStyle = '#333';
  ctx.lineWidth = 1;
  ctx.setLineDash([2, 3]);
  ctx.beginPath(); ctx.moveTo(tx, MT); ctx.lineTo(tx, H - MB); ctx.stroke();
  ctx.setLineDash([]);

  // Transfer curve
  ctx.beginPath();
  ctx.strokeStyle = comp.enabled ? '#e8c468' : '#5a4a20';
  ctx.lineWidth = 1.5;
  ctx.lineJoin = 'round';
  const N = 300;
  for (let i = 0; i <= N; i++) {
    const input = IN_MIN + (IN_MAX - IN_MIN) * i / N;
    const x = inX(input);
    const y = outY(compOutput(input));
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  }
  ctx.stroke();

  // Axis labels
  ctx.fillStyle = '#3a3a3a';
  ctx.font = '9px "SF Mono", Menlo, monospace';
  ctx.textAlign = 'center'; ctx.textBaseline = 'bottom';
  ctx.fillText('In (dBFS)', ML + PW / 2, H - 1);
  ctx.save();
  ctx.translate(8, MT + PH / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.fillText('Out (dBFS)', 0, 0);
  ctx.restore();
}

// ── Gate ──────────────────────────────────────────────────────────────────────

function drawGate(canvas, gate) {
  const { ctx, W, H } = _dynSetup(canvas);
  const p = _dynPlot(ctx, W, H);
  const { ML, MB, MR, MT, PW, PH } = p;

  const IN_MIN = -80, IN_MAX = 0;
  const OUT_MIN = -80, OUT_MAX = 0;

  const inX  = db => ML + PW * (db - IN_MIN) / (IN_MAX - IN_MIN);
  const outY = db => MT + PH * (1 - (Math.max(OUT_MIN, Math.min(OUT_MAX, db)) - OUT_MIN) / (OUT_MAX - OUT_MIN));

  ctx.fillStyle = '#0d0d0d';
  ctx.fillRect(0, 0, W, H);

  _dynGrid(ctx, W, H, p, IN_MIN, IN_MAX, OUT_MIN, OUT_MAX, 20);

  const T = gate.threshold;
  const range = gate.range;
  const type  = gate.type;
  const floor = T - range;

  function gateOutput(input) {
    if (input >= T) return input;
    switch (type) {
      case 'EXP2': return Math.max(2 * input - T, floor);
      case 'EXP4': return Math.max(4 * input - 3 * T, floor);
      default:     return input - range; // GATE / DUCK: uniform reduction below T
    }
  }

  // 1:1 reference (dashed)
  ctx.strokeStyle = '#282828';
  ctx.lineWidth = 1;
  ctx.setLineDash([3, 3]);
  ctx.beginPath();
  ctx.moveTo(inX(IN_MIN), outY(IN_MIN));
  ctx.lineTo(inX(IN_MAX), outY(IN_MAX));
  ctx.stroke();
  ctx.setLineDash([]);

  // Threshold line (dashed)
  const tx = inX(T);
  ctx.strokeStyle = '#333';
  ctx.lineWidth = 1;
  ctx.setLineDash([2, 3]);
  ctx.beginPath(); ctx.moveTo(tx, MT); ctx.lineTo(tx, H - MB); ctx.stroke();
  ctx.setLineDash([]);

  // Transfer curve
  ctx.beginPath();
  ctx.strokeStyle = gate.enabled ? '#c070f0' : '#50285a';
  ctx.lineWidth = 1.5;
  ctx.lineJoin = 'round';
  const N = 300;
  for (let i = 0; i <= N; i++) {
    const input = IN_MIN + (IN_MAX - IN_MIN) * i / N;
    const x = inX(input);
    const y = outY(gateOutput(input));
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  }
  ctx.stroke();

  // Axis labels
  ctx.fillStyle = '#3a3a3a';
  ctx.font = '9px "SF Mono", Menlo, monospace';
  ctx.textAlign = 'center'; ctx.textBaseline = 'bottom';
  ctx.fillText('In (dBFS)', ML + PW / 2, H - 1);
  ctx.save();
  ctx.translate(8, MT + PH / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.fillText('Out (dBFS)', 0, 0);
  ctx.restore();
}
