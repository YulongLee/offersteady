## 1. Guidance Copy Alignment

- [x] 1.1 Add visible upload-format guidance to the resume, JD, and knowledge sections of the materials page so users can see supported file types on entry
- [x] 1.2 Keep the format list consistent across main page copy, empty states, and upload dialogs, while separately describing JD text pasting

## 2. Upload Control Consistency

- [x] 2.1 Review and align the `accept` file-type configuration with the documented support list `pdf/docx/doc/txt/md`
- [x] 2.2 Ensure the UI copy does not imply new parsing, indexing, or pricing behavior beyond file-format support

## 3. Verification

- [x] 3.1 Add or update frontend tests proving users can see the supported format guidance when entering the materials page and when opening upload dialogs
- [x] 3.2 Run `openspec validate add-material-upload-format-guidance --strict`
