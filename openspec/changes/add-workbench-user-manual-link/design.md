## Context

The authenticated application renders desktop and mobile navigation from one internal-route array. The existing “使用说明” item is an application route and must remain available. The requested manual is a Feishu Drive folder maintained outside the product, so it needs different navigation semantics from React Router links.

## Goals / Non-Goals

**Goals:**

- Provide a clearly named “用户手册” workbench entry on desktop and mobile.
- Keep the current application and any live interview open when the manual is launched.
- Protect the opener context when navigating to the external origin.
- Keep the destination centralized and regression tested.

**Non-Goals:**

- Embedding, proxying, indexing, or authenticating the Feishu content.
- Replacing the existing internal “使用说明” route.
- Adding Backend configuration, an admin editor, or analytics tracking for the link.
- Changing public-site manual links.

## Decisions

### 1. Model external navigation separately from application routes

Keep the existing internal `navItems` unchanged and define a dedicated user-manual URL and link element. A React Router `NavLink` was rejected because the destination is a different origin and must not be treated as a client-side application route.

### 2. Open the manual in a new protected tab

Use `target="_blank"` with `rel="noopener noreferrer"`. This preserves a live or prepared interview in the original tab and prevents the external page from controlling `window.opener`. Same-tab navigation was rejected because returning could lose transient workspace context.

### 3. Show the entry in both responsive navigation surfaces

Render the external entry after “使用说明” in desktop and mobile navigation. Increase the mobile navigation grid from seven to eight columns so the existing account control and all current entries remain present; no route is removed or reordered beyond inserting the manual beside related help content.

## Risks / Trade-offs

- [The Feishu folder later requires login or loses sharing permission] → The product still opens the exact maintained destination; sharing permissions remain an operational responsibility outside this code change.
- [Eight mobile navigation columns reduce each target width] → Preserve the existing 60px height and compact label style, and cover the link through DOM regression tests without changing other navigation behavior.
- [The destination changes later] → Keep it as one named Web constant so a future update is isolated.

## Migration Plan

Deploy the Web bundle only. Rollback restores the previous Web bundle; no persisted state, Backend, desktop application, or data migration is involved.

## Open Questions

None for the supplied destination and requested workbench scope.
