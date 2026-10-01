import { lazy } from "react";

// Keep these imports out of the public entry's static dependency graph.
export const WorkspaceApp = lazy(() => import("./WorkspaceApp").then(module => ({ default: module.WorkspaceApp })));
export const LoginPage = lazy(() => import("./LoginPage").then(module => ({ default: module.LoginPage })));
export const PublicReviewPage = lazy(() => import("./PublicReviewPage").then(module => ({ default: module.PublicReviewPage })));
