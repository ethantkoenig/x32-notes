/* Detailed EQ frequency-response canvas with labelled axes.
   Depends on _biquadCoeffs and _responseDb from eq-curve.js. */

const EQ_DETAIL_N_POINTS = 400;
const EQ_DETAIL_DB_RANGE = 18; // ±18 dB

function drawDetailedEQ(canvas, eq) {
  const dpr  = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width  = Math.round(rect.width  * dpr);
  canvas.height = Math.round(rect.height * dpr);
  const ctx = canvas.getContext('2d');
  ctx.scale(dpr, dpr);
  const W = rect.width, H = rect.height;

  const ML = 30, MB = 22, MR = 8, MT = 8;
  const PW = W - ML - MR;
  const PH = H - MT - MB;

  const freqX = f =>
    ML + PW * Math.log10(f / EQ_FREQ_MIN) / Math.log10(EQ_FREQ_MAX / EQ_FREQ_MIN);
  const dbY = db =>
    MT + PH * (1 - (Math.max(-EQ_DETAIL_DB_RANGE, Math.min(EQ_DETAIL_DB_RANGE, db)) + EQ_DETAIL_DB_RANGE) / (2 * EQ_DETAIL_DB_RANGE));

  // Background
  ctx.fillStyle = '#0d0d0d';
  ctx.fillRect(0, 0, W, H);

  ctx.font = '9px "SF Mono", Menlo, monospace';

  // Horizontal grid + dB labels
  for (const db of [-12, -6, 0, 6, 12]) {
    const y = dbY(db);
    ctx.strokeStyle = db === 0 ? '#2a2a2a' : '#1a1a1a';
    ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(ML, y); ctx.lineTo(W - MR, y); ctx.stroke();
    ctx.fillStyle = db === 0 ? '#555' : '#3a3a3a';
    ctx.textAlign = 'right';
    ctx.textBaseline = 'middle';
    ctx.fillText((db > 0 ? '+' : '') + db, ML - 3, y);
  }

  // Vertical grid + freq labels
  const freqLabels = [
    [20, '20'], [50, '50'], [100, '100'], [200, '200'], [500, '500'],
    [1000, '1k'], [2000, '2k'], [5000, '5k'], [10000, '10k'], [20000, '20k'],
  ];
  for (const [f, label] of freqLabels) {
    const x = freqX(f);
    ctx.strokeStyle = '#1a1a1a';
    ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(x, MT); ctx.lineTo(x, H - MB); ctx.stroke();
    ctx.fillStyle = '#3a3a3a';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    ctx.fillText(label, x, H - MB + 3);
  }

  // Compute coefficients
  const coeffsList = [];
  if (eq.low_cut_enabled && eq.low_cut_freq > 0) {
    const lc1 = _biquadCoeffs({ type: 'LCut', freq: eq.low_cut_freq, gain: 0, q: 0.5412 });
    const lc2 = _biquadCoeffs({ type: 'LCut', freq: eq.low_cut_freq, gain: 0, q: 1.3066 });
    if (lc1) coeffsList.push(lc1);
    if (lc2) coeffsList.push(lc2);
  }
  coeffsList.push(...(eq.bands || [])
    .filter(b => b !== null)
    .map(b => _biquadCoeffs(b))
    .filter(c => c !== null));

  // EQ curve
  ctx.beginPath();
  ctx.strokeStyle = eq.enabled ? '#4ec9b0' : '#2a5a52';
  ctx.lineWidth = 1.5;
  ctx.lineJoin = 'round';
  for (let i = 0; i < EQ_DETAIL_N_POINTS; i++) {
    const t = i / (EQ_DETAIL_N_POINTS - 1);
    const f = EQ_FREQ_MIN * Math.pow(EQ_FREQ_MAX / EQ_FREQ_MIN, t);
    let db = 0;
    for (const c of coeffsList) db += _responseDb(c, f);
    const x = ML + PW * t;
    const y = dbY(db);
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  }
  ctx.stroke();

  // Band markers (dot at each band's freq + gain)
  for (const band of (eq.bands || [])) {
    if (!band) continue;
    const x = freqX(band.freq);
    const y = dbY(band.gain);
    if (x < ML || x > W - MR) continue;
    ctx.beginPath();
    ctx.arc(x, Math.max(MT + 3, Math.min(H - MB - 3, y)), 3, 0, Math.PI * 2);
    ctx.fillStyle = eq.enabled ? '#4ec9b0' : '#2a5a52';
    ctx.fill();
  }

  // Low-cut marker at the cutoff frequency
  if (eq.low_cut_freq > 0) {
    const x = freqX(eq.low_cut_freq);
    ctx.beginPath();
    ctx.arc(x, H - MB, 3, 0, Math.PI * 2);
    ctx.fillStyle = eq.low_cut_enabled ? '#4a8ee0' : '#2a3a5a';
    ctx.fill();
  }
}
