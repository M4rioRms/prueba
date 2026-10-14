import { Audio } from "@remotion/media";
import { TransitionSeries } from "@remotion/transitions";
import type React from "react";
import { AbsoluteFill, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { BarsScene } from "./scenes/BarsScene";
import { DesignScene } from "./scenes/DesignScene";
import { EasingScene } from "./scenes/EasingScene";
import { GridScene } from "./scenes/GridScene";
import { HalftoneScene } from "./scenes/HalftoneScene";
import { IsoScene } from "./scenes/IsoScene";
import { ManifestoScene } from "./scenes/ManifestoScene";
import { OutroScene } from "./scenes/OutroScene";
import { TitleScene } from "./scenes/TitleScene";

// Quick white flash centered on each cut.
const Flash: React.FC = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  return (
    <AbsoluteFill
      style={{
        backgroundColor: "white",
        opacity: interpolate(frame, [0, durationInFrames / 2, durationInFrames], [0, 0.55, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        }),
      }}
    />
  );
};

export const Showreel: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      <TransitionSeries>
        <TransitionSeries.Sequence name="Easing" durationInFrames={60} premountFor={fps}>
          <EasingScene title="EASING" />
        </TransitionSeries.Sequence>
        <TransitionSeries.Overlay durationInFrames={8} premountFor={fps}>
          <Flash />
        </TransitionSeries.Overlay>
        <TransitionSeries.Sequence name="Title" durationInFrames={60} premountFor={fps}>
          <TitleScene title="CLAUDE" />
        </TransitionSeries.Sequence>
        <TransitionSeries.Overlay durationInFrames={8} premountFor={fps}>
          <Flash />
        </TransitionSeries.Overlay>
        <TransitionSeries.Sequence name="Design" durationInFrames={60} premountFor={fps}>
          <DesignScene top="DESI" bottom="GN" />
        </TransitionSeries.Sequence>
        <TransitionSeries.Overlay durationInFrames={8} premountFor={fps}>
          <Flash />
        </TransitionSeries.Overlay>
        <TransitionSeries.Sequence name="Grid" durationInFrames={60} premountFor={fps}>
          <GridScene accentColor="#ff4d1f" />
        </TransitionSeries.Sequence>
        <TransitionSeries.Overlay durationInFrames={8} premountFor={fps}>
          <Flash />
        </TransitionSeries.Overlay>
        <TransitionSeries.Sequence name="Iso" durationInFrames={60} premountFor={fps}>
          <IsoScene accentColor="#ff4d1f" />
        </TransitionSeries.Sequence>
        <TransitionSeries.Overlay durationInFrames={8} premountFor={fps}>
          <Flash />
        </TransitionSeries.Overlay>
        <TransitionSeries.Sequence name="Halftone" durationInFrames={60} premountFor={fps}>
          <HalftoneScene title="HALFTONE" />
        </TransitionSeries.Sequence>
        <TransitionSeries.Overlay durationInFrames={8} premountFor={fps}>
          <Flash />
        </TransitionSeries.Overlay>
        <TransitionSeries.Sequence name="Bars" durationInFrames={60} premountFor={fps}>
          <BarsScene value={125} caption="FRAMES OF PURE CODE" />
        </TransitionSeries.Sequence>
        <TransitionSeries.Overlay durationInFrames={8} premountFor={fps}>
          <Flash />
        </TransitionSeries.Overlay>
        <TransitionSeries.Sequence name="Manifesto" durationInFrames={60} premountFor={fps}>
          <ManifestoScene line1="EVERY" line2="PIXEL" line3="IS" line4="CODE." />
        </TransitionSeries.Sequence>
        <TransitionSeries.Overlay durationInFrames={8} premountFor={fps}>
          <Flash />
        </TransitionSeries.Overlay>
        <TransitionSeries.Sequence name="Outro" durationInFrames={90} premountFor={fps}>
          <OutroScene title="CLAUDE" subtitle="SHOWREEL 2026" />
        </TransitionSeries.Sequence>
      </TransitionSeries>
      <AbsoluteFill
        name="Fade out"
        style={{
          backgroundColor: "black",
          opacity: interpolate(frame, [durationInFrames - 15, durationInFrames], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      />
      <Audio name="Beat" src={staticFile("beat.wav")} premountFor={fps} />
    </AbsoluteFill>
  );
};
