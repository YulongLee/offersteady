import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { HomepageAdvantages } from "./HomepageAdvantages";
import { publicReviewPage } from "./public-review-pages";

describe("homepage anonymous peer comparison", () => {
  it("uses actual anonymised peers, qualified data and canonical own pricing", () => {
    render(<MemoryRouter><HomepageAdvantages /></MemoryRouter>);
    const table = screen.getByRole("table");
    expect(within(table).getAllByRole("row")).toHaveLength(10);
    expect(within(table).getByRole("columnheader", { name: /OfferSteady/ })).toBeInTheDocument();
    for (const name of ["F*** R**** AI", "P******* AI", "L*****In AI"]) {
      expect(within(table).getByRole("columnheader", { name: text => text.includes(name) })).toBeInTheDocument();
      expect(table.querySelectorAll(`td[data-product="${name}"]`)).toHaveLength(9);
    }
    expect(table.textContent).not.toMatch(/Product [ABC]/);
    expect(screen.getByText(/not a market-wide ranking/)).toBeInTheDocument();
    expect(screen.getByText(/not confirmed unavailable/)).toBeInTheDocument();
    const monthly = within(table).getByRole("row", { name: /Plans & pricing/ });
    for (const feature of ["Live transcription", "On-demand AI answers", "Screenshot assistance", "Resume & job context", "Knowledge materials", "Answer controls", "Session review", "Desktop support"]) {
      expect(within(table).getByRole("rowheader", { name: new RegExp(feature) })).toBeInTheDocument();
    }
    expect(within(monthly).getByText("$90.00")).toBeInTheDocument();
    expect(within(monthly).getByText("Not verified")).toBeInTheDocument();
    for (const name of ["Interview Day Pass", "Pro Weekly", "Pro Monthly"]) {
      const plan = publicReviewPage("pricing")!.plans!.find(item => item.name === name)!;
      expect(within(table).getByText(plan.price)).toBeInTheDocument();
    }
    expect(screen.getByRole("link", { name: /Start free/ })).toHaveAttribute("href", "/login");
    expect(screen.getByRole("link", { name: /Explore plans/ })).toHaveAttribute("href", "#plans");
    expect(screen.getByRole("region", { name: "AI interview assistant comparison" })).toHaveAttribute("tabindex", "0");
    expect(document.body.textContent).not.toMatch(/Final Round|Parakeet|LockedIn|DIY WORKFLOW|Separate tools|cheapest|undetectable|anti-detection|bypass monitoring|[\u3400-\u9fff]/i);
  });
});
