const messages: Readonly<Record<string, string>> = {
  active_interview_conflict: "Another interview is still active. End or continue that session first.",
  active_interview_changed: "The active interview changed. Refresh and try again.",
  interview_language_locked: "The interview language is locked after the session starts.",
  interview_programming_locked: "Programming preferences are locked after the session starts.",
  written_exam_desktop_required: "Connect the desktop companion before starting the written exam.",
  written_exam_entry_insufficient_balance: "There are not enough credits to start this written exam.",
  realtime_minute_insufficient_balance: "There are not enough credits to continue realtime transcription.",
  realtime_session_ended: "This session has ended.",
  realtime_asr_frame_timeout: "Realtime transcription timed out. Check the companion audio source and network.",
  chat_output_language_violation: "The answer provider returned the wrong language. Please try again.",
  screenshot_output_language_violation: "The screenshot answer provider returned the wrong language. Please try again.",
  chat_provider_rate_limited: "The answer service is busy. Please try again shortly.",
  chat_provider_unavailable: "The answer service is temporarily unavailable.",
  vision_config_missing: "Screenshot answers are not configured for this environment.",
  realtime_asr_config_missing: "Realtime transcription is not configured for this environment.",
  unsupported_format: "This file format is not supported.",
  empty_document: "No readable text was found in this document.",
  email_challenge_not_found: "This verification session is no longer available. Request a new code and try again.",
  request_validation_error: "Check the information entered and try again.",
  internal_server_error: "The service encountered an unexpected error. Please try again.",
};

export const globalApiErrorMessage = (code: string | undefined, status: number, fallback?: string) => {
  if (code && messages[code]) return messages[code];
  if (status === 401) return "Your session has expired. Sign in again.";
  if (status === 403) return "This account cannot perform that action.";
  if (status === 404) return "The requested item was not found.";
  if (status === 409) return "The item changed while you were working. Refresh and try again.";
  if (status === 429) return "Too many requests. Please wait and try again.";
  if (status >= 500) return "The service is temporarily unavailable. Please try again.";
  return fallback && !/[\u3400-\u9fff]/.test(fallback)
    ? fallback
    : "The request could not be completed. Please try again.";
};
