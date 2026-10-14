import type React from "react";
import { AbsoluteFill, Interactive, type InteractivitySchema } from "remotion";
import { Hud } from "../Hud";
import { StaggerText } from "../StaggerText";
import { CREAM, ORANGE } from "../theme";

type Props = {
  readonly line1: string;
  readonly line2: string;
  readonly line3: string;
  readonly line4: string;
};

const ManifestoSceneInner: React.FC<Props> = ({ line1, line2, line3, line4 }) => {
  const dotColor = (i: number) => (i === line4.length - 1 && line4.endsWith(".") ? CREAM : ORANGE);
  return (
    <AbsoluteFill style={{ backgroundColor: "#141416", justifyContent: "center", alignItems: "center" }}>
      <StaggerText text={line1} fontSize={230} color={CREAM} stagger={1.5} />
      <StaggerText text={line2} fontSize={230} color={CREAM} delay={6} stagger={1.5} />
      <StaggerText text={line3} fontSize={230} color={ORANGE} delay={14} stagger={1.5} />
      <StaggerText text={line4} fontSize={230} color={dotColor} delay={18} stagger={1.5} />
      <Hud label="08 — MANIFESTO" />
    </AbsoluteFill>
  );
};

const schema = {
  line1: { type: "string", default: "EVERY", description: "Line 1" },
  line2: { type: "string", default: "PIXEL", description: "Line 2" },
  line3: { type: "string", default: "IS", description: "Line 3" },
  line4: { type: "string", default: "CODE.", description: "Line 4" },
} as const satisfies InteractivitySchema;

export const ManifestoScene = Interactive.withSchema({
  Component: ManifestoSceneInner,
  componentName: "ManifestoScene",
  schema,
  wrapInSequence: true,
  layout: "absolute-fill",
});
