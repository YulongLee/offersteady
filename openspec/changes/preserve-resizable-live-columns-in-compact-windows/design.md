## Context

React and CSS currently switch at 1050px. React unmounts `WorkspaceDivider` and CSS forces the focused grid into rows, causing the reported behavior.

## Decisions

### Keep split mode through compact desktop widths

The split workspace remains active above 720px, aligning the structural change with the existing phone breakpoint.

### Use adaptive minimum widths

At 900px and above, existing 320px/420px ratio bounds remain. Between 721px and 899px, bounds use 240px/300px minimums so resizing remains useful.

### Keep phone behavior unchanged

At 720px and below, the divider remains absent and the current ordered stacked layout remains.

## Non-goals

- Adding detachable windows or browser-window controls.
- Changing conversation, answer, audio, screenshot, or billing behavior.
- Persisting layout preference on the server.
