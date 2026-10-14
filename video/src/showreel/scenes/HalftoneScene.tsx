import type React from "react";
import {
  AbsoluteFill,
  Interactive,
  spring,
  useCurrentFrame,
  useVideoConfig,
  type InteractivitySchema,
} from "remotion";
import { Hud } from "../Hud";
import { StaggerText } from "../StaggerText";
import { INK, LIGHT, MONO, ORANGE } from "../theme";

type Props = { readonly title: string };

const R = 400;
const STEP = 19;

// A sphere drawn only with dots whose size follows a moving light.
const HalftoneSceneInner: React.FC<Props> = ({ title }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const grow = spring({ frame, fps, config: { damping: 14 } });

  const light = [Math.cos(t * 1.4) * 0.7, -0.5, 0.6];
  const len = Math.hypot(...light);
  const [lx, ly, lz] = light.map((v) => v / len);

  const dots = [];
  for (let y = -R; y <= R; y += STEP) {
    for (let x = -R; x <= R; x += STEP) {
      const r2 = x * x + y * y;
      if (r2 > R * R) continue;
      const z = Math.sqrt(R * R - r2);
      const lum = Math.max(0, Math.min(1, (x * lx + y * ly + z * lz) / R));
      const size = (1 - lum) * STEP * 0.62 * grow;
      if (size < 0.6) continue;
      dots.push(<circle key={`${x}-${y}`} cx={540 + x} cy={1060 + y} r={size} fill={INK} />);
    }
  }

  return (
    <AbsoluteFill style={{ backgroundColor: LIGHT }}>
      <div style={{ position: "absolute", top: 260, width: "100%" }}>
        <StaggerText text={title} fontSize={150} color={ORANGE} delay={4} stagger={1} />
      </div>
      <svg width="100%" height="100%" style={{ position: "absolute" }}>
        {dots}
      </svg>
      <div
        style={{
          position: "absolute",
          bottom: 260,
          width: "100%",
          textAlign: "center",
          fontFamily: MONO,
          fontSize: 34,
          color: "rgba(0,0,0,.55)",
        }}
      >
        dot = (1 − N·L) × cell
      </div>
      <Hud label="06 — TEXTURE" color="rgba(0,0,0,.45)" />
    </AbsoluteFill>
  );
};

const schema = {
  title: { type: "string", default: "HALFTONE", description: "Title" },
} as const satisfies InteractivitySchema;

export const HalftoneScene = Interactive.withSchema({
  Component: HalftoneSceneInner,
  componentName: "HalftoneScene",
  schema,
  wrapInSequence: true,
  layout: "absolute-fill",
});
