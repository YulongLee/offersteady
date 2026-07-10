# Verification Record

## Capability scenario review

### Streamlined interview entry

- The dashboard renders exactly one `继续面试` action and resolves preparing, active, recoverable and ended sessions through one state-to-route function.
- Preparation uses the account material collection shared with the materials page, preserves empty or partial confirmation, and blocks invalid saved selections without substituting another source.
- Starting an interview does not implicitly authorize audio capture. Screenshot submission still requires its dedicated preview confirmation.
- Covered by dashboard, preparation, material-action and route regression tests.

### Simplified session data controls

- Settings no longer expose an unsupported record-retention selector or expiry promise.
- The interface continues to state that raw audio is not saved by default and links to the usage guide for session-data management.
- Screenshot and whole-interview deletion retain success, failure and retry behavior on the review page.
- Covered by settings and state regression tests.

### Resizable live interview workspace

- The live material rail and live material adjustment command are absent; confirmed material provenance remains visible with answers.
- Desktop renders one conversation column and one answer/action column separated by an accessible, pointer- and keyboard-operable divider.
- The split ratio is versioned and scoped to the interview session, validated on restore, and constrained by the measured minimum column widths.
- Tablet and phone layouts stack the same component instances and remove the divider from both the layout and accessibility tree.
- Covered by workspace utility/component tests and browser review at phone, tablet, 1200 px and 1440 px widths.

## Open-question disposition

- The default desktop split is `42 / 58`; browser review confirmed it leaves both columns usable at the supported desktop widths.
- Live material changes are intentionally excluded from this change. Users confirm an empty, partial or complete material set before starting, and that revision remains fixed for the session.
- No capability scenario is intentionally deferred from the approved scope.
