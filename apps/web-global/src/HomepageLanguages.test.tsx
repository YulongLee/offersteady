import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { HomepageLanguages } from "./HomepageLanguages";

describe("global homepage language coverage", () => {
  it("shows every production interview language without exposing beta languages as ready", () => {
    render(<HomepageLanguages />);
    const region = screen.getByRole("region", { name: "Production interview languages" });
    expect(region).toBeInTheDocument();
    for (const label of ["Chinese", "English", "Japanese", "Korean", "French", "German", "Spanish", "Portuguese", "Italian", "Russian"]) {
      expect(within(region).getAllByText(label).length).toBeGreaterThan(0);
    }
    expect(screen.getByText(/10 languages are ready/)).toBeInTheDocument();
    expect(within(region).queryByText("Vietnamese")).not.toBeInTheDocument();
  });
});
