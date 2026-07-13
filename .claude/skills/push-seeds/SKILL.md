---
name: push-seeds
description: Syncs workflow improvements from the active project back to the seeds template repo. Invokes the @sync-config agent to classify diffs, propose backports, and flag cross-family patterns.
tools: Agent
---

You are executing the /push-seeds skill.

Invoke the @sync-config agent with an explicit direction parameter and context:

> Run in PUSH direction. Source: this project's working tree (run from `$(git rev-parse --show-toplevel)`). Target: the seeds template repo (sibling default: `$(git rev-parse --show-toplevel)/../seeds`; also check `$SEEDS_REPO` env var).
>
> Diff each relevant file pair (project vs seeds template) per your Step 1 rubric. Classify per your Step 2 rubric. For each structural improvement present in the project but not in the template, show the diff and ask "Backport to seeds? (y/n)". Leave project-specific customizations alone.
>
> When backporting, replace project-specific strings with generic tokens per your Step 4 PUSH rules.
>
> Report which files changed, which were skipped, and any cross-family patterns flagged.

Pass any additional arguments or context from the user to the agent alongside the above.
