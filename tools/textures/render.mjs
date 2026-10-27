// Renders tools/textures/textures.html into docs/assets/textures/<palette>-<which>.jpg.
//
//   node tools/textures/render.mjs            # every palette
//   node tools/textures/render.mjs matrix     # one palette
//
// Needs Playwright with Chromium. steel-*.jpg ship as copies of the plug-ins'
// own Cold Steel textures, so by default only matrix is drawn here.
import { createRequire } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";
import path from "node:path";

// Resolved like require() so a globally installed Playwright (NODE_PATH) works too.
const { chromium } = createRequire(import.meta.url)("playwright");
const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.resolve(HERE, "../../docs/assets/textures");
const SIZES = { chassis: [1800, 1600], panel: [512, 512] };
const JPEG_QUALITY = 82;
const palettes = process.argv.length > 2 ? process.argv.slice(2) : ["matrix"];

const browser = await chromium.launch();
for (const palette of palettes) {
  for (const [which, [width, height]] of Object.entries(SIZES)) {
    const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 });
    const url = pathToFileURL(path.join(HERE, "textures.html"));
    url.search = new URLSearchParams({ which, palette }).toString();
    await page.goto(url.href);
    const file = path.join(OUT, `${palette}-${which}.jpg`);
    await page.screenshot({ path: file, type: "jpeg", quality: JPEG_QUALITY, clip: { x: 0, y: 0, width, height } });
    console.log(file);
    await page.close();
  }
}
await browser.close();
