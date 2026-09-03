# Handoff — port the pass-health cursor distinction to the sibling collections

Paste the block below into a new session. Everything it needs is either in the
prompt or reachable from the reference commit it names; it does not depend on
this conversation.

---

Port a fix from `~/Projects/Field Assembly/transfer-safeguards` to the sibling
collections that carry a copy of `tools/pass-health.py`. Check each of:

- `~/Projects/Field Assembly/sped-safeguards`
- `~/Projects/Field Assembly/licensure mobility`
- `~/Projects/Field Assembly/gathered work`

Work one repository at a time. Read its `CLAUDE.md` before touching it, commit
its work there, and never write to a repo you are not currently working in. A
repo with no `tools/pass-health.py` needs nothing — say so and move on.

## What the fix is

`pass-health.py` reported a missing `tools/review-cursor.txt` as a severe
finding unconditionally, on the assumption that a cursor exists to be lost. An
absent cursor means two opposite things:

- **The rotation ran and lost its place.** Severe. A pass must not restart the
  rotation on its own; the position gets reconstructed from `REVIEW-LOG.md` in
  a session with the owner.
- **The rotation never started.** A note, not a finding. There was no position
  to lose, and the first pass begins at the alphabetically first published
  slug — which is where it would have begun regardless.

On 2026-09-03 transfer-safeguards reported the second case as the first, and it
cost an evening establishing that nothing was wrong.

Two independent witnesses distinguish them, either sufficient: a
`REVIEW-LOG.md` (the append-only record a pass writes), and git having ever
tracked the cursor path. Neither present means never-initialized.

## Reference implementation

Commit `54e22b6` in transfer-safeguards, `tools/pass-health.py`. Read it with
`git show 54e22b6` before writing anything. It adds a `REVIEW_LOG` module
constant, a `cursor_ever_existed(cursor, log)` helper, a `log=` parameter on
`check()`, the branched finding, a docstring paragraph under item 2, and two
self-test cases.

Port the behavior, not the bytes. Each collection's paths, slugs and rotation
size differ, and at least one may name its log something else or not keep one
at all — in that case git history is the only witness and the helper still
works. Match the local file's own conventions.

Two properties matter and both are load-bearing:

1. `cursor_ever_existed` asks git about the cursor's own repository and must
   answer `False` rather than raise where there is no repository, no history,
   or no git. The self-test runs in a temporary directory and depends on this.
2. The severe branch's text must say the position was *lost* and must say not
   to let a pass restart the rotation silently. The old wording — "the rotation
   will restart at alabama" — is what read as a loss, and is the thing being
   fixed.

## Verification, before committing anything

Per repo, and do not skip the host run:

    python3 tools/pass-health.py --self-test
    python3 tools/pass-health.py

Then tripwire it on the host in that repo, both directions:

- Move its real cursor aside → expect **severe**, if that repo's cursor is in
  its git history or it has a `REVIEW-LOG.md`. Restore it.
- A path with neither witness → expect **note**.

Two host traps, both recorded in transfer-safeguards' `CLAUDE.md` and both hit
during this work:

- **The sandbox mount refuses `rm` and `mv` on tracked files.** The tripwire
  must run through Desktop Commander, on the Mac. Reading and running tools
  from the sandbox is fine.
- **The gate runs on bash 3.2, the sandbox on bash 5.** Irrelevant to this
  Python change, but if you touch any shell script while you are in there, run
  it through Desktop Commander before believing it.

## What not to do

Do not repair, restart, or reconstruct any rotation or cursor while you are in
there. If a sibling turns out to have a genuinely lost cursor, report it and
stop — that is an owner session, and the whole point of the distinction you are
porting. Do not deploy. Do not touch page content, checked dates, or any
routine prompt.

## Report

Per repository: whether it carried `pass-health.py`, whether it needed the
change, what its `pass-health.py` says now, the tripwire results in both
directions, and the commit hash. Then anything you found that is an owner
decision rather than a port.
