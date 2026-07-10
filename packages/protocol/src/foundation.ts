export const foundationFeatureAreas = [
  "session",
  "authentication",
  "resume",
  "job-description",
  "knowledge",
  "live-answer",
  "realtime-speech",
  "screenshot-answer",
  "billing",
] as const;

export type FoundationFeatureArea = (typeof foundationFeatureAreas)[number];
export type FoundationModuleMode = "placeholder" | "reference-only" | "deferred" | "active";

export interface FoundationModuleDescriptor {
  readonly feature: FoundationFeatureArea;
  readonly owningApp: string;
  readonly routePrefix: string;
  readonly mode: FoundationModuleMode;
  readonly notes: string;
}

export interface FoundationIndexResponse {
  readonly service: string;
  readonly apiPrefix: string;
  readonly prototypeMode: string;
  readonly modules: readonly FoundationModuleDescriptor[];
}

export interface PlaceholderOperationResponse<TFeature extends FoundationFeatureArea = FoundationFeatureArea> {
  readonly status: "placeholder";
  readonly feature: TFeature;
  readonly action: string;
  readonly message: string;
}

export interface SessionDraftPlaceholderRequest {
  readonly title: string;
  readonly role: string;
  readonly company?: string;
}

export interface ResumeUploadPlaceholderRequest {
  readonly filename: string;
  readonly contentType: string;
}

export interface JobDescriptionUploadPlaceholderRequest {
  readonly filename: string;
  readonly contentType: string;
}

export interface KnowledgeCollectionPlaceholderRequest {
  readonly name: string;
}

export interface LiveAnswerPlaceholderRequest {
  readonly sessionId: string;
  readonly prompt: string;
}

export interface ScreenshotAnswerPlaceholderRequest {
  readonly sessionId: string;
  readonly filename: string;
}

export interface FutureIntegrationPorts {
  readonly storage: "reserved";
  readonly parsing: "reserved";
  readonly retrieval: "reserved";
  readonly answerGeneration: "reserved";
  readonly screenshotAnalysis: "reserved";
  readonly streaming: "reserved";
}
