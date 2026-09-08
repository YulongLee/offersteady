# English film verification

- TypeScript: `node_modules/.bin/tsc --noEmit` passed.
- Picture: 1,470 frames, 1920×1080, 30fps, H.264. The final voice version is 49.000 seconds and 7,809,405 bytes, with 48kHz AAC audio.
- Source surfaces: the Global web application and Global Desktop Companion were captured with synthetic fixtures. The phone answer, phone conversation, tablet, computer web, and companion screens contain English UI. The connection panel is an English film overlay using product tokens.
- Story review: frames 100, 280, 560, 740, 960, 1160, 1290, and 1430 were assembled into `out/qa/final-contact.jpg` and checked for layout, readable copy, device roles, and the final brand line.
- Narration: eight MiniMax `speech-2.8-hd` clips use `English_Trustworthy_Man`. Each trimmed clip ends inside its assigned scene; the final line ends at 48.350 seconds and the file carries silence to 49 seconds. Timing is recorded in `voiceover-timing.json` and `out/qa/voice-silence.txt`.
- Mix: narration drives smooth sidechain reduction of the music. Final mean level is −22.5 dBFS and peak is −4.9 dBFS, with no clipping. The final MP4 decoded completely through FFmpeg.
- Security: the API credential was passed through hidden terminal input. A repository scan found no persisted `sk-api-…` credential in this project.
- Scope: only the independent video directory was added. The website, backend, desktop application, and OpenSpec behavior were not changed or deployed.
