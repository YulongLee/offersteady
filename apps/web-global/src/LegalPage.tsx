import { useState } from "react";
import { PublicReviewPage } from "./PublicReviewPage";

// Preserve the legacy privacy control; policy text has one canonical source.
function PromotionPrivacyControl() {
  const [status, setStatus] = useState("");
  const optOut = async () => {
    setStatus("Saving your preference…");
    try {
      const response = await fetch("/api/v1/promotion/opt-out", { method: "POST", credentials: "include" });
      if (!response.ok) throw new Error("request failed");
      window.sessionStorage?.removeItem("offersteady.promotion.qualification_event");
      setStatus("Optional promotion attribution is disabled for this browser. Core product features are unchanged.");
    } catch {
      setStatus("Unable to save this preference. Try again or contact support.");
    }
  };
  return <aside className="legal-review-note"><strong>Promotion attribution</strong><p>You can disable the optional first-party identifier used to measure promotion performance.</p><button type="button" className="button secondary" onClick={() => void optOut()}>Disable attribution</button>{status ? <p role="status">{status}</p> : null}</aside>;
}

export function LegalPage({ kind }: { readonly kind: "terms" | "privacy" }) {
  return <><PublicReviewPage slug={kind} />{kind === "privacy" ? <PromotionPrivacyControl /> : null}</>;
}
