import { assetUrl } from "./assets";

export const Logo = ({ compact = false }: { readonly compact?: boolean }) => <span className="logo-lockup"><img src={assetUrl("brand.app-icon")} width="44" height="44" decoding="async" alt="" /><strong>{compact ? "OfferSteady" : "OfferSteady AI Interview Assistant"}</strong></span>;

export function RouteLoadingPage() { return <main className="route-loading-page" role="status" aria-label="Loading page" />; }
