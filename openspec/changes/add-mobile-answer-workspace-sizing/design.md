## Context

On phones, the answer workspace is one item in a vertically scrolling grid. It currently has no mobile minimum height, so the question and generated answer receive too little visible space.

## Decisions

### Use a two-state mobile height control

The default answer height is `58dvh`, providing substantially more content without hiding the rest of the workflow. An explicit control expands it to `84dvh`; the same control restores the default height.

### Keep the answer component mounted

Expansion is represented by a local CSS class on the existing answer section. It does not replace the component or alter answer navigation, streaming, retry, or provenance state.

### Keep desktop behavior unchanged

The control is hidden above the phone breakpoint. Desktop and compact desktop windows continue to use the existing column divider.

## Non-goals

- Replacing the mobile page with tabs or a modal.
- Persisting the mobile height across browser restarts.
- Changing generated answer length.
