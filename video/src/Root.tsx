import { Composition, Folder } from "remotion";
import { Showreel } from "./showreel/Showreel";
import { BarsScene } from "./showreel/scenes/BarsScene";
import { DesignScene } from "./showreel/scenes/DesignScene";
import { EasingScene } from "./showreel/scenes/EasingScene";
import { GridScene } from "./showreel/scenes/GridScene";
import { HalftoneScene } from "./showreel/scenes/HalftoneScene";
import { IsoScene } from "./showreel/scenes/IsoScene";
import { ManifestoScene } from "./showreel/scenes/ManifestoScene";
import { OutroScene } from "./showreel/scenes/OutroScene";
import { TitleScene } from "./showreel/scenes/TitleScene";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="Showreel"
        component={Showreel}
        durationInFrames={570}
        fps={30}
        width={1080}
        height={1920}
      />
      <Folder name="Showreel-Scenes">
        <Composition
          id="Easing"
          component={EasingScene}
          durationInFrames={60}
          fps={30}
          width={1080}
          height={1920}
          defaultProps={{ title: "EASING" }}
        />
        <Composition
          id="Title"
          component={TitleScene}
          durationInFrames={60}
          fps={30}
          width={1080}
          height={1920}
          defaultProps={{ title: "CLAUDE" }}
        />
        <Composition
          id="Design"
          component={DesignScene}
          durationInFrames={60}
          fps={30}
          width={1080}
          height={1920}
          defaultProps={{ top: "DESI", bottom: "GN" }}
        />
        <Composition
          id="Grid"
          component={GridScene}
          durationInFrames={60}
          fps={30}
          width={1080}
          height={1920}
          defaultProps={{ accentColor: "#ff4d1f" }}
        />
        <Composition
          id="Iso"
          component={IsoScene}
          durationInFrames={60}
          fps={30}
          width={1080}
          height={1920}
          defaultProps={{ accentColor: "#ff4d1f" }}
        />
        <Composition
          id="Halftone"
          component={HalftoneScene}
          durationInFrames={60}
          fps={30}
          width={1080}
          height={1920}
          defaultProps={{ title: "HALFTONE" }}
        />
        <Composition
          id="Bars"
          component={BarsScene}
          durationInFrames={60}
          fps={30}
          width={1080}
          height={1920}
          defaultProps={{ value: 125, caption: "FRAMES OF PURE CODE" }}
        />
        <Composition
          id="Manifesto"
          component={ManifestoScene}
          durationInFrames={60}
          fps={30}
          width={1080}
          height={1920}
          defaultProps={{ line1: "EVERY", line2: "PIXEL", line3: "IS", line4: "CODE." }}
        />
        <Composition
          id="Outro"
          component={OutroScene}
          durationInFrames={90}
          fps={30}
          width={1080}
          height={1920}
          defaultProps={{ title: "CLAUDE", subtitle: "SHOWREEL 2026" }}
        />
      </Folder>
    </>
  );
};
