/* Alpine.js components — registered before Alpine initialises */

document.addEventListener('alpine:init', () => {

  /* ── Scene list (index.html) ───────────────────────────────────────── */
  Alpine.data('sceneList', () => ({
    scenes:   [],
    orphaned: [],
    query:    '',
    sortBy:   'name',
    sortDir:  'asc',
    loading:  true,
    offline:  false,
    variant:  null,
    _es:      null,

    async init() {
      this.variant = variantStore.get();
      await this.load();
      this._connectSSE();
    },

    destroy() {
      if (this._es) this._es.close();
    },

    async load() {
      this.loading = true;
      try {
        const data = await api.getScenes();
        this.scenes   = data.scenes;
        this.orphaned = data.orphaned_notes;
        this.offline  = false;
      } catch {
        this.offline = true;
      } finally {
        this.loading = false;
      }
    },

    _connectSSE() {
      const connect = () => {
        const es = new EventSource('/api/events');
        es.onmessage = () => this.load();
        es.onerror   = () => { es.close(); setTimeout(connect, 5000); };
        this._es = es;
      };
      connect();
    },

    get filtered() {
      let result = this.scenes;
      if (this.query) {
        const q = this.query.toLowerCase();
        result = result.filter(s =>
          s.file_name.toLowerCase().includes(q) ||
          s.note_preview.toLowerCase().includes(q)
        );
      }
      const dir = this.sortDir === 'asc' ? 1 : -1;
      return [...result].sort((a, b) => {
        let va, vb;
        if      (this.sortBy === 'name')     { va = a.file_name.toLowerCase(); vb = b.file_name.toLowerCase(); }
        else if (this.sortBy === 'modified') { va = a.last_modified; vb = b.last_modified; }
        else                                  { va = a.has_note ? 1 : 0; vb = b.has_note ? 1 : 0; }
        return va < vb ? -dir : va > vb ? dir : 0;
      });
    },

    toggleSort(field) {
      if (this.sortBy === field) this.sortDir = this.sortDir === 'asc' ? 'desc' : 'asc';
      else { this.sortBy = field; this.sortDir = 'asc'; }
    },

    openScene(path) {
      const page = path.endsWith('.chn') ? 'channel.html' : 'scene.html';
      window.location.href = page + '?path=' + encodeURIComponent(path);
    },

    goToBaseScene() {
      window.location.href = 'scene.html?path=' + encodeURIComponent(this.variant.basePath);
    },

    discardVariant() {
      variantStore.discard();
      this.variant = null;
    },

    // exposed to template
    formatDate,
  }));


  /* ── Scene detail (scene.html) ─────────────────────────────────────── */
  Alpine.data('sceneDetail', () => ({
    filePath:          '',
    scene:             null,
    note:              '',
    loading:           true,
    saving:            false,
    savedFlash:        false,
    offline:           false,
    _flashTimer:       null,
    variant:           null,
    variantOutputName: '',
    creating:          false,
    createError:       '',

    async init() {
      this.filePath = new URLSearchParams(window.location.search).get('path') || '';
      this.variant  = variantStore.get();
      if (this.variant) this.variantOutputName = this.variant.outputName || '';
      if (!this.filePath) { this.loading = false; return; }
      await this.load();
    },

    async load() {
      this.loading = true;
      try {
        this.scene = await api.getScene(this.filePath);
        this.note  = this.scene.note;
        this.offline = false;
      } catch {
        this.offline = true;
      } finally {
        this.loading = false;
      }
      await this.$nextTick();
      this._drawEQ();
    },

    _drawEQ() {
      for (const idx of Object.keys(this.scene?.channels || {})) {
        const canvas = document.querySelector(`[data-ch="${idx}"] .eq-canvas`);
        const ch = this.scene.channels[idx];
        if (canvas && ch.eq) drawEQCurve(canvas, ch.eq);
      }
    },

    async saveNote() {
      if (this.saving) return;
      this.saving = true;
      try {
        await api.saveNote(this.filePath, this.note);
        this.savedFlash = true;
        clearTimeout(this._flashTimer);
        this._flashTimer = setTimeout(() => { this.savedFlash = false; }, 2000);
      } catch {
        /* silently ignore — offline banner covers it */
      } finally {
        this.saving = false;
      }
    },

    startVariant() {
      variantStore.start(this.filePath, this.scene.file_name);
      window.location.href = 'index.html';
    },

    removeVariantPatch(channelIndex) {
      variantStore.removePatch(channelIndex);
      this.variant = variantStore.get();
    },

    discardVariant() {
      variantStore.discard();
      this.variant = null;
    },

    updateVariantOutputName(name) {
      this.variantOutputName = name;
      variantStore.setOutputName(name);
    },

    async doCreateScene() {
      if (this.creating) return;
      if (!this.variantOutputName.trim()) { this.createError = 'Enter an output filename.'; return; }
      if (!this.variant?.patches?.length) { this.createError = 'Add at least one preset.'; return; }
      this.creating = true;
      this.createError = '';
      try {
        const patches = this.variant.patches.map(p => ({
          chn_path: p.chnPath, channel_index: p.channelIndex,
        }));
        const result = await api.createScene(this.filePath, this.variantOutputName.trim(), patches);
        variantStore.discard();
        window.location.href = 'scene.html?path=' + encodeURIComponent(result.file_path);
      } catch (e) {
        this.createError = e.message || 'Failed to create scene.';
      } finally {
        this.creating = false;
      }
    },

    get sortedChannels() {
      if (!this.scene) return [];
      return Object.entries(this.scene.channels)
        .map(([idx, ch]) => ({ idx: Number(idx), ...ch }))
        .sort((a, b) => a.idx - b.idx);
    },

    // helpers exposed to template
    x32Color,
    formatDb,
    formatDate,

    formatComp(ch) {
      const c = ch.compressor;
      if (!c) return '';
      const state = c.enabled ? '' : 'off ';
      return `${state}${c.mode} ${c.threshold.toFixed(1)} dB  ${c.ratio.toFixed(1)}:1`;
    },

    formatGate(ch) {
      const g = ch.gate;
      if (!g) return '';
      const state = g.enabled ? '' : 'off ';
      return `${state}${g.type} ${g.threshold.toFixed(1)} dB`;
    },
  }));


  /* ── Channel detail (channel.html) ────────────────────────────────────── */
  Alpine.data('channelDetail', () => ({
    filePath:            '',
    scene:               null,
    ch:                  null,
    note:                '',
    loading:             true,
    saving:              false,
    savedFlash:          false,
    offline:             false,
    _flashTimer:         null,
    variant:             null,
    baseChannels:        [],
    variantChannelIndex: '',

    async init() {
      this.filePath = new URLSearchParams(window.location.search).get('path') || '';
      this.variant  = variantStore.get();
      if (!this.filePath) { this.loading = false; return; }
      await this.load();
      if (this.variant) {
        await this._loadBaseChannels();
        this._autoSelectChannel();
      }
    },

    async load() {
      this.loading = true;
      try {
        this.scene = await api.getScene(this.filePath);
        const keys = Object.keys(this.scene.channels);
        this.ch   = keys.length ? this.scene.channels[keys[0]] : null;
        this.note = this.scene.note;
        this.offline = false;
      } catch {
        this.offline = true;
      } finally {
        this.loading = false;
      }
      await this.$nextTick();
      this._drawAll();
    },

    _drawAll() {
      if (this.$refs.eqCanvas  && this.ch?.eq)         drawDetailedEQ(this.$refs.eqCanvas,  this.ch.eq);
      if (this.$refs.compCanvas && this.ch?.compressor) drawCompressor(this.$refs.compCanvas, this.ch.compressor);
      if (this.$refs.gateCanvas && this.ch?.gate)       drawGate(this.$refs.gateCanvas,       this.ch.gate);
    },

    async _loadBaseChannels() {
      try {
        const data = await api.getScene(this.variant.basePath);
        this.baseChannels = Object.entries(data.channels)
          .map(([idx, ch]) => ({ idx: Number(idx), ...ch }))
          .sort((a, b) => a.idx - b.idx);
      } catch {
        this.baseChannels = [];
      }
    },

    _autoSelectChannel() {
      if (!this.baseChannels.length) { this.variantChannelIndex = ''; return; }
      const myName = this.ch?.name?.toLowerCase();
      const match  = myName && this.baseChannels.find(c => c.name?.toLowerCase() === myName);
      this.variantChannelIndex = String(match ? match.idx : this.baseChannels[0].idx);
    },

    addToVariant() {
      const idx = Number(this.variantChannelIndex);
      const ch  = this.baseChannels.find(c => c.idx === idx);
      variantStore.addPatch(this.filePath, this.scene.file_name, idx, ch?.name || '');
      window.location.href = 'index.html';
    },

    discardVariant() {
      variantStore.discard();
      this.variant = null;
    },

    async saveNote() {
      if (this.saving) return;
      this.saving = true;
      try {
        await api.saveNote(this.filePath, this.note);
        this.savedFlash = true;
        clearTimeout(this._flashTimer);
        this._flashTimer = setTimeout(() => { this.savedFlash = false; }, 2000);
      } catch { /* offline banner covers it */ } finally {
        this.saving = false;
      }
    },

    x32Color,
    formatDb,
    formatDate,
    formatFreq(hz) {
      if (hz >= 1000) {
        const k = hz / 1000;
        return (k < 10 ? k.toFixed(2) : k.toFixed(1)).replace(/\.?0+$/, '') + ' kHz';
      }
      return (hz % 1 === 0 ? hz : hz.toFixed(1)) + ' Hz';
    },
  }));

});
