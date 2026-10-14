import type React from "react";
import {
  AbsoluteFill,
  Easing,
  Interactive,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
  type InteractivitySchema,
} from "remotion";
import { Hud } from "../Hud";
import { DARK, MONO, ORANGE, SANS, easeInOutCubic } from "../theme";

type Props = { readonly title: string };

const EasingSceneInner: React.FC<Props> = ({ title }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const x0 = 130;
  const y0 = 1340;
  const size = 820;
  const p = interpolate(frame, [0.15 * fps, 1.7 * fps], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.65, 0, 0.35, 1),
  });

  const steps = Math.round(120 * p);
  const curve = Array.from({ length: steps + 1 }, (_, i) => {
    const u = i / 120;
    return `${i ? "L" : "M"} ${x0 + u * size} ${y0 - easeInOutCubic(u) * size}`;
  }).join(" ");
  const v = easeInOutCubic(p);
  const hx = x0 + p * size;
  const hy = y0 - v * size;

  return (
    <AbsoluteFill style={{ backgroundColor: DARK }}>
      <div
        style={{
          position: "absolute",
          top: 230,
          width: "100%",
          textAlign: "center",
          fontFamily: SANS,
          fontWeight: 900,
          fontSize: 120,
          color: "#f4f1ea",
          opacity: interpolate(frame, [0, 0.4 * fps], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      >
        {title}
      </div>
      <svg width="100%" height="100%" style={{ position: "absolute" }}>
        {Array.from({ length: 9 }, (_, i) => (
          <g key={i} stroke="rgba(255,255,255,.12)" strokeWidth={2}>
            <line x1={x0 + (i * size) / 8} y1={y0} x2={x0 + (i * size) / 8} y2={y0 - size} />
            <line x1={x0} y1={y0 - (i * size) / 8} x2={x0 + size} y2={y0 - (i * size) / 8} />
          </g>
        ))}
        <path
          d={`M ${x0} ${y0 - size} L ${x0} ${y0} L ${x0 + size} ${y0}`}
          stroke="rgba(255,255,255,.6)"
          strokeWidth={3}
          fill="none"
        />
        <path d={curve} stroke={ORANGE} strokeWidth={9} strokeLinecap="round" fill="none" />
        <path
          d={`M ${hx} ${y0} L ${hx} ${hy} L ${x0} ${hy}`}
          stroke="rgba(255,255,255,.35)"
          strokeWidth={2}
          strokeDasharray="8 10"
          fill="none"
        />
        <circle cx={hx} cy={hy} r={16} fill="#fff" />
      </svg>
      <div
        style={{
          position: "absolute",
          top: y0 + 60,
          left: x0,
          right: 1080 - x0 - size,
          display: "flex",
          justifyContent: "space-between",
          fontFamily: MONO,
          fontSize: 30,
          color: "rgba(255,255,255,.7)",
        }}
      >
        <span>bezier(.65, 0, .35, 1)</span>
        <span>v={v.toFixed(2)}</span>
      </div>
      <Hud label="01 — EASING" />
    </AbsoluteFill>
  );
};

const schema = {
  title: { type: "string", default: "EASING", description: "Title" },
} as const satisfies InteractivitySchema;

export const EasingScene = Interactive.withSchema({
  Component: EasingSceneInner,
  componentName: "EasingScene",
  schema,
  wrapInSequence: true,
  layout: "absolute-fill",
});
