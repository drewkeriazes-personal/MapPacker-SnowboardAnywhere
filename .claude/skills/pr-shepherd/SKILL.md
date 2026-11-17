---
name: pr-shepherd
description: Keep every open PR in MapPacker and the game repo mergeable while Drew merges them one after another. Sends a background agent to each PR with a problem (merge conflicts with main, failing checks), then watches both repos' main and sends agents again whenever a merge leaves a still-open PR conflicting. Use when Drew says "shepherd the PRs", "keep the PRs mergeable", "resolve conflicts as I merge", "babysit the open PRs" or calls /pr-shepherd.
---

# PR shepherd (pointer, FEAT-327)

The skill lives in the game repo, so there is one copy for both repos: `.claude/skills/pr-shepherd/` in drewkeriazes-personal/SnowboardAnywhere (FEAT-324; FEAT-326 made it cover this repo too). It watches and fixes PRs in both repos whichever one you start from.

1. Find it in the sibling game clone: `C:\Users\Drew\git\SnowboardAnywhere\.claude\skills\pr-shepherd\SKILL.md` (the main checkout, found at `../SnowboardAnywhere` next to this one; `SBA_GAME_REPO` overrides).
2. If that checkout hasn't pulled it yet (no `repos.sh` next to it), don't pull there: other sessions keep uncommitted work in it. Export `main`'s copy into your scratchpad instead and use that folder:
   `git -C C:\Users\Drew\git\SnowboardAnywhere fetch origin` then `git -C C:\Users\Drew\git\SnowboardAnywhere archive origin/main .claude/skills/pr-shepherd | tar -x -C <scratchpad>`.
3. Read that `SKILL.md` and follow it from the top. It is written from the game repo's side, but its scripts and agent brief cover both repos (tag `MP` is this one).
