import { readRuntimeConfig, type GlobalLocale } from "./runtime-config";

export const GLOBAL_PRODUCT_EDITION = "global" as const;
export const GLOBAL_INTERVIEW_LANGUAGE = "en-US" as const;

export interface GlobalEditionMetadata {
  readonly edition: typeof GLOBAL_PRODUCT_EDITION;
  readonly locale: GlobalLocale;
  readonly interviewLanguage: typeof GLOBAL_INTERVIEW_LANGUAGE;
  readonly productName: string;
  readonly companyName: string;
  readonly supportEmail: string;
}

export const globalEditionMetadata = (env = import.meta.env): GlobalEditionMetadata => {
  const runtime = readRuntimeConfig(env);
  return {
    edition: GLOBAL_PRODUCT_EDITION,
    locale: runtime.locale,
    interviewLanguage: GLOBAL_INTERVIEW_LANGUAGE,
    productName: "OfferSteady AI Interview Assistant",
    companyName: "OneShow AI Lab",
    supportEmail: "contact@oneshowailab.com",
  };
};

export const formatGlobalDateTime = (value: string | number | Date, locale = globalEditionMetadata().locale) =>
  new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));

export const formatGlobalNumber = (value: number, locale = globalEditionMetadata().locale) =>
  new Intl.NumberFormat(locale).format(value);
