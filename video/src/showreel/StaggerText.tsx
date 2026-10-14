import type React from "react";
import { spring, useCurrentFrame, useVideoConfig } from "remotion";
import { SANS } from "./theme";

// Letters rise from behind a mask one after another, with a springy overshoot.
export const StaggerText: React.FC<{
  readonly text: string;
  readonly fontSize: number;
  readonly color: string | ((index: number) => string);
  readonly delay?: number;
  readonly stagger?: number;
  readonly letterSpacing?: number;
}> = ({ text, fontSize, color, delay = 0, stagger = 2, letterSpacing = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <div
      style={{
        display: "flex",
        justifyContent: "center",
        fontFamily: SANS,
        fontWeight: 900,
        fontSize,
        lineHeight: 1,
        letterSpacing,
      }}
    >
      {[...text].map((ch, i) => {
        const p = spring({
          frame: frame - delay - i * stagger,
          fps,
          config: { damping: 12, stiffness: 140 },
        });
        return (
          <span
            key={i}
            style={{ display: "inline-block", overflow: "hidden", padding: "0.08em 0" }}
          >
            <span
              style={{
                display: "inline-block",
                whiteSpace: "pre",
                color: typeof color === "function" ? color(i) : color,
                translate: `0 ${(1 - p) * 110}%`,
              }}
            >
              {ch}
            </span>
          </span>
        );
      })}
    </div>
  );
};
