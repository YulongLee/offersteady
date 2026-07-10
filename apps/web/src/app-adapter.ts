import { BackendPreviewInterviewAdapter } from "./backend-adapter";
import type { InterviewAppAdapter } from "./domain";
import { readRuntimeConfig } from "./runtime-config";

export const runtimeConfig = readRuntimeConfig(import.meta.env);

export const interviewAppAdapter: InterviewAppAdapter = new BackendPreviewInterviewAdapter(runtimeConfig.apiBaseUrl);
