import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { PublicReviewPage } from "./PublicReviewPage";
import { publicReviewCatalogue as catalogue, publicReviewPage } from "./public-review-pages";

describe("Merchant review commercial disclosures", () => {
  it("retains the authoritative v2 catalogue and separates billing types", () => {
    const plans = publicReviewPage("pricing")!.plans!;
    expect(plans.map(plan => [plan.name, plan.price, plan.term])).toEqual([
      ["Free", "$0", ""], ["Interview Day Pass", "$9.99", " / 24 hours"],
      ["Pro Weekly", "$49.99", " / 7 days"], ["Pro Monthly", "$99.99", "/month"],
      ["Job Hunt", "$199.99", " / 90 days"],
    ]);
    expect(plans.filter(plan => plan.billing.includes("renews automatically")).map(plan => plan.name)).toEqual(["Pro Monthly"]);
    expect(plans[0].features).toContain("One-time allowance per account");
    expect(plans[0].features.join(" ")).toContain("Resume/JD, knowledge base and Written Exam mode not included");
    expect(plans[1].features.join(" ")).toContain("180 minutes");
    expect(plans[1].features.join(" ")).toContain("knowledge base not included");
    expect(plans.slice(1).every(plan => plan.href === "" && plan.accessStarts.includes("confirmed"))).toBe(true);
  });

  it.each(["terms", "privacy", "refund-policy", "about", "contact", "security", "pricing"])("identifies the operator and support on %s", slug => {
    const { container } = render(<MemoryRouter><PublicReviewPage slug={slug} /></MemoryRouter>);
    const footer = within(container.querySelector("footer")!);
    expect(footer.getByText(new RegExp(catalogue.operator.replace(/[（（））]/g, ".")))).toBeInTheDocument();
    expect(footer.getByRole("link", { name: catalogue.supportEmail })).toHaveAttribute("href", "mailto:contact@oneshowailab.com");
    for (const [name, href] of [["Terms of Service", "/terms"], ["Privacy Policy", "/privacy"], ["Refund Policy", "/refund-policy"], ["Pricing", "/pricing"], ["About", "/about"], ["Contact", "/contact"]]) {
      expect(footer.getByRole("link", { name })).toHaveAttribute("href", href);
    }
    expect(container.textContent).not.toMatch(/support@offersteady\.com|coming soon|paid checkout|checkout is not active/i);
  });

  it("covers the fifteen requested terms without guaranteeing an outcome", () => {
    const page = publicReviewPage("terms")!;
    expect(page.sections).toHaveLength(15);
    expect(page.sections.map(section => section.heading)).toEqual([
      "1. Service Description", "2. Eligibility", "3. Account Responsibility", "4. AI-generated Content",
      "5. Acceptable Use", "6. Interview Rules and Third-party Policies", "7. Paid Services", "8. Billing",
      "9. Refunds", "10. Intellectual Property", "11. Privacy", "12. Limitation of Liability",
      "13. Termination", "14. Governing Terms", "15. Contact Information",
    ]);
    expect(JSON.stringify(page)).toContain("If assistance or capture is prohibited, do not use those features");
    expect(JSON.stringify(page)).toContain("independently verify every claim");
  });

  it("preserves the request window without promising unconditional refunds", () => {
    render(<MemoryRouter><PublicReviewPage slug="refund-policy" /></MemoryRouter>);
    expect(screen.getByRole("heading", { name: "Effective Date" })).toBeInTheDocument();
    expect(screen.getByText(/14 calendar days/)).toHaveTextContent("not a promise of an unconditional refund");
    expect(screen.getByText(/We aim to acknowledge/)).toHaveTextContent("3 business days");
    expect(screen.getByText(/If approved, a refund/)).toHaveTextContent("original payment method");
    expect(screen.getByText(/Nothing in this policy limits/)).toHaveTextContent("mandatory consumer rights");
  });

  it("discloses retained transcripts, payment metadata and staged deletion", () => {
    const text = JSON.stringify(publicReviewPage("privacy"));
    for (const phrase of ["resumes", "job descriptions", "audio-derived text", "screenshots", "browser", "usage", "subscription identifiers", "does not directly store full payment card details", "not an immediate erasure", "does not mean transcripts", "Browser storage", "contact@oneshowailab.com"]) expect(text).toContain(phrase);
  });
});
