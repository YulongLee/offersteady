import { Composition } from "remotion";
import { OfferSteadyPromo } from "./main";

export const Root: React.FC = () => (
  <Composition
    id="OfferSteadyPromo"
    component={OfferSteadyPromo}
    durationInFrames={1800}
    fps={30}
    width={1920}
    height={1080}
    defaultProps={{ bgm: true }}
  />
);
