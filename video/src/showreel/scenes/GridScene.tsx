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
import { DARK } from "../theme";

type Props = { readonly accentColor: string };

const COLS = 12;
const ROWS = 21;
const CELL = 90;

// A field of plus signs and squares pulsing outwards from the center.
const GridSceneInner: React.FC<Props> = ({ accentColor }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const intro = interpolate(frame, [0, 0.5 * fps], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const shapes = [];
  for (let j = 0; j < ROWS; j++) {
    for (let i = 0; i < COLS; i++) {
      const cx = (i + 0.5) * CELL;
      const cy = (j + 0.5) * CELL + 15;
      const d = Math.hypot(i - COLS / 2 + 0.5, j - ROWS / 2 + 0.5);
      const wave = Math.sin(d * 0.6 - t * 6) * 0.5 + 0.5;
      const s = (12 + wave * 34) * intro;
      const fill = wave > 0.6 ? accentColor : `rgba(255,255,255,${0.25 + wave * 0.6})`;
      shapes.push(
        (i + j) % 2 === 0 ? (
          <g key={`${i}-${j}`} fill={fill}>
            <rect x={cx - s / 2} y={cy - s / 6} width={s} height={s / 3} />
            <rect x={cx - s / 6} y={cy - s / 2} width={s / 3} height={s} />
          </g>
        ) : (
          <rect key={`${i}-${j}`} x={cx - s / 2.4} y={cy - s / 2.4} width={s / 1.2} height={s / 1.2} fill={fill} />
        ),
      );
    }
  }

  return (
    <AbsoluteFill style={{ backgroundColor: DARK }}>
      <svg width="100%" height="100%">
        {shapes}
      </svg>
      <Hud label="04 — SYSTEM" />
    </AbsoluteFill>
  );
};

const schema = {
  accentColor: { type: "color", default: "#ff4d1f", description: "Accent color" },
} as const satisfies InteractivitySchema;

export const GridScene = Interactive.withSchema({
  Component: GridSceneInner,
  componentName: "GridScene",
  schema,
  wrapInSequence: true,
  layout: "absolute-fill",
});
