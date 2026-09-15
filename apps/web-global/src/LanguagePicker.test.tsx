import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { LanguagePicker } from "./App";

describe("Global interview language picker", () => {
  it("renders the expanded language list with English as the green default tier", () => {
    render(<LanguagePicker value="en-US" saving={false} onChange={vi.fn()} />);

    expect(screen.getByText("Default · Production")).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /日本語/ })).toBeInTheDocument();
  });

  it("reveals registry options and preserves the selected locale", () => {
    const onChange = vi.fn();
    render(<LanguagePicker value="en-US" saving={false} onChange={onChange} />);

    expect(screen.getByRole("radio", { name: /日本語/ })).toBeInTheDocument();
    const english = screen.getByRole("radio", { name: /English/ }) as HTMLInputElement;
    expect(english.checked).toBe(true);

    fireEvent.click(screen.getByRole("radio", { name: /日本語/ }));
    expect(onChange).toHaveBeenCalledWith("ja-JP");
  });
});
