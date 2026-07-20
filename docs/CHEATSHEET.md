SEEDS WORKFLOW CHEATSHEET                                v2026-06-12

  /its-alive  ->  [ work ]  ->  /kill-this  ->  /its-dead
                     ^                              v
                     +--- /pause-this <--- /restart-this


SESSION
  /its-alive       start. stamps time, opens session file, reads
                   context, recommends task. waits for confirmation.
  /pause-this      walking away. build check + WIP commit.
  /restart-this    resume from /pause-this. reloads context.
  /kill-this       end pt 1. build + commit + PR + @code-review.
  /its-dead        end pt 2. stamps ended, tallies points,
                   shows wall_clock gut-check, finalizes file.

PHASE
  /start-phase     materialize current phase as Issues
                   ( phase:N + points:X labels )
  /retro           close phase. mark [x], reconcile drift,
                   compute throughput, write retro, bump minor.

SEMVER  ( dev projects only — needs package.json )
  /bump-major      breaking change. manual. tag on main.
  /promote-production main->prod ff-merge + push.
                   ( needs origin/production — DEC-S022 )
  patch bumps      automatic in /its-dead on PR merge.

REFLECT / SYNC
  /read-the-tape   scan a session for anti-patterns.
                   arg: number, file path, or none = latest.
  /push-seeds      backport workflow wins to seeds.
  /pull-seeds      pull seeds improvements into this project.
                   gated on `seeds-version` match.

INFRA                              DOMAIN
  /update-config                     /stripe-best-practices
  /fewer-permission-prompts          /stripe-projects
  /keybindings-help                  /upgrade-stripe
  /session-start-hook                /claude-api
  /simplify
  /loop <interval> <cmd>           BUILT-IN
  /init                              /review
                                     /security-review

DEV IDENTITY      ~/.claude/devname  ( one line, e.g. "eric" )
SESSION FILE      sessions/YYYY-MM-DD-HHMM-<dev>-<slug>.md
TRANSCRIPT PATH   in YAML frontmatter, captured at /its-alive


THE SHORT VERSION
  start of work:     /its-alive
  break:             /pause-this    ->  /restart-this
  end of work:       /kill-this     ->  /its-dead
  start of phase:    /start-phase
  end of phase:      /retro
  after a rough one: /read-the-tape
  after a good one:  /push-seeds
  refresh template:  /pull-seeds
