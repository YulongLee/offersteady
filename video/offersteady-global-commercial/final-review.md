# OfferSteady Global commercial v3 — independent final review

Review date: 2026-09-07  
Reviewed master: `out/offersteady-global-commercial.mp4`  
Picture: 2160 frames, 1920×1080, 60 fps, 36.000 s; container 36.053333 s  
Master SHA-256: `7564f89639608a5b40ffd26a88841ad2c31127315ea9eee0bdf109e6f7789393`  
Verdict: **PASS. No release blocker found.**

## Method and evidence

- Read the final-review and aesthetic rules, current design spec and README, Gallery selection, selected recipe cards and exact demos, `verification.md`, `delivery-checks.json`, `loudness.log`, `playback.json`, and audio attribution.
- Watched the complete v3 master at normal speed in QuickTime Player. The review surface showed picture but did not return monitor audio, so subjective music/SFX taste and masking remain unable to verify; objective audio checks pass.
- Independently extracted representative frames and every scene seam at ±2 frames to `out/final-review/`. Evidence includes `v3-f210.png`, `v3-f500.png`, `v3-f850.png`, `v3-f1240.png`, `v3-f1680.png`, `v3-f2020.png`, `v3-f2100.png`, `v3-f2158.png`, the five `v3-f{boundary±2}.png` groups, and `v3-seams-480.png`.
- Inspected independent 480px frames `v3-f500-480.png`, `v3-f850-480.png`, `v3-f1240-480.png`, `v3-f1680-480.png`, and `v3-f2100-480.png`.
- Independently recomputed all four SHA-256 hashes and probed the master. They match the QA manifest; all files decode cleanly and have faststart.

Status: ✓ pass · ✗ blocker · ◇ suggestion · △ unable to verify · N/A not applicable.

## P — product objective

- P1 ✓ Positioning, audience, and value are clear: an AI interview assistant that follows the conversation, grounds guidance in selected context, and supports screen prompts.
- P2 ✓ The six-shot story follows the intended priority: live workspace, context, conversation, answer guidance, Screen Assist, and brand CTA.
- P3 ✓ No guaranteed hiring result, invisibility, guaranteed accuracy, or measured-latency claim appears. Visible assertions match demonstrated behavior.
- P4 ✓ Real product textures, restrained Global styling, recipe motion, synthetic disclosure, physical SFX, and a held final CTA are present.

## F — feature completeness

- F1 ✓ Required capabilities are readable: context selection, separated interviewer/candidate content and Quick Answer, concise-then-detailed guidance, and user-triggered Screen Assist.
- F2 ✓ Each shot adds information; the outro summarizes without adding a duplicate feature claim.
- F3 ✓ Named context sources, role-labelled transcript, explicit controls, and structured answer sections explain real states rather than decorate them.

## V — visual direction

- V1 ✓ Representative frames consistently use the recorded dark navy, mint accent, clean sans typography, fine borders, restrained shadows, and rounded panels.
- V2 ✓ Normal-speed playback shows calm easing, legible entrances, and stable holds without high-frequency bounce or overshoot.
- V3 ✓ The film remains in OfferSteady's dark product language throughout.
- V4 ✓ No prohibited handheld noise, full-frame beat pumping, decorative particle field, or unrelated palette appears.

## S — selected shot recipes and Gallery variants

- S1 ✓ `depth-layer-moves · multiplane` is present in context; adapted `ai-stream-response` grammar is present in answer guidance.
- S2 ✓ Gallery mappings are exact: `multiplane` → `MultiplaneReal.tsx`; `ai-stream-response` → `StreamResponse.tsx`.
- S3 ✓ Context preserves the 0.35/0.7/1.4 drive gradient, depth blur, and sharp midground. Guidance preserves summary-first sequencing, stepped rows, tightening cues, and a completion hold.
- S4 ✓ Adaptations preserve critical constraints. Omitting per-row status icons suits semantic answer paragraphs; rows still land in captured product slots.
- S5 ✓ Product textures, coordinates, crops, and brand tokens integrate naturally; fresh captures are sufficiently resolved.
- S6 N/A Neither style is custom-only or missing preview; both local references are present.

## B — storyboard consistency

- B1 ✓ Current ranges match the design spec: 0–238, 239–542, 543–902, 903–1318, 1319–1733, 1734–2159.
- B2 ✓ Actions, page states, captions, transitions, and declared SFX match the storyboard.
- B3 ✓ Brand and CTA settle with more than two seconds of readable hold before the closing fade. See `v3-f2020.png`, `v3-f2100.png`, and `v3-f2158.png`.
- B4 ✓ No required shot is missing, substituted, or added without a recorded basis.

## D — data and asset safety

- D1 ✓ `PRODUCT DEMO · SYNTHETIC EXAMPLE` remains visible across product scenes, including independent 1920px and 480px samples.
- D2 ✓ No customer name, personal contact, credential, key, internal URL, or production identifier is visible. Identities and interview content are synthetic.
- D3 ✓ Existing pages use fresh real screenshots; editorial emphasis layers are clearly allowed film-composition elements.
- D4 ✓ Captures are complete and sharp, with no missing font, image, loading skeleton, or broken dynamic state.
- D5 ✓ Visible film copy is English-only. No Han characters are visible; fixtures are synthetic and the capture record documents blocked external/production data sources.

## A — audio and rhythm

- A1 ✓ Objective mix passes: −21.1 LUFS integrated, −3.8 dBTP true peak, 11.8 LU LRA. △ Subjective music fit and balance could not be monitored.
- A2 ✓ All rendered SFX peaks align with target events within 0.46 frame.
- A3 ✓ **Strict beat gate passes.** Every v3 boundary is within 3 frames of both the source grid and audible AAC-shifted grid. Maximum errors are 2.156f source and 1.001f audible:

  | Boundary | Source error | Audible error |
  |---:|---:|---:|
  | 239 | 2.156f | 0.404f |
  | 543 | 1.743f | 0.817f |
  | 903 | 1.601f | 0.959f |
  | 1319 | 1.732f | 0.828f |
  | 1734 | 1.559f | 1.001f |

- A4 ✓ The outro uses the recorded riser, impact, and sparkle sequence aligned to build, landing, and afterglow.
- A5 ✓ Every SFX is duration-bounded; no unbounded audio sequence is present.
- A6 ✓ Objective presence/headroom passes: peaks are detected, mono peak is −1.375 dBFS, and there are no full-scale samples. △ Subjective masking could not be monitored.
- A7 ✓ UI-adjacent sounds use physical/cinematic sources rather than confirmation bleeps or game tones.
- A8 ✓ BGM and no-BGM masters contain the same 2160-frame composition and shared SFX timing; `bgm` is the intended audio-only option.
- A9 ✓ The 2.56-frame AAC output offset is measured separately from source peak lag and included in audible-grid calculations.

## Q — visual technical quality

- Q1 ✓ Text and UI are sharp at 1920px, with no blocky transformed rasterization.
- Q2 ✓ Composition stays balanced with a clear hierarchy per shot.
- Q3 ✓ Rounded masks contain screenshots and effects; no square-corner spill appears.
- Q4 ✓ Perspective layers retain a sharp reading plane and use blur only as a depth cue.
- Q5 ✓ Elements settle without jumps, wrong coordinates, or floating final positions.
- Q6 ✓ Normal-speed viewing shows stable cameras and no unintended shake.
- Q7 ◇ The five transitions are clean, but their repeated full-dark fades are visually uniform. Varying one or two could improve momentum in a future polish pass; this is not a blocker.
- Q8 ✓ Glow is restrained and clipped; no repeated glint or cheap light sweep appears.
- Q9 ✓ Headlines, captions, feature labels, detail copy, disclosure, and CTA remain readable in independent 480px samples.
- Q10 ✓ Output timing is deterministic and the alternate audio render preserves the same picture timeline.

## Complete aesthetic-rules check

- AR1 ✓ Main messages and CTA receive adequate reading holds; CTA exceeds one second.
- AR2 ✓ Context elements use eased, staggered motion and settle long enough to read.
- AR3 ✓ Opening action and click demonstrations move at followable human speed.
- AR4 ✓ No full-frame beat pump, shake, flash, or repeated slam appears.
- AQ1 ✓ Existing pages use real captures; custom editorial panels are clear and publication quality.
- AQ2 ✓ High-resolution assets keep reading planes sharp.
- AQ3 ✓ No handheld shake.
- AQ4 ✓ No repeated glints; restrained scan treatment stays inside its panel.
- AQ5 ✓ Opening establishes one primary workspace/action subject.
- AQ6 ✓ Dense information is front-facing or mildly angled and readable.
- AQ7 N/A No physical-object orbit shot is used.
- AQ8 ✓ Outro assembles context, live actions, answer guidance, and screen guidance around the brand and reaches the visual peak.
- AQ9 ✓ Animated answer rows settle into product coordinates; no permanent fake floating row remains.
- AQ10 ✓ Example content has coherent, realistic density and complete structure.
- AQ11 ✓ Headline, caption, support copy, disclosure, and CTA hierarchy remains legible at 480px scale.
- AS1 △ Assets match the product-commercial vocabulary and exclude game bleeps, but subjective listening was unavailable.
- AS2 ✓ SFX are centrally declared by frame, source, gain, and duration; no machine-gun repetition.
- AS3 ✓ Final rendered SFX were remeasured against output.
- AS4 ✓ Clicks, transitions, motion, and final build have bounded matching effects.
- AS5 ✓ Source peak lag and 2.56-frame output delay are measured separately and accounted for.
- AC1 ✓ Captions track each shot's final action; the clean brand outro is the permitted exception.
- AC2 ✓ Copy names concrete capabilities and benefits.
- AC3 N/A No annotation text is attached to a 3D object.
- AP1 ✓ Supplied and independently extracted final-render stills were inspected.
- AP2 ✓ Both references have explicit adaptations and comparison evidence.
- AP3 N/A No ambiguous user feedback was implemented in this review.
- AP4 ✓ Required features map one-to-one to shots; motion devices do not duplicate feature set pieces.

## Delivery verification

| File | Video/audio | Frames | Bytes | SHA-256 |
|---|---|---:|---:|---|
| `offersteady-global-commercial.mp4` | H.264 1920×1080 60 fps + AAC 48 kHz | 2160 | 10,357,149 | `7564f89639608a5b40ffd26a88841ad2c31127315ea9eee0bdf109e6f7789393` |
| `offersteady-global-commercial-nobgm.mp4` | H.264 1920×1080 60 fps + AAC 48 kHz | 2160 | 10,348,794 | `16e2f75fe050ec9b783875461abf0a307ff5277c67dd12750bc7b8eca01d66e6` |
| `web/offersteady-global-web.mp4` | H.264 1920×1080 30 fps + AAC 48 kHz | 1080 | 4,605,529 | `42cb09a287ad460ee0f165320e30b69a28fb8d408afcc23f4d067ebea06d656d` |
| `web/offersteady-global-web-720.mp4` | H.264 1280×720 30 fps + AAC 48 kHz | 1080 | 2,294,295 | `8d81fa9b6bce95f79e8b8bdf90151b793329ef6613195090da7db6cf9eebef0b` |

- All four: faststart ✓, complete decode ✓, decode errors 0.
- Browser playback at 1280px and 390px: metadata, playback advance, seeking, ready state, unmute availability, and media dimensions pass; no media error.
- Audio attribution is present for Mixkit music and SFX assets.

## Blockers, suggestions, and limits

- **Blockers:** none.
- **Suggestion:** consider varying one or two repeated full-dark scene fades in a future polish pass.
- **Unable to verify:** subjective music character, SFX timbre, and masking by ear because the review surface did not return monitor audio. Loudness, headroom, clipping, attribution, event presence, sync, AAC offset, and beat alignment were verified objectively and pass.
