import catalogueSource from "./public-review-pages.json";

export interface PublicPlan { readonly name: string; readonly price: string; readonly term: string; readonly description: string; readonly features: readonly string[]; readonly billing: string; readonly accessStarts: string; readonly action: string; readonly href: string; readonly featured: boolean }
export interface PublicPageAction { readonly label: string; readonly href: string; readonly detail: string }
export interface PublicReviewPageRecord { readonly slug: string; readonly title: string; readonly description: string; readonly eyebrow: string; readonly h1: string; readonly intro: string; readonly actions?: readonly PublicPageAction[]; readonly plans?: readonly PublicPlan[]; readonly sections: readonly { readonly heading: string; readonly paragraphs: readonly string[] }[] }
export const publicReviewCatalogue = catalogueSource as { readonly siteUrl: string; readonly supportEmail: string; readonly operator: string; readonly operatorLocation: string; readonly updatedAt: string; readonly updatedDateIso: string; readonly heroTitle: string; readonly productDescription: string; readonly guidanceNotice: string; readonly checkoutNotice: string; readonly pages: readonly PublicReviewPageRecord[] };
export const publicReviewPage = (slug: string) => publicReviewCatalogue.pages.find(page => page.slug === slug);
