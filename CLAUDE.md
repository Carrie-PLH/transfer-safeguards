# transfer-safeguards — operating notes

## Doctrine — the long-horizon frame (read before optimizing anything)

Field Assembly is privately funded institution-building, not a startup. The
full thesis is ~/Projects/Field Assembly/field-assembly-standard/STEWARDSHIP.md;
the rules a working session must not violate are these four. Public access is
permanent and free: no gating, no analytics, no accounts, no advertising, at
any depth, ever. The endowment ceilings (~$6k/year, eventually ≤10 hours/week)
mean expansion never comes at the cost of maintaining what exists — a
collection that cannot be faithfully observed for years is a liability, not
progress. A competent stranger must be able to inherit everything: no
undocumented cleverness, no reliance on memory, no single-vendor dependence.
The corpus is designed to outlive Field Assembly LLC: portable, independently
verifiable, separable from its current custodian. Revenue, if it ever comes,
is upside, not oxygen — never redesign toward a buyer. Collection conventions
live in the Field Assembly Record Standard
(~/Projects/Field Assembly/field-assembly-standard).

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

## Provisioning status (updated 2026-08-30)

- Domain: roomandrecourse.com registered by the owner (2026-08-30 session
  handoff). Cloudflare worker: config scaffolded at site/wrangler.toml
  (worker name quiet-marram-7t2d, workers_dev false); the worker itself is
  created by the first `npx wrangler deploy`, which must wait for the site
  shell (index.html, assets/, about.html, legal/, 404.html — not yet
  built) and for the owner to ask. Domain binding happens in the dashboard
  outside wrangler.toml, per the sibling pattern.
- `tools/` adapted 2026-08-30: check-fidelity.py allowlist carries
  roomandrecourse.com (plus two advisory additions), build-status.py uses
  the "Notice periods and deadlines, as stated in the sources" marker and
  tracks the federal layer, render-state.py renders the Room & Recourse
  shell with federal.md → site/federal.html special-cased. See
  tools/README.md.
- Build/review skills exist: rr-state-page and rr-state-review (account
  skills, saved 2026-08-30).
- Iconography adopted 2026-08-30 from the owner's Room & Recourse lockup,
  following the Gathered Work pattern: site/assets/roomandrecourse-wordmark.svg
  (masthead and colophon) and site/assets/favicon.svg, both hand-authored in the
  original art's coordinates, with tools/make-icons.py redrawing the PNG and ICO
  icons from the same geometry. The source .png was deleted at the owner's
  direction once the SVGs were in place. SVG comments must not contain a double
  hyphen — the CSS token names do, and an XML parser rejects the file.
- Anchoring initialized 2026-08-30 (first chain entry 2026-08-30T144139Z,
  near-contemporaneous with the initial captures). Run
  `python3 tools/anchor.py run` after every capture or review session and
  commit anchors/; `upgrade` a day later; never edit anything under
  anchors/.

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
