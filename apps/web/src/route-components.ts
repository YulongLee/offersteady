import { lazy } from "react";

export const DownloadCenter = lazy(() => import("./DownloadCenter").then(module => ({ default: module.DownloadCenter })));
export const LibraryManager = lazy(() => import("./LibraryManager").then(module => ({ default: module.LibraryManager })));
export const BillingPage = lazy(() => import("./BillingPage").then(module => ({ default: module.BillingPage })));
export const GuidePage = lazy(() => import("./GuidePage").then(module => ({ default: module.GuidePage })));
export const LegalPage = lazy(() => import("./LegalPage").then(module => ({ default: module.LegalPage })));
export const AnswerWorkspace = lazy(() => import("./AnswerWorkspace").then(module => ({ default: module.AnswerWorkspace })));
