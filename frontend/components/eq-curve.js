/* EQ frequency response renderer using RBJ biquad cookbook formulas. */

const EQ_FS = 48000;
const EQ_FREQ_MIN = 20;
const EQ_FREQ_MAX = 20000;
const EQ_N_POINTS = 200;
const EQ_DB_RANGE = 15; // ±15 dB

function _biquadCoeffs(band) {
  const w0 = 2 * Math.PI * band.freq / EQ_FS;
  const cw = Math.cos(w0);
  const sw = Math.sin(w0);
  const A  = Math.pow(10, band.gain / 40);
  const alpha = sw / (2 * band.q);
  let b0, b1, b2, a0, a1, a2;

  switch (band.type) {
    case 'PEQ': case 'VEQ':
      b0 = 1 + alpha * A;  b1 = -2 * cw;  b2 = 1 - alpha * A;
      a0 = 1 + alpha / A;  a1 = -2 * cw;  a2 = 1 - alpha / A;
      break;
    case 'HShv': {
      const sqA = Math.sqrt(A);
      b0 = A * ((A+1) + (A-1)*cw + 2*sqA*alpha);
      b1 = -2 * A * ((A-1) + (A+1)*cw);
      b2 = A * ((A+1) + (A-1)*cw - 2*sqA*alpha);
      a0 = (A+1) - (A-1)*cw + 2*sqA*alpha;
      a1 = 2 * ((A-1) - (A+1)*cw);
      a2 = (A+1) - (A-1)*cw - 2*sqA*alpha;
      break;
    }
    case 'LShv': {
      const sqA = Math.sqrt(A);
      b0 = A * ((A+1) - (A-1)*cw + 2*sqA*alpha);
      b1 = 2 * A * ((A-1) - (A+1)*cw);
      b2 = A * ((A+1) - (A-1)*cw - 2*sqA*alpha);
      a0 = (A+1) + (A-1)*cw + 2*sqA*alpha;
      a1 = -2 * ((A-1) + (A+1)*cw);
      a2 = (A+1) + (A-1)*cw - 2*sqA*alpha;
      break;
    }
    case 'HCut': // high cut = low pass
      b0 = (1 - cw) / 2;  b1 = 1 - cw;  b2 = (1 - cw) / 2;
      a0 = 1 + alpha;      a1 = -2 * cw;  a2 = 1 - alpha;
      break;
    case 'LCut': // low cut = high pass
      b0 = (1 + cw) / 2;  b1 = -(1 + cw);  b2 = (1 + cw) / 2;
      a0 = 1 + alpha;      a1 = -2 * cw;    a2 = 1 - alpha;
      break;
    default:
      return null;
  }
  return { b0, b1, b2, a0, a1, a2 };
}

function _responseDb(c, freq) {
  const w = 2 * Math.PI * freq / EQ_FS;
  const cw = Math.cos(w), sw = Math.sin(w);
  const c2w = Math.cos(2 * w), s2w = Math.sin(2 * w);
  const bRe = c.b0 + c.b1*cw + c.b2*c2w;
  const bIm = -c.b1*sw - c.b2*s2w;
  const aRe = c.a0 + c.a1*cw + c.a2*c2w;
  const aIm = -c.a1*sw - c.a2*s2w;
  const aMag2 = aRe*aRe + aIm*aIm;
  if (aMag2 < 1e-14) return 0;
  return 10 * Math.log10((bRe*bRe + bIm*bIm) / aMag2);
}

function drawEQCurve(canvas, eq) {
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width  = Math.round(rect.width  * dpr);
  canvas.height = Math.round(rect.height * dpr);
  const ctx = canvas.getContext('2d');
  ctx.scale(dpr, dpr);
  const W = rect.width;
  const H = rect.height;

  // Background
  ctx.fillStyle = '#0d0d0d';
  ctx.fillRect(0, 0, W, H);

  // Grid helpers
  const freqX = f =>
    W * Math.log10(f / EQ_FREQ_MIN) / Math.log10(EQ_FREQ_MAX / EQ_FREQ_MIN);
  const dbY = db =>
    H * (1 - (Math.max(-EQ_DB_RANGE, Math.min(EQ_DB_RANGE, db)) + EQ_DB_RANGE) / (2 * EQ_DB_RANGE));

  // Horizontal grid: 0 dB brighter, ±6, ±12 dimmer
  for (const db of [-12, -6, 0, 6, 12]) {
    ctx.strokeStyle = db === 0 ? '#2a2a2a' : '#1a1a1a';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, dbY(db));
    ctx.lineTo(W, dbY(db));
    ctx.stroke();
  }

  // Vertical grid: 100 Hz, 1 kHz, 10 kHz
  ctx.strokeStyle = '#1a1a1a';
  for (const f of [100, 1000, 10000]) {
    const x = freqX(f);
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, H);
    ctx.stroke();
  }

  // Compute response
  const coeffsList = [];

  // Low-cut from preamp: 24 dB/oct = two cascaded 2nd-order Butterworth HPFs
  // Q values for a 4th-order Butterworth: 0.5412 and 1.3066
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

  // Draw curve
  ctx.beginPath();
  ctx.strokeStyle = eq.enabled ? '#4ec9b0' : '#2a5a52';
  ctx.lineWidth = 1.5;
  ctx.lineJoin = 'round';

  for (let i = 0; i < EQ_N_POINTS; i++) {
    const t = i / (EQ_N_POINTS - 1);
    const f = EQ_FREQ_MIN * Math.pow(EQ_FREQ_MAX / EQ_FREQ_MIN, t);
    let db = 0;
    for (const c of coeffsList) db += _responseDb(c, f);
    const x = W * t;
    const y = dbY(db);
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  }
  ctx.stroke();
}
