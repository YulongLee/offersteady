# Mock interview prompts — v1

Spec: [AI mock interview](../../../openspec/changes/add-ai-mock-interview/specs/ai-mock-interview/spec.md).

`tts.txt` is the voice instruction for Qwen realtime TTS, not a reasoning prompt.
Input is a validated question; output is PCM audio. Credentials and candidate audio
never appear in prompts or fixtures. Existing quick/detail prompts are unaffected.

`question.md` consumes a bounded selected resume, optional target role and confirmed
round history. Its output is one validated question/focus object.
`report.md` returns four practice scores and feedback quoting each submitted answer.
No-answer reports are generated deterministically without requesting fabricated scores.
