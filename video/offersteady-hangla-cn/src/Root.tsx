import React from 'react';
import {Composition} from 'remotion';
import {HanglaVideo} from './main';
import {InternationalVideo, InternationalInterviewVideo} from './international';
import {YoutubeAd} from './youtubeAd';

export const Root: React.FC = () => (<>
  <Composition
    id="OfferSteadyHangla"
    component={HanglaVideo}
    durationInFrames={1350}
    fps={30}
    width={1080}
    height={1920}
    defaultProps={{bgm: true}}
  />
  <Composition id="OfferSteadyInternationalShort" component={InternationalVideo} durationInFrames={450} fps={30} width={1080} height={1920} defaultProps={{variant:'short',bgm:true}} />
  <Composition id="OfferSteadyInternationalFeature" component={InternationalVideo} durationInFrames={600} fps={30} width={1080} height={1920} defaultProps={{variant:'feature',bgm:true}} />
  <Composition id="OfferSteadyInternationalTrust" component={InternationalVideo} durationInFrames={900} fps={30} width={1080} height={1920} defaultProps={{variant:'trust',bgm:true}} />
  <Composition id="OfferSteadyInternationalInterview" component={InternationalInterviewVideo} durationInFrames={1800} fps={30} width={1080} height={1920} defaultProps={{bgm:true}} />
  <Composition id="OfferSteadyYoutubeAd" component={YoutubeAd} durationInFrames={1800} fps={30} width={1920} height={1080} defaultProps={{bgm:true}} />
</>);
