export const routes = {
  landing: "/",
  login: "/login",
  app: "/app",
  newInterview: "/app/interviews/new",
  prepare: (id = ":id") => `/app/interviews/${id}/prepare`,
  live: (id = ":id") => `/app/interviews/${id}/live`,
  review: (id = ":id") => `/app/interviews/${id}/review`,
  library: "/app/library",
  billing: "/app/billing",
  guide: "/app/guide",
  devices: "/app/devices",
  settings: "/app/settings",
} as const;

export type ProtectedRoute =
  | typeof routes.app
  | typeof routes.newInterview
  | typeof routes.library
  | typeof routes.billing
  | typeof routes.guide
  | typeof routes.devices
  | typeof routes.settings;
