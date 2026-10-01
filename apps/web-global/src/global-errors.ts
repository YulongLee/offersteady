const messages: Readonly<Record<string, string>> = {
  global_practice_membership_required: "An active membership originally purchased for 7 days or longer is required.",
  global_mock_daily_limit: "You have used today's 3 sessions. Try again after 00:00 UTC.",
  mock_not_enabled: "Mock interviews are not available yet.",
  mock_not_configured: "Mock interviews are temporarily unavailable. Your existing interview tools are unaffected.",
  mock_history_full: "You can keep up to 2 records. Delete a completed session before creating another.",
  mock_creation_deleted: "That session was deleted. Refresh before creating another.",
  mock_auth_required: "Please sign in again.",
  mock_desktop_unavailable: "Open your companion, then verify the machine code and connection.",
  mock_desktop_incompatible: "Reconnect the current official desktop companion to confirm its microphone protocol.",
  mock_microphone_required: "Enable microphone access in your desktop companion.",
  mock_resume_required: "Select a successfully processed resume before starting.",
  mock_control_in_use: "This practice is open in another page. Continue there or close that page first.",
  mock_control_busy: "Practice is busy. Please try again shortly.",
  mock_control_expired: "Your connection expired. Reconnect to continue.",
  mock_session_ended: "This practice has ended or is no longer available.",
  mock_not_found: "This practice was not found.",
  mock_version_conflict: "The session changed. Please retry the current action.",
  mock_generation_in_progress: "Still generating. Please wait.",
  mock_generation_unavailable: "Generation is temporarily unavailable. Please retry.",
  mock_speech_in_progress: "A question is already playing.",
  mock_playback_not_ready: "Play the question or choose Ready to answer.",
  mock_stale_round: "The question changed. Please use the current question.",
  mock_invalid_command: "That action is not available in the current state.",
  mock_invalid_answer: "Enter or record an answer before continuing.",
  mock_not_completed: "Finish this practice before deleting it.",
  mock_audio_clock_invalid: "Enable automatic system time, then reconnect the companion.",
  mock_audio_sequence_gap: "Audio was interrupted. Reconnect the companion and retry.",
  mock_binding_changed: "The companion connection changed. Verify it again.",
  mock_device_in_use: "This companion is already connected to another practice.",
  mock_device_mismatch: "The companion does not match this session. Verify its machine code.",
  mock_invalid_audio: "The microphone audio could not be processed. Reconnect and try again.",
  mock_capture_busy: "Microphone processing is busy. Please wait and retry.",
  mock_capture_expired: "The microphone connection expired. Reconnect to continue.",
  mock_capture_in_use: "The microphone is already in use by another connection.",
  mock_answer_length_limit: "The answer reached its length limit. Review it and select Answer complete.",
  mock_audio_rate_limited: "Audio arrived too quickly. Pause and reconnect your companion.",
  mock_publisher_unavailable: "The microphone channel is unavailable. Reconnect your companion.",
  global_fair_use_restricted: "New sessions are temporarily restricted. Contact support for review.",
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
