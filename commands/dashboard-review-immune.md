---
name: dashboard-review-immune
description: Deep-link companion — when an immune asset is marked needs-review in the dashboard, run audit to keep, update, or deprecate the rule. Use when the user opens this command with dashboard-filled placeholders or immune decay signals.
---

# Dashboard — immune asset review

The dashboard shows immune assets marked **needs-review** (decay / stale review).

**Asset ID**: {{asset_id}}  
**Confidence**: {{confidence}}  
**Last checked at**: {{last_checked_at}}  
**Reason**: Past decay threshold without review.

Please use **audit** on this immune asset and decide:

1. **keep** — Rule still valuable; refresh `last_checked_at`
2. **update** — Adjust scope or wording of the rule
3. **deprecate** — Rule is obsolete; mark **deprecated**

Replace the `{{...}}` placeholders with values from the deep link or user input if they are still placeholders.
