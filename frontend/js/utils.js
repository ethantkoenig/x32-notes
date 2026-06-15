/* Shared utilities */

const X32_COLORS = {
  OFF: '#555', RD: '#e05050', GN: '#50be60', YE: '#d4c040',
  BL:  '#4a8ee0', MG: '#c040a0', CY: '#40b4c0', WHi: '#909090',
  CYi: '#40b4c0',
};

function x32Color(code) {
  return X32_COLORS[code] || '#555';
}

function formatDb(db) {
  if (db === null || db === undefined || !isFinite(db)) return '−∞';
  return (db >= 0 ? '+' : '') + db.toFixed(1) + ' dB';
}

function formatDate(ts) {
  return new Date(ts * 1000).toLocaleDateString(undefined, {
    month: 'short', day: 'numeric', year: 'numeric',
  });
}

function encodePath(path) {
  return path.split('/').map(encodeURIComponent).join('/');
}
