export const knowledgeEconomicsFixtures = {
  synthetic: true,
  minimumGrossMargin: 0.6,
  pointValueCents: 10,
  knowledgeCases: [
    { tokenCount: 3_000, chargedPoints: 200, estimatedCostCents: 60 },
    { tokenCount: 10_000, chargedPoints: 200, estimatedCostCents: 100 },
    { tokenCount: 25_001, chargedPoints: 520, estimatedCostCents: 220 },
  ],
  longPassCases: [
    { durationDays: 15, priceCents: 21_990, conservativeTotalCostCents: 8_000, includedKnowledgeDocuments: 2 },
    { durationDays: 30, priceCents: 32_990, conservativeTotalCostCents: 13_000, includedKnowledgeDocuments: 2 },
  ],
} as const;
