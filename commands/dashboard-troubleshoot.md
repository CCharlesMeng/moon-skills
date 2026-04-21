---
name: dashboard-troubleshoot
description: Deep-link companion — structured troubleshooting from the visualization dashboard (symptom, source view, object id). Use when the user pastes dashboard context or runs this command after a dashboard deep link.
---

# Dashboard — troubleshoot

I see the following issue from the dashboard; help me triage and fix:

**Source view**: {{source_view}} (panorama / feature / requirement / health)  
**Object ID**: {{object_id}} (module id / feature id / requirement topic / immune asset id)  
**Symptom**: {{symptom}}

Please:

1. Warm context with **sync-context** for the relevant module(s).
2. Then route:
   - **Bug or regression** → **immune-debug** (structured root cause + immunity decision)
   - **Stale context** → **sync-context** incremental sync
   - **Immune asset decay** → **audit** then keep / update / deprecate

Replace the `{{...}}` placeholders with values from the deep link or ask the user briefly if missing.
