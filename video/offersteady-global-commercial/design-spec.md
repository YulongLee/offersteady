# OfferSteady Global commercial video — design and production spec

## Mode and objective

Autonomous free creation, continuing the visual direction approved by the user for the Chinese commercial. The deliverable is a 36-second English product film for `offersteady.com`, with a music master and a compressed web version that keeps its audio track while loading muted.

The film explains four existing product capabilities: selecting interview context, following separate interviewer/candidate transcripts, requesting concise then detailed answer guidance, and initiating Screen Assist. It does not promise hiring outcomes, invisibility, guaranteed accuracy, or measured latency.

## Product evidence and data boundary

All product textures are fresh 1920×1080 screenshots of `apps/web-global`, captured at 2× device scale. A local adapter freezes synthetic English names, questions, transcripts, materials, and answers. Network access to production APIs and external HTTPS resources is blocked during capture. Product chrome uses the Global copy catalogue. The reference commercial contributes motion and pacing only; no competitor footage, interface, logo, people, or audio is reused.

## Visual direction

Use the current Global product system: `#080c13` background, `#101721` surfaces, `#6ee7bd` accent, `#edf2f8` text, Inter/system sans, fine borders, 16–24px radii, and restrained shadows. Headlines use 66–76px type, supporting copy 32–42px, narrative captions 60px, and the synthetic-demo disclosure 32px. The 18px chapter index is decorative metadata and carries no selling point.

Movement is calm, dimensional, and readable. There is no handheld noise, full-screen beat pumping, neon cyber treatment, or decorative particle field. Real UI remains legible through true screenshots and enlarged crops. Editorial emphasis cards are clearly video composition layers rather than invented product panels.

## Feature-to-shot mapping

| Shot | Frames | Product fact | Motion and evidence |
|---|---:|---|---|
| Open | 0–238 | Live workspace and two answer actions | Isolated real action bar; camera withdraws to the full Global workspace |
| Context | 239–542 | Resume, job description, knowledge base | `depth-layer-moves · multiplane`: one drive with 0.35/0.7/1.4 parallax coefficients and real material textures |
| Conversation | 543–902 | Separate interviewer/candidate transcript; Quick Answer | Real conversation/workspace background, readable editorial excerpt, real action bar and cursor |
| Guidance | 903–1318 | Concise answer before detailed guidance | Adapted `ai-stream-response`: readable summary first, then three real semantic answer-row crops, followed by a stable hold |
| Screen Assist | 1319–1733 | User-triggered screenshot question and structured approach | Synthetic system-design prompt, real Screen Assist action bar, scan, then an editorial summary over the real screenshot-answer panel |
| Outro | 1734–2159 | Brand and call to action | Feature tiles assemble once; logo, tagline, and CTA hold for more than two seconds |

`ai-stream-response` is adapted from seven status rows to three answer paragraphs because the product exposes three semantic blocks and no per-row status icons. Summary holds before detail, rows enter over 24 frames with 32/28-frame cue spacing, and the finished content rests before exiting. `depth-layer-moves` retains the 0.35/0.7/1.4 depth gradient, background and foreground blur anchors, and a sharp midground.

## Sound

The same licensed Mixkit music and physical transition/click effects are used so the Chinese and Global films feel like one campaign. All sound events are declared relative to shot starts. Every scene boundary is placed between the analyzed 130.013 BPM source-grid position and its measured 2.56-frame encoded-audio position, keeping both source-grid and audible-output error below two frames. Source peak delays and the measured AAC output delay are compensated so event peaks land within half a frame of intended actions. The website encode retains music and sound effects; HTML starts muted and exposes native controls so viewers can enable sound.

## Storyboard copy

1. “Stay ready for every question.”
2. “Ground every answer in your experience.”
3. “Follow the question as it unfolds.”
4. “Start clear. Then add the detail.”
5. “Turn an on-screen prompt into a plan.”
6. “Every answer, with more clarity.”

The persistent disclosure reads “PRODUCT DEMO · SYNTHETIC EXAMPLE.”
