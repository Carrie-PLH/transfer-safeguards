# transfer-safeguards — operating notes

Working notes for Claude sessions in this repository. Content rules live in
CHARTER.md (page specification, hard boundaries) and PROVENANCE.md (packet
and quotation rules); this file covers only how to run commands against
this folder and how the site will ship. Fourth Field Assembly database,
after Gathered Work, Rules & Record (sped-safeguards), and Board & Border
(~/Projects/Field Assembly/Licensure Mobility). When a convention question
is not answered here, licensure-mobility is the nearest sibling and its
answer usually transfers.

## Run host commands through Desktop Commander

Anything that touches the git repository or Cloudflare should run through
the Desktop Commander MCP (`mcp__Desktop_Commander__start_process` and its
companions), which executes on the Mac itself with the real filesystem, the
real `~/.wrangler` session, and the real git config.

## The sandbox shell cannot do host-credentialed work

The sandboxed Linux shell reaches sibling folders through mounts, but it
does not share the Mac's home directory. `npx wrangler deploy` fails there
demanding `CLOUDFLARE_API_TOKEN`. Do not work around this by hunting for a
token — run the command through Desktop Commander instead. The same applies
to anything else expecting host credentials or host config. Note also that
this folder is not currently mounted into the Cowork sandbox at all; until
it is added as a connected folder, all reads and writes here go through
Desktop Commander.

## Prefer host-side writes to this folder

In-place rewrites through a mount (`perl -i`, `sed -i`) strand
`.fuse_hidden…` debris and stale `.git/index.lock` files in the siblings.
Write through Desktop Commander or the Read/Write/Edit file tools. Python
tools in `tools/` are safe to *run* from a sandbox mount (they read and
write whole files); avoid sandbox-side in-place edits of tracked files.

## Not yet provisioned (as of 2026-08-29 scaffold)

- roomandrecourse.com: unregistered at scaffold time; register before any
  public naming. No Cloudflare worker exists yet; create per the sibling
  pattern (Workers static assets, domain bound in the dashboard outside
  wrangler.toml, `workers_dev` false) when the first pages are ready.
- `tools/` is copied from licensure-mobility as a starting point and NOT
  yet adapted: check-fidelity.py's allowlist must gain roomandrecourse.com,
  build-status.py's full-page marker must match this charter's heading
  ("Notice periods and deadlines, as stated in the sources"), and the
  docket-row logic in build-status.py / render-state.py must match the
  five-row docket in CHARTER.md. Adapt before first use; do not trust a
  passing run from unadapted tools.
- No build/review skills exist yet (sibling pattern: sped-state-page /
  lm-jurisdiction-page and their review twins). Create once the exemplar
  pages have settled the format.
- Anchoring (tools/anchor.py, anchors/) starts after the first real
  evidence exists, per the Gathered Work scheme.

## Deploy only when asked, and only on a passing check

Once the worker exists, the gate follows the siblings:
`bash site/predeploy-check.sh && (cd site && npx wrangler deploy)` — deploy
only if the check passes and only if the owner asked in that session.
Verify afterwards by fetching changed pages with `curl -sSL` rather than
trusting the deploy log.

## Fidelity before anything ships

A page that has not passed `python3 tools/check-fidelity.py` against its
packet(s) — markdown and HTML both, zero failures — is not done. There is
no expected miss.
