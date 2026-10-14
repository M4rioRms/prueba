import type React from "react";
import {
  AbsoluteFill,
  Interactive,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
  type InteractivitySchema,
} from "remotion";
import { Hud } from "../Hud";
import { StaggerText } from "../StaggerText";
import { INK, LIGHT, ORANGE } from "../theme";

type Props = { readonly top: string; readonly bottom: string };

const DesignSceneInner: React.FC<Props> = ({ top, bottom }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pop = spring({ frame: frame - 0.6 * fps, fps, config: { damping: 10 } });
  const shrink = interpolate(frame, [1.55 * fps, 2 * fps], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: LIGHT, justifyContent: "center", alignItems: "center" }}>
      <StaggerText text={top} fontSize={300} color={INK} stagger={2} />
      <StaggerText text={bottom} fontSize={300} color={INK} delay={6} stagger={2} />
      <div
        style={{
          position: "absolute",
          left: 870,
          top: 1185,
          width: 150,
          height: 150,
          marginLeft: -75,
          marginTop: -75,
          borderRadius: "50%",
          backgroundColor: ORANGE,
          scale: pop * shrink,
        }}
      />
      <Hud label="03 — FORM" color="rgba(0,0,0,.45)" />
    </AbsoluteFill>
  );
};

const schema = {
  top: { type: "string", default: "DESI", description: "First line" },
  bottom: { type: "string", default: "GN", description: "Second line" },
} as const satisfies InteractivitySchema;

export const DesignScene = Interactive.withSchema({
  Component: DesignSceneInner,
  componentName: "DesignScene",
  schema,
  wrapInSequence: true,
  layout: "absolute-fill",
});
