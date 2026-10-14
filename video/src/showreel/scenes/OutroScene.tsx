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
import { CREAM, MONO, ORANGE, SANS } from "../theme";

type Props = { readonly title: string; readonly subtitle: string };

const OutroSceneInner: React.FC<Props> = ({ title, subtitle }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const burst = interpolate(frame, [0, 1.4 * fps], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ background: "radial-gradient(circle at 50% 50%, #3a1a10, #0b0b0c 65%)" }}>
      <svg width="100%" height="100%" style={{ position: "absolute" }}>
        {Array.from({ length: 110 }, (_, i) => {
          const a = i * 2.39996;
          const speed = 0.6 + ((i * 37) % 10) / 10;
          const r1 = 160 + burst * 1400 * speed;
          const r2 = r1 + 50 + speed * 80;
          return (
            <line
              key={i}
              x1={540 + Math.cos(a) * r1}
              y1={960 + Math.sin(a) * r1}
              x2={540 + Math.cos(a) * r2}
              y2={960 + Math.sin(a) * r2}
              stroke={i % 4 ? `rgba(255,255,255,${0.6 * (1 - burst)})` : `rgba(255,77,31,${1 - burst})`}
              strokeWidth={4}
            />
          );
        })}
      </svg>
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          scale: interpolate(frame, [0, 0.9 * fps], [1.3, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.out(Easing.exp),
          }),
          opacity: interpolate(frame, [0, 0.25 * fps], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      >
        <div style={{ fontFamily: SANS, fontWeight: 900, fontSize: 200, color: CREAM, lineHeight: 1 }}>
          {title}
          <span style={{ color: ORANGE }}>.</span>
        </div>
      </AbsoluteFill>
      <div
        style={{
          position: "absolute",
          top: 1130,
          width: "100%",
          textAlign: "center",
          fontFamily: MONO,
          fontSize: 34,
          letterSpacing: 10,
          color: "rgba(255,255,255,.75)",
          opacity: interpolate(frame, [0.8 * fps, 1.3 * fps], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      >
        {subtitle}
      </div>
      <Hud label="09 — END" />
    </AbsoluteFill>
  );
};

const schema = {
  title: { type: "string", default: "CLAUDE", description: "Title" },
  subtitle: { type: "string", default: "SHOWREEL 2026", description: "Subtitle" },
} as const satisfies InteractivitySchema;

export const OutroScene = Interactive.withSchema({
  Component: OutroSceneInner,
  componentName: "OutroScene",
  schema,
  wrapInSequence: true,
  layout: "absolute-fill",
});
