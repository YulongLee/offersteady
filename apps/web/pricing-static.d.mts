export interface PublicPricing {
  catalog: Array<{ id: string; displayName: string; kind: string; priceCents: number; catalogVersion: number; durationDays?: number; knowledgeIndexAllowance?: number; points?: number }>;
  rates: Record<string, number>;
}
export const catalogSource: string;
export function publicPricing(envelope: unknown): PublicPricing;
export function loadProductionPricing(fetcher?: typeof fetch): Promise<PublicPricing>;
export function pricingFingerprint(pricing: PublicPricing): string;
export function renderPricing(template: string, pricing: PublicPricing, now?: Date): string;
export function assertCurrentPricing(html: string, pricing: PublicPricing, now?: Date): void;
