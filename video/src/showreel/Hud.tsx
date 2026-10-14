import type React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { MONO } from "./theme";

// Corner ticks, scene label and timecode shared by every scene.
export const Hud: React.FC<{
  readonly label: string;
  readonly color?: string;
}> = ({ label, color = "rgba(255,255,255,.5)" }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const m = 60;
  const tick = 28;
  const timecode = `00:00:${String(Math.floor(frame / fps)).padStart(2, "0")}:${String(frame % fps).padStart(2, "0")}`;
  const text: React.CSSProperties = {
    position: "absolute",
    fontFamily: MONO,
    fontSize: 26,
    color,
    letterSpacing: 2,
  };

  return (
    <AbsoluteFill name="HUD" style={{ pointerEvents: "none" }}>
      <svg width="100%" height="100%" style={{ position: "absolute" }}>
        {[
          [m, m, 1, 1],
          [1080 - m, m, -1, 1],
          [m, 1920 - m, 1, -1],
          [1080 - m, 1920 - m, -1, -1],
        ].map(([x, y, sx, sy]) => (
          <path
            key={`${x}-${y}`}
            d={`M ${x} ${y + sy * tick} L ${x} ${y} L ${x + sx * tick} ${y}`}
            stroke={color}
            strokeWidth={3}
            fill="none"
          />
        ))}
      </svg>
      <div style={{ ...text, left: m + 44, top: m + 4 }}>{label}</div>
      <div style={{ ...text, right: m + 44, top: m + 4 }}>{timecode}</div>
      <div style={{ ...text, left: m + 44, bottom: m + 4 }}>MOTION / 2026</div>
      <div style={{ ...text, right: m + 44, bottom: m + 4 }}>MADE WITH CODE</div>
    </AbsoluteFill>
  );
};
