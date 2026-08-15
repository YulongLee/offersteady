import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { ContextPicker } from "./ContextPicker";


describe("ContextPicker material downloads", () => {
  it("downloads a material without changing its selected state", () => {
    const onDownload = vi.fn();
    const onSave = vi.fn();
    render(
      <MemoryRouter>
        <ContextPicker
          sources={[{
            id: "knowledge-1",
            documentId: "knowledge-1",
            ownerUserId: "user-1",
            kind: "knowledge",
            displayName: "面试准备 (2).md",
            version: "v1",
            status: "ready",
            selectable: true,
            updatedAtMs: 1,
            summary: "已建立索引",
          }]}
          selection={{
            sessionId: "session-1",
            resumeSourceId: null,
            jobDescriptionSourceId: null,
            knowledgeSourceIds: ["knowledge-1"],
            revision: 1,
            confirmedAtMs: 1,
          }}
          onSave={onSave}
          onDownload={onDownload}
        />
      </MemoryRouter>,
    );

    const checkbox = screen.getByRole("checkbox") as HTMLInputElement;
    expect(checkbox.checked).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "下载 面试准备 (2).md" }));
    expect(onDownload).toHaveBeenCalledWith(expect.objectContaining({ id: "knowledge-1" }));
    expect(checkbox.checked).toBe(true);
    expect(onSave).not.toHaveBeenCalled();
  });
});
