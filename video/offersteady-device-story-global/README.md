# OfferSteady · Cross-device walkthrough

49-second English website film, 1920×1080 / 30fps.

- [English voice version](out/offersteady-device-story-global-voice.mp4)
- [English narration track](out/offersteady-device-story-global-narration.wav)
- [Voiceover script](voiceover-script.md)
- [Music-only version](out/offersteady-device-story-global.mp4)
- [Poster](out/poster.jpg)
- [Local playback preview](out/index.html)
- [Design record](design.md)

The story follows a computer running the Desktop Companion while a phone displays the transcript and answer guidance. Tablet and computer web views are shown as separate viewing choices. Web and companion imagery comes from the current Global product source with synthetic demo data; no production API, real account, or recorded interview data was used.

The connection code `628391` is synthetic. The connection panel is a film overlay styled from the product UI because the long mobile preparation page does not expose that section in one stable capture viewport. The rest of the product surfaces are source-rendered screenshots. The film does not imply that several live web pages remain active at the same time.

MiniMax `speech-2.8-hd` generated the English narration with the `English_Trustworthy_Man` voice. The credential was entered through a hidden prompt and was not stored in the project.

Run `npm run typecheck` and `npm run render` in this directory to reproduce the picture master. The local `node_modules` symlink reuses the established Remotion toolchain; use `npm install` after moving the project elsewhere.
