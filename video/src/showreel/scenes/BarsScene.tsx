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
import { DARK, MONO, ORANGE, SANS } from "../theme";

type Props = { readonly value: number; readonly caption: string };

const BARS = 20;

const BarsSceneInner: React.FC<Props> = ({ value, caption }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const x0 = 100;
  const w = 880;
  const base = 1560;
  const count = interpolate(frame, [0, 1.3 * fps], [0, value], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  return (
    <AbsoluteFill style={{ backgroundColor: DARK }}>
      <div
        style={{
          position: "absolute",
          top: 240,
          left: x0,
          fontFamily: SANS,
          fontWeight: 900,
          fontSize: 300,
          lineHeight: 1,
          color: ORANGE,
        }}
      >
        {Math.round(count)}
      </div>
      <div
        style={{
          position: "absolute",
          top: 560,
          left: x0 + 8,
          right: x0,
          fontFamily: MONO,
          fontSize: 34,
          color: "rgba(255,255,255,.65)",
        }}
      >
        {caption}
      </div>
      <svg width="100%" height="100%" style={{ position: "absolute" }}>
        {Array.from({ length: BARS }, (_, i) => {
          const v = (Math.sin(i * 0.55) * 0.35 + 0.55 + Math.sin(i * 1.7 + 1) * 0.18) * 780;
          const h =
            v *
            interpolate(frame, [i * 1.2, i * 1.2 + 0.8 * fps], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: Easing.out(Easing.exp),
            });
          const bw = (w / BARS) * 0.66;
          const fill = i % 5 === 2 ? ORANGE : i % 3 ? "#f4f1ea" : "#ff8a66";
          return <rect key={i} x={x0 + (i * w) / BARS} y={base - h} width={bw} height={h} fill={fill} />;
        })}
        <rect x={x0} y={base + 12} width={w} height={3} fill="rgba(255,255,255,.4)" />
      </svg>
      <Hud label="07 — DATA" />
    </AbsoluteFill>
  );
};

const schema = {
  value: { type: "number", default: 125, min: 0, integer: true, hiddenFromList: false, description: "Counter target" },
  caption: { type: "string", default: "FRAMES OF PURE CODE", description: "Caption" },
} as const satisfies InteractivitySchema;

export const BarsScene = Interactive.withSchema({
  Component: BarsSceneInner,
  componentName: "BarsScene",
  schema,
  wrapInSequence: true,
  layout: "absolute-fill",
});
