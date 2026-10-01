import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { DeferredVideo } from "./DeferredVideo";

describe("promotional media loading", () => {
  afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });
  const props = { label: "Synthetic demo", poster: "/test-poster.jpg", src: "/test-demo.mp4" };

  it("loads the poster near the viewport but the video only on explicit activation", () => {
    let intersect!: IntersectionObserverCallback;
    const disconnect = vi.fn();
    vi.stubGlobal("IntersectionObserver", class {
      constructor(callback: IntersectionObserverCallback) { intersect = callback; }
      observe = vi.fn(); disconnect = disconnect;
    });
    const play = vi.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue();
    const { unmount } = render(<DeferredVideo {...props} />);
    const video = screen.getByLabelText(props.label);
    expect(video).not.toHaveAttribute("src");
    expect(video).not.toHaveAttribute("poster");
    expect(video).toHaveAttribute("preload", "none");
    act(() => intersect([{ isIntersecting: true } as IntersectionObserverEntry], {} as IntersectionObserver));
    expect(video).toHaveAttribute("poster", props.poster);
    expect(video).not.toHaveAttribute("src");
    expect(play).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: `Play ${props.label}` }));
    expect(video).toHaveAttribute("src", props.src);
    expect(video).toHaveAttribute("controls");
    expect(play).toHaveBeenCalledOnce();
    unmount();
    expect(disconnect).toHaveBeenCalled();
  });

  it("remains operable without an observer and preserves controls when autoplay is rejected", async () => {
    vi.stubGlobal("IntersectionObserver", undefined);
    vi.spyOn(HTMLMediaElement.prototype, "play").mockRejectedValue(new Error("gesture required"));
    render(<DeferredVideo {...props} />);
    expect(screen.getByLabelText(props.label)).not.toHaveAttribute("poster");
    fireEvent.click(screen.getByRole("button", { name: `Play ${props.label}` }));
    expect(await screen.findByRole("status")).toHaveTextContent("Use the video controls");
    expect(screen.getByLabelText(props.label)).toHaveAttribute("controls");
    expect(screen.getByRole("link", { name: "Open video" })).toHaveAttribute("href", props.src);
  });
});
