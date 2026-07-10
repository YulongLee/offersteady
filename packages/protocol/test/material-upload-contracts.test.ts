import { describe, expect, it } from "vitest";

import { detectMaterialUploadFormat, isMaterialUploadMimeAllowed, materialUploadAccept, materialUploadFormatLabel, materialUploadFormats } from "../src";

describe("material upload contracts", () => {
  it("keeps one canonical registry for supported upload formats", () => {
    expect(materialUploadFormats.map(item => item.id)).toEqual(["pdf", "docx", "doc", "txt", "md"]);
    expect(materialUploadAccept).toBe(".pdf,.docx,.doc,.txt,.md");
    expect(materialUploadFormatLabel).toBe("PDF、DOCX、DOC、TXT、MD");
  });

  it("detects supported formats from filenames", () => {
    expect(detectMaterialUploadFormat("resume.PDF")).toBe("pdf");
    expect(detectMaterialUploadFormat("job-description.docx")).toBe("docx");
    expect(detectMaterialUploadFormat("notes.md")).toBe("md");
    expect(detectMaterialUploadFormat("archive.zip")).toBeNull();
  });

  it("accepts known MIME types and allows blank browser MIME values", () => {
    expect(isMaterialUploadMimeAllowed("pdf", "application/pdf")).toBe(true);
    expect(isMaterialUploadMimeAllowed("doc", "application/msword")).toBe(true);
    expect(isMaterialUploadMimeAllowed("md", "text/plain")).toBe(true);
    expect(isMaterialUploadMimeAllowed("pdf", "")).toBe(true);
    expect(isMaterialUploadMimeAllowed("pdf", "image/png")).toBe(false);
  });
});
