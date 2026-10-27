// Applies the reader's saved skin before the page paints, so there's no flash
// of the wrong one. Loaded as a classic blocking script in <head>; the module
// scripts (settings.js, rain.js) use window.briefSkin to read and change it.
//
// <html data-skin> names the skin, data-kit the stylesheet that draws it
// (terminal.css, steel.css or the paper defaults in styles.css), and data-fx
// whether its effects run (code rain for Matrix, scratches and wear for Cold
// Steel). fxLabel is what the settings menu calls that switch; Paper has none.
(function () {
  const SKINS = {
    matrix: { label: "Matrix", kit: "terminal", fxLabel: "Code rain" },
    steel: { label: "Cold Steel", kit: "steel", fxLabel: "Grit: scratches and wear" },
    paper: { label: "Paper", kit: "paper", fxLabel: "" },
  };
  const DEFAULT_SKIN = "matrix";
  const DEFAULT_FX = true;
  const SKIN_KEY = "brief.skin";
  const FX_KEY = "brief.fx";
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

  function apply(skin, fx) {
    const root = document.documentElement;
    root.dataset.skin = skin;
    root.dataset.kit = SKINS[skin].kit;
    root.dataset.fx = fx ? "on" : "off";
  }

  const savedSkin = read(SKIN_KEY);
  const savedFx = read(FX_KEY);
  apply(savedSkin in SKINS ? savedSkin : DEFAULT_SKIN, savedFx === null ? DEFAULT_FX : savedFx === "on");

  window.briefSkin = {
    SKINS,
    CHANGE_EVENT,
    current() {
      const { skin, fx } = document.documentElement.dataset;
      return { skin, fx: fx === "on" };
    },
    set(skin, fx) {
      apply(skin, fx);
      write(SKIN_KEY, skin);
      write(FX_KEY, fx ? "on" : "off");
      document.dispatchEvent(new CustomEvent(CHANGE_EVENT, { detail: { skin, fx } }));
    },
  };
})();
