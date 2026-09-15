export type InterviewLanguage =
  | "zh-CN" | "en-US" | "ja-JP" | "ko-KR" | "vi-VN" | "th-TH" | "id-ID" | "ms-MY" | "fil-PH" | "hi-IN"
  | "ar-SA" | "fr-FR" | "de-DE" | "es-ES" | "pt-BR" | "ru-RU" | "it-IT" | "nl-NL" | "sv-SE" | "da-DK"
  | "fi-FI" | "nb-NO" | "el-GR" | "pl-PL" | "cs-CZ" | "hu-HU" | "ro-RO" | "bg-BG" | "hr-HR" | "sk-SK";

export type InterviewLanguageTier = "production" | "beta";

export interface InterviewLanguageDefinition {
  readonly locale: InterviewLanguage;
  readonly label: string;
  readonly nativeLabel: string;
  readonly asrLanguageCode: string;
  readonly outputLanguage: string;
  readonly tier: InterviewLanguageTier;
  readonly direction: "ltr" | "rtl";
}

const production = new Set<InterviewLanguage>([
  "zh-CN", "en-US", "ja-JP", "ko-KR", "fr-FR", "de-DE", "es-ES", "pt-BR", "it-IT", "ru-RU",
]);

const labels: Record<InterviewLanguage, [string, string, string, string]> = {
  "zh-CN": ["Chinese", "中文", "zh", "Chinese"], "en-US": ["English", "English", "en", "English"],
  "ja-JP": ["Japanese", "日本語", "ja", "Japanese"], "ko-KR": ["Korean", "한국어", "ko", "Korean"],
  "vi-VN": ["Vietnamese", "Tiếng Việt", "vi", "Vietnamese"], "th-TH": ["Thai", "ไทย", "th", "Thai"],
  "id-ID": ["Indonesian", "Bahasa Indonesia", "id", "Indonesian"], "ms-MY": ["Malay", "Bahasa Melayu", "ms", "Malay"],
  "fil-PH": ["Filipino", "Filipino", "fil", "Filipino"], "hi-IN": ["Hindi", "हिन्दी", "hi", "Hindi"],
  "ar-SA": ["Arabic", "العربية", "ar", "Arabic"], "fr-FR": ["French", "Français", "fr", "French"],
  "de-DE": ["German", "Deutsch", "de", "German"], "es-ES": ["Spanish", "Español", "es", "Spanish"],
  "pt-BR": ["Portuguese", "Português", "pt", "Portuguese"], "ru-RU": ["Russian", "Русский", "ru", "Russian"],
  "it-IT": ["Italian", "Italiano", "it", "Italian"], "nl-NL": ["Dutch", "Nederlands", "nl", "Dutch"],
  "sv-SE": ["Swedish", "Svenska", "sv", "Swedish"], "da-DK": ["Danish", "Dansk", "da", "Danish"],
  "fi-FI": ["Finnish", "Suomi", "fi", "Finnish"], "nb-NO": ["Norwegian", "Norsk", "no", "Norwegian"],
  "el-GR": ["Greek", "Ελληνικά", "el", "Greek"], "pl-PL": ["Polish", "Polski", "pl", "Polish"],
  "cs-CZ": ["Czech", "Čeština", "cs", "Czech"], "hu-HU": ["Hungarian", "Magyar", "hu", "Hungarian"],
  "ro-RO": ["Romanian", "Română", "ro", "Romanian"], "bg-BG": ["Bulgarian", "Български", "bg", "Bulgarian"],
  "hr-HR": ["Croatian", "Hrvatski", "hr", "Croatian"], "sk-SK": ["Slovak", "Slovenčina", "sk", "Slovak"],
};

export const INTERVIEW_LANGUAGE_REGISTRY: readonly InterviewLanguageDefinition[] = (Object.keys(labels) as InterviewLanguage[]).map(locale => {
  const [label, nativeLabel, asrLanguageCode, outputLanguage] = labels[locale];
  return { locale, label, nativeLabel, asrLanguageCode, outputLanguage, tier: production.has(locale) ? "production" : "beta", direction: locale === "ar-SA" ? "rtl" : "ltr" };
});

export const DEFAULT_GLOBAL_INTERVIEW_LANGUAGE: InterviewLanguage = "en-US";

export function interviewLanguageDefinition(locale: string | undefined | null): InterviewLanguageDefinition | undefined {
  return INTERVIEW_LANGUAGE_REGISTRY.find(item => item.locale === locale);
}
