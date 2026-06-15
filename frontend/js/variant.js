/* In-progress variant state — persisted in localStorage across pages. */

const variantStore = (() => {
  const KEY = 'x32_variant';

  return {
    get() {
      try { return JSON.parse(localStorage.getItem(KEY)); }
      catch { return null; }
    },

    start(basePath, baseName) {
      const dot = baseName.lastIndexOf('.');
      const outputName = (dot > 0 ? baseName.slice(0, dot) : baseName) + '_copy.scn';
      localStorage.setItem(KEY, JSON.stringify({ basePath, baseName, outputName, patches: [] }));
    },

    setOutputName(name) {
      const v = this.get();
      if (!v) return;
      v.outputName = name;
      localStorage.setItem(KEY, JSON.stringify(v));
    },

    addPatch(chnPath, chnName, channelIndex, channelName) {
      const v = this.get();
      if (!v) return;
      // Replace any existing patch for the same channel slot
      v.patches = v.patches.filter(p => p.channelIndex !== Number(channelIndex));
      v.patches.push({ chnPath, chnName, channelIndex: Number(channelIndex), channelName });
      localStorage.setItem(KEY, JSON.stringify(v));
    },

    removePatch(channelIndex) {
      const v = this.get();
      if (!v) return;
      v.patches = v.patches.filter(p => p.channelIndex !== Number(channelIndex));
      localStorage.setItem(KEY, JSON.stringify(v));
    },

    discard() {
      localStorage.removeItem(KEY);
    },
  };
})();
