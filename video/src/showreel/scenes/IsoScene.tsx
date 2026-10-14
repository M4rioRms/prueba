import type React from "react";
import {
  AbsoluteFill,
  Interactive,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
  type InteractivitySchema,
} from "remotion";
import { Hud } from "../Hud";

type Props = { readonly accentColor: string };

const N = 12;
const CELL = 62;

const hexToRgb = (hex: string) => {
  const n = parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
};

// Isometric block field with a pulsing bump in the middle, slowly rotating.
const IsoSceneInner: React.FC<Props> = ({ accentColor }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const rise = interpolate(frame, [0, 0.8 * fps], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const rot = 0.5 + t * 0.15;
  const project = (x: number, y: number, z: number): [number, number] => {
    const rx = x * Math.cos(rot) - y * Math.sin(rot);
    const ry = x * Math.sin(rot) + y * Math.cos(rot);
    return [540 + rx, 1060 + ry * 0.5 - z];
  };
  const accent = hexToRgb(accentColor);

  const cells = [];
  for (let j = 0; j < N; j++) {
    for (let i = 0; i < N; i++) {
      const x = (i - N / 2 + 0.5) * CELL;
      const y = (j - N / 2 + 0.5) * CELL;
      const r = Math.hypot(i - N / 2 + 0.5, j - N / 2 + 0.5);
      const bump = Math.max(0, 1 - r / 4.2);
      const h = 14 + bump * bump * 340 * (Math.sin(t * 3) * 0.3 + 0.8) * rise;
      cells.push({ x, y, h, bump, depth: Math.sin(rot) * x + Math.cos(rot) * y });
    }
  }
  cells.sort((a, b) => a.depth - b.depth);

  const s = CELL * 0.46;
  const corners: [number, number][] = [
    [-s, -s],
    [s, -s],
    [s, s],
    [-s, s],
  ];

  return (
    <AbsoluteFill style={{ background: "radial-gradient(circle at 50% 50%, #26282e, #0b0b0d 70%)" }}>
      <svg width="100%" height="100%">
        {cells.map((c, idx) => {
          const top = corners.map(([dx, dy]) => project(c.x + dx, c.y + dy, c.h));
          const bot = corners.map(([dx, dy]) => project(c.x + dx, c.y + dy, 0));
          const base = c.bump > 0.2 ? accent : [225, 225, 230];
          const shade = (k: number) => `rgb(${base.map((v) => Math.round(v * k)).join(",")})`;
          return (
            <g key={idx}>
              {[0, 1, 2, 3].map((k) => {
                const a = k;
                const b = (k + 1) % 4;
                return (
                  <polygon
                    key={k}
                    points={[top[a], top[b], bot[b], bot[a]].map((p) => p.join(",")).join(" ")}
                    fill={shade(0.45 + 0.15 * k)}
                  />
                );
              })}
              <polygon points={top.map((p) => p.join(",")).join(" ")} fill={shade(1)} />
            </g>
          );
        })}
      </svg>
      <Hud label="05 — DEPTH" />
    </AbsoluteFill>
  );
};

const schema = {
  accentColor: { type: "color", default: "#ff4d1f", description: "Accent color" },
} as const satisfies InteractivitySchema;

export const IsoScene = Interactive.withSchema({
  Component: IsoSceneInner,
  componentName: "IsoScene",
  schema,
  wrapInSequence: true,
  layout: "absolute-fill",
});
