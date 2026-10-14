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
import { StaggerText } from "../StaggerText";
import { CREAM, DARK, ORANGE } from "../theme";

type Props = { readonly title: string };

const TitleSceneInner: React.FC<Props> = ({ title }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <AbsoluteFill style={{ backgroundColor: DARK }}>
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          scale: interpolate(frame, [0, 2 * fps], [1, 1.08], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      >
        <StaggerText text={title} fontSize={210} color={CREAM} delay={3} />
        <div
          style={{
            marginTop: 40,
            height: 14,
            backgroundColor: ORANGE,
            width: interpolate(frame, [0.6 * fps, 1.3 * fps], [0, 820], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: Easing.bezier(0.16, 1, 0.3, 1),
            }),
          }}
        />
      </AbsoluteFill>
      <Hud label="02 — TYPE" />
    </AbsoluteFill>
  );
};

const schema = {
  title: { type: "string", default: "CLAUDE", description: "Title" },
} as const satisfies InteractivitySchema;

export const TitleScene = Interactive.withSchema({
  Component: TitleSceneInner,
  componentName: "TitleScene",
  schema,
  wrapInSequence: true,
  layout: "absolute-fill",
});
