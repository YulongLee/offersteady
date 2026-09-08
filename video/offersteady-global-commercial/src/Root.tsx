import React from "react";
import { Composition } from "remotion";
import { Commercial, FPS, TOTAL } from "./main";
import { AudioProbe } from "./audio";
export const Root = () => (
  <>
    {" "}
    <Composition
      id="OfferSteadyGlobalCommercial"
      component={Commercial}
      width={1920}
      height={1080}
      fps={FPS}
      durationInFrames={TOTAL}
      defaultProps={{ bgm: true, sfx: true }}
    />
    <Composition
      id="AudioProbe"
      component={AudioProbe}
      width={16}
      height={16}
      fps={60}
      durationInFrames={240}
    />
  </>
);
