---
name: lean
description: Cut and tighten the current branch before it is pushed. Finds code that does not need to exist, duplicates something already in the repo, or makes the code harder to read, and applies the cuts that keep behavior. Quality and size only; correctness bugs are the PR bot's. Use when Drew says "lean", "tighten this", "cut this down", "quality pass", or before the first push of any PR that changes code (the game repo's FEAT-352, adapted for this pipeline).
---

# Lean pass (MapPacker)

One pass over the branch diff, by you, inline. No subagents unless the diff is over about 800 changed lines (then one Explore agent per top-level folder, each given only its slice of the diff). Read the diff and the files it touches, nothing else unless a rule below sends you there.

## 1. Scope
- `git diff --stat origin/main...HEAD`, then `git diff origin/main...HEAD -- <files>`. Uncommitted work: add `git diff HEAD`.
- Review only added or changed lines. Old code is out of scope unless the change makes it dead or duplicates it.
- Skip docs-only diffs: say so and stop.

## 2. The ladder (for every new function, class, module, option or branch)
Take the first rung that holds and flag the code if a higher rung was available:
1. Does it need to exist? (Not asked for by the card, no caller, "for later".)
2. Is it already in this repo? This rung saves the most: grep `pipeline/` for the name and for the idea (a smoothstep, a raster sample, a tile writer, a cost field, a Dijkstra, a hash). Link the existing one.
3. Does the standard library, numpy or scipy (already used) do it?
4. Does an installed dependency do it? (`pipeline/requirements.txt` only; never add one for this.)
5. Can it be a few lines instead of a module?

## 3. Structure checks
- **File size:** a file that crosses 1,000 lines in this diff is a finding. A file already over it (`pipeline/build_pack.py`, `pipeline/resort.py`, `pipeline/pack_report.py` today) may grow only by wiring, about 20 lines, with the logic in a new module; past that, split first. Either way, search the board for a split card and file one if none exists (the game's `docs/BOARD.md` rule 3), so a reason in the PR is never the end of it.
- **Code judo:** a restructure that keeps behavior and removes code (merge two near-copies, replace a flag-driven branch with data, delete a wrapper that only forwards).
- **Spaghetti:** one-off `if` checks for a special case dropped into shared code; a stage's logic leaking into `packwriter.py` or another stage that does not own it.
- **Magic:** clever indirection, string-keyed dispatch, or hidden module state where a direct call would read plainly.
- **Vectorise:** a Python loop over raster cells or points where a numpy expression does the same; a per-cell loop in a hot stage is a finding.
- **Names and numbers:** a bare number with units gets a named module constant (`ANGLE_K`, `R_MIN`); a name that needs a comment to explain it gets renamed.
- **Comments:** keep the why, cut the what. A known limit taken on purpose gets `# shortcut: <limit>, <when to revisit>` and a board card, not just the comment.

## 4. Never cut
Pack format and `FORMAT_VERSION` handling, `pack_lint.py` and contract checks, publish safeguards (`publish_pack.py` refusals), coordinate and CRS conversions, error handling that stops silent wrong output, determinism (seeded randomness, stable ordering), or anything the card asked for.

## 5. Apply
- Sort findings: structural regressions, missed code judo, spaghetti, slow loops, size, names. Keep at most 8; drop nits a reader would not miss.
- Apply the ones that keep behavior and are local to the diff. Then `python -m pytest pipeline/tests`. If the change alters pack output, say which pack report value or rebuilt file would prove nothing moved; do not rebuild unless Drew asks.
- Leave the rest as a list for Drew with the file and line and one line on why.

## 6. Report (short)
```
Lean: -<n> lines (<before> to <after>), <k> cuts applied, <m> left for you.
Applied: <file:line> <what>   (one line each)
Left:    <file:line> <what, why it needs you>
Not checked: <what you skipped, e.g. pack output, the game side>
```
