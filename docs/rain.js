// Code rain behind the Matrix masthead: columns of glyphs scrolling down, and
// some up, at two speeds. Runs only on the Matrix skin with code rain on,
// never when the reader prefers reduced motion, and pauses while the tab is
// hidden. About 100 glyphs per frame at 20 fps, so it costs next to nothing.

const GLYPHS = "ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜﾝ012345789Z:.=*+-<>¦";
const GLYPH_PX = 14;
const FRAME_MS = 50;
const FADE = "rgba(0, 0, 0, 0.12)";
const TRAIL = "#00ff41";
const HEAD = "#c8ffd6";
const RISING_SHARE = 0.35;
const SLOW_SHARE = 0.4;
const SLOW_STEP_FRAMES = 2;
const RESET_CHANCE = 0.025;
const START_SPREAD_ROWS = 30;
const RAIN_SKIN = "matrix";

function randomGlyph() {
  return GLYPHS[Math.floor(Math.random() * GLYPHS.length)];
}

function newColumn(rows) {
  const rising = Math.random() < RISING_SHARE;
  const spread = Math.floor(Math.random() * START_SPREAD_ROWS);
  return {
    rising,
    step: Math.random() < SLOW_SHARE ? SLOW_STEP_FRAMES : 1,
    row: rising ? rows + spread : -spread,
  };
}

class Rain {
  constructor(canvas) {
    this.canvas = canvas;
    this.context = canvas.getContext("2d");
    this.columns = [];
    this.rows = 0;
    this.tick = 0;
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
    this.context.font = `${GLYPH_PX}px "IBM Plex Mono", monospace`;
    this.rows = Math.ceil(height / GLYPH_PX);
    this.columns = Array.from({ length: Math.ceil(width / GLYPH_PX) }, () => newColumn(this.rows));
  }

  frame() {
    const { context } = this;
    const { width, height } = this.canvas.getBoundingClientRect();
    context.fillStyle = FADE;
    context.fillRect(0, 0, width, height);
    this.tick += 1;
    this.columns.forEach((column, index) => {
      if (this.tick % column.step) return;
      const x = index * GLYPH_PX;
      const behind = column.rising ? column.row + 1 : column.row - 1;
      context.fillStyle = TRAIL;
      context.fillText(randomGlyph(), x, behind * GLYPH_PX);
      context.fillStyle = HEAD;
      context.fillText(randomGlyph(), x, column.row * GLYPH_PX);
      column.row += column.rising ? -1 : 1;
      const offscreen = column.rising ? column.row < 0 : column.row > this.rows;
      if (offscreen && Math.random() < RESET_CHANCE) this.columns[index] = newColumn(this.rows);
    });
  }

  sync() {
    const { skin, fx } = window.briefSkin.current();
    const wanted = skin === RAIN_SKIN && fx && !this.motion.matches && !document.hidden;
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
