// Applies the reader's saved skin before the page paints, so there's no flash
// of the wrong one. Loaded as a classic blocking script in <head>; the module
// scripts (settings.js, rain.js) use window.briefSkin to read and change it.
//
// <html data-skin> picks the palette, data-kit the structure (steel skins share
// the chamfered modules, bolts and plates), data-grit the textures and effects.
(function () {
  const SKINS = {
    matrix: { label: "Matrix", kit: "steel" },
    steel: { label: "Cold Steel", kit: "steel" },
    paper: { label: "Paper", kit: "paper" },
  };
  const DEFAULT_SKIN = "matrix";
  const DEFAULT_GRIT = true;
  const SKIN_KEY = "brief.skin";
  const GRIT_KEY = "brief.grit";
  const CHANGE_EVENT = "briefskinchange";

  // Storage can be missing or throw (private windows, blocked site data).
  function read(key) {
    try {
      return localStorage.getItem(key);
    } catch {
      return null;
    }
  }

  function write(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch {
      // The choice still applies for this page view.
    }
  }

  function apply(skin, grit) {
    const root = document.documentElement;
    root.dataset.skin = skin;
    root.dataset.kit = SKINS[skin].kit;
    root.dataset.grit = grit ? "on" : "off";
  }

  const savedSkin = read(SKIN_KEY);
  const savedGrit = read(GRIT_KEY);
  apply(savedSkin in SKINS ? savedSkin : DEFAULT_SKIN, savedGrit === null ? DEFAULT_GRIT : savedGrit === "on");

  window.briefSkin = {
    SKINS,
    CHANGE_EVENT,
    current() {
      const { skin, grit } = document.documentElement.dataset;
      return { skin, grit: grit === "on" };
    },
    set(skin, grit) {
      apply(skin, grit);
      write(SKIN_KEY, skin);
      write(GRIT_KEY, grit ? "on" : "off");
      document.dispatchEvent(new CustomEvent(CHANGE_EVENT, { detail: { skin, grit } }));
    },
  };
})();
