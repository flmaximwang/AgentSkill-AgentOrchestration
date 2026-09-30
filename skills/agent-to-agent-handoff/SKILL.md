---
name: agent-to-agent-handoff
description: "Use when another agent shares the task or sends a handoff."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [multi-agent, handoff, review-loop, discord, profiles, collaboration]
    related_skills: [maintain-hermes-gateway, install-hermes-skills]
---

# Working a task that another agent shares with you

## When to Use

- One Discord message @-mentions several bots and assigns each a role ("you summarize, they build"), or the user describes a build-then-review loop between two agents.
- The other agent left a handoff / experience brief / spec in a shared repo and expects you to build
  from it and hand the project back for review.
- You are asked to review or approve work another agent produced against a checklist.
- A repo clone or a profile skill directory is shared with another session and may be edited mid-run.

Several Hermes profiles run as separate bots on this machine, in one guild, over one filesystem. The
user orchestrates them. Do not infer your role from message order or from who spoke last:
**every bot mentioned in a message receives it**, so one instruction reaches both sides and each
side tends to read it as its own job.

## Step 1 — Work out which agent you are, before acting

Input: the inbound message (thread id, sender id, mentions). Output: your own bot identity plus the
half of the work that is yours.

```bash
# which profiles this gateway serves, and the per-profile platform state
cat "$HERMES_HOME/gateway_state.json" | python3 -m json.tool | head -40

# profile -> bot identity: each profile carries its own token; ask Discord who it is
for f in "$HERMES_HOME/.env" "$HERMES_HOME"/profiles/*/.env; do
  tok=$(grep -m1 '^DISCORD_BOT_TOKEN=' "$f" | cut -d= -f2- | tr -d '"')
  [ -n "$tok" ] && { curl -s -H "Authorization: Bot $tok" https://discord.com/api/v10/users/@me \
    | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("id"), d.get("username"))'; \
    echo "   ^ $f"; }
done
```

`HERMES_HOME` is exported by the CLI and points at this profile's home — write every path below
through it, and re-derive it if the shell lost it
(`H="${HERMES_HOME:-$HOME/.hermes}"`, then use `"$H/…"`). Never echo a token — pipe it and print only
the filtered JSON. Then pin your own session: this profile's gateway log is
`$HERMES_HOME/logs/agent.log` (a named profile's home carries its own `logs/`); grep the inbound
message text or the thread id and read its `session=` field. `discord_threads.json` and `channel_directory.json` map a thread id back
to its chat.

If the two sides still look symmetric, use the asymmetric evidence: whose session carried the
original request, whose profile produced the existing artifacts, whose report the user has been
answering.

🔴 CHECKPOINT — identity first: touch no file in the shared repo until you know which side you are, and
never edit the artifact the other side is still writing.

## Step 2 — Read the whole handoff before building

Input: every file the other side left (spec, brief, its own notes). Output: the acceptance checklist,
plus the list of claims you will re-measure.

Handoffs arrive in pieces (page markers such as `(1/2)` / `(2/2)`) plus a long file in the repo. Read
the file end to end, including its "what I did not verify" rows — those are where your corrections
come from.

## Step 3 — Build to the handoff's acceptance checklist, and self-check it in code

Input: the checklist from Step 2. Output: the built artifact plus a per-item pass/fail line from the
script, not an assertion of compliance.

A reviewer's checklist is machine-checkable. Run it and report pass/fail per item instead of
asserting compliance — `scripts/check_skill_package.py <skill-dir | repo-root>` prints every item
below per skill (and the local scan verdict) and exits non-zero on any failure:

- directory name equals the SKILL.md frontmatter `name:`
- `description` opens with a self-contained trigger (`Use when <trigger>. <behaviour>.`) — the first
  ~57 characters must carry the routing signal on their own, because the index truncates there
- frontmatter parses as YAML; no unfilled placeholder marker (the checklist script's own word list:
  the three usual three-letter markers) left behind in any file
- every `references/…` link in every file resolves to an existing file
- for a skill-package deliverable, the install scan verdict predicted locally and reported as a
  verdict — load `install-hermes-skills` and follow its scan-gate reference for the command

## Step 4 — Verify the handoff's own claims; report every discrepancy

Input: the claims list from Step 2. Output: one line per claim — their value, your measured value, and
where you measured it.

This is the currency of the review loop. **Re-measure the handoff's numbers from the live sources
before writing them into the artifact**, and list each disagreement with the value you measured and
where you measured it. The spec author wants this; it is the difference between reviewing a document
and rubber-stamping it.

Drift classes measured so far: counts that moved since the brief was written (files added or deleted, rows
grown); a trap note contradicted by a later finding in the same document; a "current status" section
that a subsequent fix already invalidated; a flag or default the document describes that a newer
measurement overturned.

## Step 5 — Deliver, then stay in your role

Input: the verified artifact plus the Step 4 discrepancy list. Output: the filesystem handoff and the
4-section report.

- Hand the artifact back **through the filesystem** (the shared repo), not through chat prose — the
  reviewer needs a diff, not a summary.
- Report in the 4-section shape this user expects: **what you were asked / what you did / effect with
  measured numbers / what is left**. Lead the effect section with the corrections list. No tables.
- Do not self-approve, and do not answer the user's open questions for them: items the handoff routed
  to the user (naming, scope, out-of-repo documents) stay open until the user answers.
- State plainly what you did **not** do — unpushed commits, artifacts left untracked, tools not yet run.

🔴 CHECKPOINT — do not write "checklist passed" before the checklist has actually run, and do not
convert a failed item into a passing one.
🛑 STOP — publishing actions (push, merge, install, category change) wait for **both sides plus the
user**; a local commit is as far as a lone agent goes on its own.

## When a step fails — branch, do not improvise

Run the first column against reality; each row is a measured failure, not a hypothetical. Take the
middle column first, the right column only when that fails, and say in the report which row you took.

| trigger | first fix | still failing → fallback |
|---|---|---|
| Bot identity unavailable (token request 401 / no reply) | read the token field out of `"$HERMES_HOME/.env"` for that profile and retry the `/users/@me` call | fall back to file evidence: the profile's `logs/agent.log` plus `discord_threads.json` thread ownership; if that is also silent, ask the user which side you are and stop |
| `logs/agent.log` has no hit for this thread id | grep an inbound-message fragment (first ~40 characters of the message) instead of the thread id, and check for a rotated `agent.log.1` | use the production-side evidence — whose profile produced the artifacts already in the repo |
| Both sides' evidence is symmetric | do only the half of the message that names you unambiguously, and state the assumption in one line | 🔴 STOP: put both readings to the user and wait for an answer before touching anything |
| Acceptance checklist script fails (non-zero exit, no interpreter) | hand-run each item: directory name vs frontmatter `name`, description's first 57 chars, every `references/…` link exists, local scan verdict | write the failing items into the delivery report as failed — never reword them into passes |
| Install scan returns caution | rewrite the flagged literal (see Pitfalls) and rescan; meaning unchanged | report the block and hand it back to the author — a layout/content fix upstream, not a flag to bypass |
| Install scan returns dangerous | stop editing content; the flag cannot be forced | publish nothing; report the blocked verdict with the finding lines |
| push rejected (non-fast-forward) | keep the local commit, `git fetch`, and list the diverging commits to the reviewer | do not rebase or force-push; state the unpushed commit plainly in the report |
| Handoff's numbers disagree with your measurement | write the measured value into the artifact and list "their value vs mine + where I measured it" | if the disagreement changes **what** to build (not just a count), 🔴 STOP and ask the user |
| A tool the skill names is missing on this machine | complete the equivalent step by hand and label it degraded | never degrade silently: name the item that did not run |

## Ownership and concurrency rules

- **Commit locally; push only after both sides agree and the user decides.** Step the commits, one
  logical change each, so the reviewer can read them one at a time.
- **Never commit the other agent's artifact** (their handoff doc, spec, WIP). Leave it untracked and
  say so — staging it silently claims authorship and buries their intent.
- **Stage by pathspec.** A shared clone carries the other agent's unpushed commits and working-tree
  edits, and `git add -A` sweeps them into your commit.
- Before editing a file the other agent also touches: `git status` + `git fetch` first, and diff
  before overwriting a copy that may be ahead of yours.

## Pitfalls

- **A gateway posts its own progress notes into the thread** (running tool calls, "still working"
  ticks). They read like the other agent's messages — attribute by author id, never by content.
- **A plan is not the deliverable.** A handoff asks for a built, self-checked artifact; a summary of
  what you intend to build reads as no progress and wastes the round.
- **A false `caution` scan verdict is usually a documentation artefact, and a blocked install is a
  delivery failure.** The scan pattern `inline_shell_exec` is a bang-sign, a backtick, one non-space
  character, then another backtick — so an error literal ending in a bang-sign, written inside
  backticks and immediately followed by another code span, trips it. Write such literals (spreadsheet
  error values, bang-suffixed tokens) without backticks and rescan. Never ship around it by forcing
  the install.
- **"Keep this section as it stands" outranks your style preferences.** If the brief asks for
  verbatim preservation, preserve it and flag the change you would rather make instead of making it
  unilaterally.
- **A number from one project instance is evidence, not a constant.** Label every measured figure
  with the instance it came from; reviewers check exactly this, and "more general" must never cost a
  measured error string or a concrete digit.
