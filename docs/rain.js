// Matrix code rain behind the masthead. Runs only on the Matrix skin with grit
// on, never when the reader prefers reduced motion, and pauses while the tab is
// hidden. About 100 glyphs per frame at 20 fps, so it costs next to nothing.

const GLYPHS = "ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜﾝ012345789Z:.=*+-<>¦";
const GLYPH_PX = 14;
const FRAME_MS = 50;
const FADE = "rgba(0, 0, 0, 0.12)";
const TRAIL = "#00ff41";
const HEAD = "#c8ffd6";
const RESET_CHANCE = 0.025;
const START_SPREAD_ROWS = 40;
const RAIN_SKIN = "matrix";

function randomGlyph() {
  return GLYPHS[Math.floor(Math.random() * GLYPHS.length)];
}

class Rain {
  constructor(canvas) {
    this.canvas = canvas;
    this.context = canvas.getContext("2d");
    this.drops = [];
    this.timer = 0;
    this.motion = window.matchMedia("(prefers-reduced-motion: reduce)");
    new ResizeObserver(() => this.resize()).observe(canvas);
  }

  resize() {
    const ratio = window.devicePixelRatio || 1;
    const { width, height } = this.canvas.getBoundingClientRect();
    this.canvas.width = Math.round(width * ratio);
    this.canvas.height = Math.round(height * ratio);
    this.context.setTransform(ratio, 0, 0, ratio, 0, 0);
    this.context.font = `${GLYPH_PX}px "Share Tech Mono", monospace`;
    this.rows = Math.ceil(height / GLYPH_PX);
    this.drops = Array.from({ length: Math.ceil(width / GLYPH_PX) }, () => -Math.floor(Math.random() * START_SPREAD_ROWS));
  }

  frame() {
    const { context } = this;
    const { width, height } = this.canvas.getBoundingClientRect();
    context.fillStyle = FADE;
    context.fillRect(0, 0, width, height);
    this.drops.forEach((row, column) => {
      const x = column * GLYPH_PX;
      if (row > 0) {
        context.fillStyle = TRAIL;
        context.fillText(randomGlyph(), x, (row - 1) * GLYPH_PX);
        context.fillStyle = HEAD;
        context.fillText(randomGlyph(), x, row * GLYPH_PX);
      }
      this.drops[column] = row > this.rows && Math.random() < RESET_CHANCE ? 0 : row + 1;
    });
  }

  sync() {
    const { skin, grit } = window.briefSkin.current();
    const wanted = skin === RAIN_SKIN && grit && !this.motion.matches && !document.hidden;
    if (wanted && !this.timer) {
      this.resize();
      this.timer = window.setInterval(() => this.frame(), FRAME_MS);
    } else if (!wanted && this.timer) {
      window.clearInterval(this.timer);
      this.timer = 0;
      this.context.clearRect(0, 0, this.canvas.width, this.canvas.height);
    }
  }
}

export function mountRain() {
  const rain = new Rain(document.getElementById("rain"));
  const sync = () => rain.sync();
  document.addEventListener(window.briefSkin.CHANGE_EVENT, sync);
  document.addEventListener("visibilitychange", sync);
  rain.motion.addEventListener("change", sync);
  sync();
}
