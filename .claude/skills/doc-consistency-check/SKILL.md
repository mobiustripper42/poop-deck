---
name: doc-consistency-check
description: Cross-references factual claims across the project's doc set (`docs/*.md` + root `CLAUDE.md`) and flags mismatches. Report-only — proposes no edits, no restructuring. Use mid-project anytime docs feel like they've drifted apart, before a phase boundary, or after a session that touched multiple docs at once.
tools: Agent
---

You are executing the /doc-consistency-check skill.

Invoke the @doc-consistency agent with the project context:

> Run a doc consistency sweep on this project. Scope is `<project-root>/docs/*.md` and `<project-root>/CLAUDE.md`. Read `<project-root>/.claude/project-type` to decide how to interpret `docs/BRAND.md` (webapp must declare brand; tool must justify any "not used"; either way, literal `PLACEHOLDER` is always a finding).
>
> Follow your defined output format exactly. Report findings only. Do not propose structural changes, file ownership recommendations, DEC numbering changes, or any edits — these are explicitly out of scope. If you notice an out-of-scope issue worth knowing about, list it once in the `## Out of scope (not investigated)` tail section and stop.

Pass any additional arguments or context from the user to the agent alongside the above.

After the agent returns its report, present the report to the user verbatim. Do not summarize or compress it — the report's specificity (file:line refs, verbatim quoted strings) is its value. If there are zero findings, that is a valid full report; relay it as-is.

Do not ask "want me to fix these?" — the fix is the user's call, on their own clock. End the skill once the report is shown.
