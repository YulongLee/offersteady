## ADDED Requirements

### Requirement: Authenticated workbench SHALL expose the maintained user manual
The authenticated workbench SHALL display a navigation entry named `用户手册` on both desktop and mobile navigation surfaces. The entry MUST point to `https://pwksrh0z1i6.feishu.cn/drive/folder/KFlcfWorslX2hmdyyByc2fLvngp?from=from_copylink` and MUST NOT replace the existing internal `使用说明` entry.

#### Scenario: User views authenticated workbench navigation
- **WHEN** an authenticated user opens any workbench route
- **THEN** both responsive navigation surfaces contain a `用户手册` link with the configured Feishu folder destination while `使用说明` remains available

### Requirement: External manual navigation SHALL preserve the workbench
The user-manual entry MUST open in a new browsing tab and MUST apply opener-isolation attributes suitable for an external origin.

#### Scenario: User opens the user manual
- **WHEN** the user activates the `用户手册` entry
- **THEN** the browser opens the Feishu folder in a new tab using `noopener` and `noreferrer`, and the current workbench remains open
