/**
 * Contrast of the semantic token pairs.
 *
 * The financial-state tokens are defined twice, once per theme, and each is
 * used as text on three grounds: its own wash, the page and a card. That is
 * thirty combinations to keep above the WCAG AA threshold for small text,
 * which is what these badges use. `--neutral` was originally set to the
 * same lightness as `--muted-foreground` and came out at 4.34:1 on its own
 * wash -- close enough to look fine and low enough to fail.
 *
 * axe catches this too, but only for combinations that appear on a page it
 * visits. This checks the palette itself, so a token pair is verified
 * before anything renders it, and reports the ratio rather than a selector.
 *
 * Chart strokes are deliberately not held to 4.5. They are graphical
 * objects, not text: WCAG 1.4.11 asks 3:1 of them, and forcing a line to
 * text contrast would flatten five hues into near-black.
 */

import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const CSS = readFileSync(new URL("./globals.css", import.meta.url), "utf8");

const TONES = ["positive", "negative", "warning", "informational", "neutral"];
const GROUNDS = ["background", "card"];

/** WCAG 2.1 AA, text below 18.66px bold or 24px regular. */
const AA_SMALL_TEXT = 4.5;
/** WCAG 2.1 AA for graphical objects. */
const AA_NON_TEXT = 3;

type Rgb = [number, number, number];

/** oklch to gamma-encoded sRGB, clamped to the display gamut. */
function oklchToSrgb(l: number, c: number, h: number): Rgb {
  const a = c * Math.cos((h * Math.PI) / 180);
  const b = c * Math.sin((h * Math.PI) / 180);

  const lRoot = l + 0.3963377774 * a + 0.2158037573 * b;
  const mRoot = l - 0.1055613458 * a - 0.0638541728 * b;
  const sRoot = l - 0.0894841775 * a - 1.291485548 * b;

  const lLin = lRoot ** 3;
  const mLin = mRoot ** 3;
  const sLin = sRoot ** 3;

  const linear: Rgb = [
    4.0767416621 * lLin - 3.3077115913 * mLin + 0.2309699292 * sLin,
    -1.2684380046 * lLin + 2.6097574011 * mLin - 0.3413193965 * sLin,
    -0.0041960863 * lLin - 0.7034186147 * mLin + 1.707614701 * sLin,
  ];

  return linear.map((channel) => {
    const clamped = Math.min(1, Math.max(0, channel));
    return clamped <= 0.0031308
      ? 12.92 * clamped
      : 1.055 * clamped ** (1 / 2.4) - 0.055;
  }) as Rgb;
}

function relativeLuminance([r, g, b]: Rgb): number {
  const decode = (channel: number) =>
    channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
  return 0.2126 * decode(r) + 0.7152 * decode(g) + 0.0722 * decode(b);
}

function contrast(a: Rgb, b: Rgb): number {
  const [high, low] = [relativeLuminance(a), relativeLuminance(b)].sort(
    (x, y) => y - x,
  );
  return (high + 0.05) / (low + 0.05);
}

/** Every `--token: oklch(...)` inside one declaration block. */
function tokensOf(selector: string): Record<string, Rgb> {
  const lines = CSS.split("\n");
  const start = lines.findIndex((line) => line.trim().startsWith(`${selector} {`));
  expect(start, `no ${selector} block in globals.css`).toBeGreaterThan(-1);

  const tokens: Record<string, Rgb> = {};
  for (const line of lines.slice(start + 1)) {
    if (line.startsWith("}")) break;
    const match = /^\s*--([a-z0-9-]+):\s*oklch\(([^)]+)\)/.exec(line);
    if (!match) continue;
    const [l, c, h] = match[2].split("/")[0].trim().split(/\s+/).map(Number);
    tokens[match[1]] = oklchToSrgb(l, c, h);
  }
  return tokens;
}

describe.each([
  ["light", ":root"],
  ["dark", ".dark"],
])("%s theme", (_name, selector) => {
  const tokens = tokensOf(selector);

  it.each(TONES)("%s reads on its own wash", (tone) => {
    const ratio = contrast(tokens[tone], tokens[`${tone}-subtle`]);
    expect(ratio, `${tone} on ${tone}-subtle is ${ratio.toFixed(2)}:1`)
      .toBeGreaterThanOrEqual(AA_SMALL_TEXT);
  });

  it.each(TONES.flatMap((tone) => GROUNDS.map((ground) => [tone, ground])))(
    "%s reads on the %s",
    (tone, ground) => {
      const ratio = contrast(tokens[tone], tokens[ground]);
      expect(ratio, `${tone} on ${ground} is ${ratio.toFixed(2)}:1`)
        .toBeGreaterThanOrEqual(AA_SMALL_TEXT);
    },
  );

  it("keeps the five chart hues distinguishable from the page", () => {
    for (let index = 1; index <= 5; index += 1) {
      const ratio = contrast(tokens[`chart-${index}`], tokens.background);
      expect(ratio, `chart-${index} is ${ratio.toFixed(2)}:1`)
        .toBeGreaterThanOrEqual(AA_NON_TEXT);
    }
  });
});
