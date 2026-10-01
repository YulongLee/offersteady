import { useEffect } from "react";
import { useLocation } from "react-router-dom";
import { routes } from "./routes";
import { publicReviewPage } from "./public-review-pages";
import homeCopy from "./homepage-commercial.json";

export function DocumentTitleManager() {
  const { pathname } = useLocation();
  useEffect(() => {
    const reviewPage = publicReviewPage(pathname.replace(/^\//, ""));
    const landingMetadata = pathname === routes.landing ? {
      title: "OfferSteady | AI Interview Assistant",
      description: homeCopy.metaDescription,
      canonical: "https://offersteady.com/",
    } : null;
    if (pathname === routes.landing) {
      document.title = "OfferSteady | AI Interview Assistant";
    } else if (reviewPage) {
      document.title = reviewPage.title;
    } else {
      document.title = "OfferSteady AI Interview Assistant";
    }
    const metadata = reviewPage ? { title: reviewPage.title, description: reviewPage.description, canonical: `https://offersteady.com/${reviewPage.slug}` } : landingMetadata;
    if (metadata) {
      let description = document.querySelector<HTMLMetaElement>('meta[name="description"]');
      if (!description) { description = document.createElement("meta"); description.name = "description"; document.head.append(description); }
      description.content = metadata.description;
      let canonical = document.querySelector<HTMLLinkElement>('link[rel="canonical"]');
      if (!canonical) { canonical = document.createElement("link"); canonical.rel = "canonical"; document.head.append(canonical); }
      canonical.href = metadata.canonical;
    }
  }, [pathname]);
  return null;
}
