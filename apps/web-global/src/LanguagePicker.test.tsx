import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { LanguagePicker } from "./App";

describe("Global interview language picker", () => {
  it("starts collapsed with English as the green default tier", () => {
    render(<LanguagePicker value="en-US" saving={false} onChange={vi.fn()} />);

    expect(screen.getByText("Default · Production")).toBeInTheDocument();
    expect(screen.getByText("Change language")).toBeInTheDocument();
    expect(screen.getByText("Change language").closest("details")).not.toHaveAttribute("open");
  });

  it("reveals registry options and preserves the selected locale", () => {
    const onChange = vi.fn();
    render(<LanguagePicker value="en-US" saving={false} onChange={onChange} />);

    fireEvent.click(screen.getByText("Change language"));
    expect(screen.getByRole("radio", { name: /日本語/ })).toBeInTheDocument();
    const english = screen.getByRole("radio", { name: /English/ }) as HTMLInputElement;
    expect(english.checked).toBe(true);

    fireEvent.click(screen.getByRole("radio", { name: /日本語/ }));
    expect(onChange).toHaveBeenCalledWith("ja-JP");
  });
});
