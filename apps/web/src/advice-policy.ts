export interface AdviceEvaluation {
  readonly accepted: boolean;
  readonly unsupportedClaims: readonly string[];
  readonly safeMessage?: string;
}

export const evaluateGroundedAdvice = (
  generatedClaims: readonly string[],
  groundedFacts: readonly string[],
): AdviceEvaluation => {
  const evidence = new Set(groundedFacts.map(fact => fact.trim()).filter(Boolean));
  const unsupportedClaims = generatedClaims.map(claim => claim.trim()).filter(claim => claim && !evidence.has(claim));
  if (unsupportedClaims.length === 0) return { accepted: true, unsupportedClaims: [] };
  return {
    accepted: false,
    unsupportedClaims,
    safeMessage: "现有资料不足以支持具体经历或数据，请使用你能核对的真实信息补充回答。",
  };
};
