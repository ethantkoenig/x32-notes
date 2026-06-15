/* API client — thin fetch wrappers */

const api = {
  async getScenes() {
    const r = await fetch('/api/scenes');
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
  },

  async getScene(path) {
    const r = await fetch('/api/scenes/' + encodePath(path));
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
  },

  async saveNote(path, note) {
    const r = await fetch('/api/notes/' + encodePath(path), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ note }),
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
  },

  async createScene(sourcePath, outputName, patches) {
    const r = await fetch('/api/scenes/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source_path: sourcePath, output_name: outputName, patches }),
    });
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${r.status}`);
    }
    return r.json();
  },
};
