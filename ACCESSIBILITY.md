# Accessibility

AdLint includes a CLI, FastAPI service, reports, documentation, and a local Web
UI. Accessibility work in this repo focuses on making policy review usable for
keyboard-only users, screen reader users, low-vision users, and users who rely on
structured output.

## What we aim for

- CLI output remains useful without color and supports JSON for automation.
- Markdown reports use clear headings, tables, and descriptive links.
- The local Web UI supports keyboard navigation and visible focus states.
- Form fields have labels, descriptions, and useful error messages.
- Review decisions do not depend on color alone.
- Screenshots and docs include meaningful alt text.
- Motion or loading states avoid creating barriers.

## Reporting accessibility issues

Please open an accessibility issue if you find:

- unlabeled form controls or confusing focus order
- color-only severity or decision indicators
- reports that are hard to navigate with assistive technology
- CLI output that cannot be understood without color
- screenshots or docs without useful text alternatives

Include the command, page, browser, terminal, operating system, assistive
technology, and sample input when relevant. Do not include private ad copy,
customer data, credentials, or raw real submissions.

## Contribution expectations

UI changes should include a keyboard pass, visible-focus check, and
color-independent review of severity/status indicators. CLI/report changes
should preserve structured output and readable text output.
