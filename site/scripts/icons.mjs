// Genera le icone PNG (PWA, Apple touch, Open Graph) dalla favicon SVG.
import { mkdir, readFile } from "node:fs/promises";
import sharp from "sharp";

const root = new URL("../public/", import.meta.url);
const out = new URL("icons/", root);
await mkdir(out, { recursive: true });

const svg = await readFile(new URL("favicon.svg", root));
const banana = "#f2c230";

for (const size of [16, 32, 180, 192, 512]) {
  await sharp(svg, { density: 72 * (size / 64) * 2 })
    .resize(size, size)
    .png()
    .toFile(new URL(`icon-${size}.png`, out).pathname.replace(/^\/(\w:)/, "$1"));
}

// icona "maskable": la scimmia al centro con margine di sicurezza su sfondo banana
const inner = await sharp(svg, { density: 72 * (410 / 64) * 2 }).resize(410, 410).png().toBuffer();
await sharp({ create: { width: 512, height: 512, channels: 4, background: banana } })
  .composite([{ input: inner, gravity: "center" }])
  .png()
  .toFile(new URL("icon-maskable-512.png", out).pathname.replace(/^\/(\w:)/, "$1"));

console.log("icone generate in public/icons/");
