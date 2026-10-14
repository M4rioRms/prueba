import { loadFont } from "@remotion/fonts";
import { staticFile } from "remotion";

loadFont({ family: "Inter", url: staticFile("fonts/Inter-Black.otf"), weight: "900" });
loadFont({ family: "Inter", url: staticFile("fonts/Inter-Medium.otf"), weight: "500" });
loadFont({ family: "Mono", url: staticFile("fonts/DejaVuSansMono.ttf"), weight: "400" });

export const ORANGE = "#ff4d1f";
export const DARK = "#0e0e10";
export const LIGHT = "#efece6";
export const INK = "#141414";
export const CREAM = "#f4f1ea";

export const SANS = "Inter, sans-serif";
export const MONO = "Mono, monospace";

export const easeInOutCubic = (t: number) =>
  t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
