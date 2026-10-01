import { globalApiErrorMessage } from "./global-errors";

export const mockPreparationMessage = (code: string) => {
  if (code === "mock_ready") return "Companion ready. You can start your mock interview.";
  if (code === "mock_permission_deferred") return "Companion connected. Confirm microphone access in the companion; streaming connects when you start.";
  return globalApiErrorMessage(code, 400);
};
