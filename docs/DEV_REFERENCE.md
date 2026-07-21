# Dev Reference

Reference material pulled out of the always-loaded `CLAUDE.md` shell (DEC-S031) — read when you need it, not every session.

## `<VersionTag />` component

Build-time version display, reads `process.env.NEXT_PUBLIC_APP_VERSION` + `process.env.NEXT_PUBLIC_VERCEL_GIT_COMMIT_SHA`. Renders e.g. `v1.2.3 (a1b2c3)`.

Wiring:
- `next.config.ts` (or `next.config.js`) forwards `npm_package_version` → `NEXT_PUBLIC_APP_VERSION`. Critical — without `NEXT_PUBLIC_`, client trees silently render `v0.0.0`.
- Wire into login screen and footer.
- Vercel sets `NEXT_PUBLIC_VERCEL_GIT_COMMIT_SHA` automatically. Local `npm run dev` outside Vercel omits the commit hash — that's intentional.

```tsx
import { VersionTag } from "@/components/VersionTag";
<VersionTag className="text-xs text-muted-foreground" />
```

## CHANGELOG.md

Auto-maintained by `/retro` and `/bump-major` (DEC-S013 — `/its-dead` no longer touches it). Don't edit by hand mid-flow — the skills always prepend after the `# Changelog` header. The first bump creates the file if absent.

Format (Keep-a-Changelog inspired but simpler):
```
# Changelog

## [1.2.3] - 2026-05-05
- PR #42: Add login form

## [1.2.2] - 2026-05-04
- PR #41: Fix dashboard query
```

## PR Review on Mobile (developer notes)

Doing PR reviews from your phone is tolerable if you structure for it:
- **GitHub mobile app, not web.** The native app's diff + approve + merge flow is usable. The mobile web is not.
- **Tap the preview URL first.** Vercel posts it as a comment. 60 seconds of clicking the actual feature catches more than reading the diff would.
- **Enable auto-merge.** Repo Settings → enable auto-merge, then "Enable auto-merge" on each PR. Checks pass → it merges itself. One less thing to remember to do.
- **Branch protection:** require CI green (Vercel build + Playwright). Skip reviewer count requirements for solo dev — they add friction with no benefit.
- **Checklist PR descriptions.** `/kill-this` should populate: does this PR have a migration? RLS change? UI change at 375px? A checkbox list is fast to scan on a small screen.
- **`gh` CLI on your dev server** is faster than any UI when you're at a keyboard: `gh pr list`, `gh pr view 42 --web`, `gh pr merge 42 --auto`.
