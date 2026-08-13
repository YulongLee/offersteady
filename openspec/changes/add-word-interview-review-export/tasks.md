## 1. Word document generation

- [x] 1.1 Add the browser DOCX generation dependency and isolated review export module
- [x] 1.2 Build the A4 Word document with session metadata, complete dual-role transcript and complete question/AI advice sections
- [x] 1.3 Add safe `.docx` filename generation, local Blob download and truthful empty states

## 2. Review page integration

- [x] 2.1 Replace the primary Markdown download action with “下载 Word”
- [x] 2.2 Add generating, success and recoverable failure states while preventing duplicate clicks
- [x] 2.3 Keep the privacy notice explicit that the sensitive review file is generated locally

## 3. Verification

- [x] 3.1 Add focused tests for OOXML structure, Chinese text, complete long content, empty states, filename and browser download behavior
- [x] 3.2 Generate a synthetic sample DOCX, render every page and visually inspect layout in accordance with the documents skill
- [x] 3.3 Run full Web tests, typecheck, production build, diff checks and strict OpenSpec validation
