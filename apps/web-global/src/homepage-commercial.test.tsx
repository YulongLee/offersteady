import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import type { WebAppState } from "./domain";
import { syntheticState } from "../../web/src/test-state";
import { publicReviewCatalogue as catalogue } from "./public-review-pages";
import home from "./homepage-commercial.json";

describe("Commercial homepage clarity", () => {
  beforeEach(() => window.history.replaceState({}, "", "/"));
  const mount = () => render(<App initialAuthenticated={false} initialState={structuredClone(syntheticState) as unknown as WebAppState} />);

  it("keeps the first screen concise with actions before the guidance note", () => {
    const { container } = mount();
    expect(catalogue.heroTitle.split(/\s+/).length).toBeLessThanOrEqual(10);
    expect(catalogue.productDescription.split(/\s+/).length).toBeLessThanOrEqual(30);
    expect(catalogue.guidanceNotice.split(/\s+/).length).toBeLessThanOrEqual(15);
    const hero = container.querySelector(".landing-hero")!;
    expect(hero.querySelector(".hero-actions a")).toHaveAttribute("href", "/login");
    expect(hero.querySelector('a[href="#product-tour"]')).toBeInTheDocument();
    expect(hero.querySelector(".hero-actions")!.compareDocumentPosition(hero.querySelector(".hero-guidance-note")!) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("shows four distinct benefits and places pricing before optional detail", () => {
    const { container } = mount();
    expect(container.querySelectorAll(".commercial-benefits article")).toHaveLength(4);
    const ids = [...container.querySelector(".commercial-home")!.children].map(node => node.id).filter(Boolean);
    expect(ids).toEqual(["benefits", "plans", "product-tour", "why-offersteady", "faq"]);
    expect(container.querySelector(".workflow-grid")).not.toBeInTheDocument();
    expect(container.querySelector(".value-proof")).not.toBeInTheDocument();
  });

  it("keeps FAQ and comparison native and closed until requested", () => {
    const { container } = mount();
    const comparison = container.querySelector("details.commercial-comparison")!;
    expect(comparison).not.toHaveAttribute("open");
    expect(comparison.querySelector("table")).toBeInTheDocument();
    const faqs = container.querySelectorAll(".commercial-faq-list details");
    expect(faqs).toHaveLength(7);
    for (const item of faqs) expect(item).not.toHaveAttribute("open");
    for (const faq of home.faqs) expect(screen.getByText(faq.question)).toBeInTheDocument();
    expect(container.textContent).toContain("Resume/JD context, knowledge materials and Written Exam mode require an eligible paid plan");
    expect(container.textContent).toContain("Only Pro Monthly renews automatically");
  });

  it("offers free entry at the beginning, pricing and end without checkout requests", () => {
    const spy = vi.spyOn(globalThis, "fetch");
    const { container } = mount();
    for (const selector of [".hero-actions", ".homepage-free-plan", ".commercial-closing"]) expect(container.querySelector(`${selector} a[href='/login']`)).toBeInTheDocument();
    expect(spy).not.toHaveBeenCalled();
    spy.mockRestore();
  });

  it("preserves policy navigation and does not imply approval or invented proof", () => {
    const { container } = mount();
    const footer = container.querySelector("footer")!;
    expect(footer.textContent).toContain(catalogue.operator);
    expect(footer.textContent).toContain(catalogue.supportEmail);
    expect(container.textContent).toContain("payment provider approval");
    expect(container.textContent).not.toMatch(/coming soon|creem verified|guaranteed offer|never get caught|fastest|cheapest/i);
    for (const path of ["/terms", "/privacy", "/refund-policy", "/about", "/contact"]) expect(footer.querySelector(`a[href='${path}']`)).toBeInTheDocument();
  });
});
