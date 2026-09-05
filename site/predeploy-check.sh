#!/bin/bash
# transfer-safeguards — pre-deploy invariants check (internal, never deployed)
# Run from site/ before `npx wrangler deploy`. Exit 0 = safe to deploy.
# Adapted from the Gathered Work check. Verifies, mechanically:
#   1. No reviewer placeholders remain in any deployable HTML file.
#   2. Zero third-party requests: no loaded resource (script, stylesheet,
#      image, font, iframe, media) points off-domain. Ordinary <a href>
#      links to sources are allowed and expected.
#   3. No advisory language outside verbatim quotation.
#   4. WCAG 2.1 AA contrast holds for every colour token, on every ground.
#   5. The generated state-picker markers are present where the generator
#      expects them.
#   6. .assetsignore still excludes the internal files.
#   7. Every page carries the colophon footer.
#   8. Every page carries the skip link and its target (WCAG 2.4.1).
#   9. Every state page has a packet, globbed as <slug>-packet*.txt.
#  10. Every published state page has a row in states/index.html and a record
#      in the STATES JSON, and both carry the date the page itself publishes.
#  11. The generated state picker markup is current.
#  12. Nothing under the deploy root but the kinds of file this site
#      publishes — an allowlist, so tool debris fails without anyone having
#      had to anticipate it.
# (Per-page quotation fidelity is tools/check-fidelity.py, run per page at
# build time; this script gates the deploy as a whole.)
cd "$(dirname "$0")" || exit 1
fail=0

say()  { printf '%s\n' "$*"; }
bad()  { printf 'FAIL  %s\n' "$*"; fail=1; }
ok()   { printf 'ok    %s\n' "$*"; }

# Deployable HTML only — paths excluded from deploy are excluded here too.
# NUL-delimited: an unquoted word-split over these paths invents filenames.
HTML0() { find . -name '*.html' -not -path './.wrangler/*' -not -path './node_modules/*' -print0; }
HTML=$(find . -name '*.html' -not -path './.wrangler/*' -not -path './node_modules/*')
PAGES=$(printf '%s\n' "$HTML" | grep -c '')

# 1 — reviewer placeholders (bracketed template wordings only; the standing
# "review pending before publication" change-log line is legitimate content)
RPLACE='\[named human reviewer|\[pending review before publication|\[reviewer'
if grep -lE "$RPLACE" $HTML >/dev/null 2>&1; then
  bad "reviewer placeholder still present in:"
  grep -lE "$RPLACE" $HTML | sed 's/^/        /'
else
  ok "no reviewer placeholders"
fi

# 2 — external loaded resources. Loads from the site's own domain are
# allowed; everything else off-site fails. Ordinary <a href> links are not
# loads and are expected.
ext=$(grep -Eon '<(script|link|img|iframe|embed|object|source|video|audio)[^>]*(src|href)="https?://[^"]*"' $HTML 2>/dev/null \
      | grep -v 'https\?://roomandrecourse\.com' || true)
if [ -n "$ext" ]; then
  bad "external loaded resource(s) found:"
  printf '%s\n' "$ext" | sed 's/^/        /'
else
  ok "no external loaded resources in HTML"
fi
cssext=$(grep -Eon '@import|url\(\s*["'\'']?https?://' assets/*.css 2>/dev/null || true)
if [ -n "$cssext" ]; then
  bad "external reference(s) in CSS:"
  printf '%s\n' "$cssext" | sed 's/^/        /'
else
  ok "no external references in CSS"
fi

# 3 — advisory language (the product's hard boundary). Verbatim source
# quotations are exempt: state materials legitimately say "you should" and
# "you must submit", and reproducing that faithfully is the whole product.
#
# The exemption used to work line by line — a line beginning with a quotation
# mark was taken to be a quoted passage. That fails on this project's rendered
# pages, which are a single line, so one quotation put the entire file outside
# the exemption. New Hampshire tripped it on 2026-09-01 quoting the notice RSA
# 151:26 requires, which tells a resident "If you think you should not have to
# leave this facility, you may file an appeal" — the state's own words.
#
# Masking quoted spans the way check 3b does is the fix, and it is stricter as
# well as more accurate: it also catches advisory prose sharing a line with a
# quotation, which the line rule let through. Tags come out first, because in
# rendered HTML every attribute delimiter is also a double quote and parity
# counted on raw markup inverts at the first tag.
#
# Tripwire before trusting any change to this, in both directions — a check
# that never fires looks exactly like a clean corpus:
#   inject <p>You should file within 30 days.</p> into a page  -> must FAIL
#   inject <p>The state wrote "you should appeal" here.</p>    -> must PASS
adv=$(for f in $HTML; do
       perl -0777 -pe 's/<[^>]*>/ /g; s/&quot;/"/g; s/[\x{201C}][^\x{201D}]*[\x{201D}]//g; s/"[^"]*"//g;' "$f" \
         | grep -Ein 'you should|we recommend|your deadline|be sure to|you qualify|we advise|you need to file' \
         | sed "s|^|$f:|"
     done 2>/dev/null | cut -c1-160 || true)
if [ -n "$adv" ]; then
  bad "advisory language found:"
  printf '%s\n' "$adv" | sed 's/^/        /'
else
  ok "no advisory language"
fi

# 3b — house spelling: license, not licence, in the project's own prose.
#
# Field Assembly house style is American spelling (field-assembly-standard/
# STYLE.md). This is a gate rather than a note because a note is only as good
# as whoever remembers to read it, and this drift is invisible: "licence" reads
# as correct to a large share of English speakers, nothing downstream complains,
# and it accumulates. Board & Border reached 408 occurrences across 31
# published pages before anyone noticed; Gathered Work carried 33 more.
#
# Quotations are exempt, and that exemption matters more here than in the
# advisory check. Sources do write "licence", and correcting a quoted one would
# be falsifying a source to satisfy a style rule — a worse fault than the
# inconsistency it tidies. Quoted spans come out before the scan, tags first:
# in rendered HTML every attribute delimiter is also a double quote, so parity
# counted on raw markup inverts at the first tag and the check would protect
# prose while rewriting quotations, exactly backwards.
#
# Known gap, deliberate: text inside attributes is not scanned, because tags
# are masked. A meta description is prose living in an attribute and is invisible
# to this check. Gathered Work had two; they were found by hand.
#
# Tripwire before trusting any change to this, in both directions — a check that
# never fires looks exactly like a clean corpus:
#   inject <p>The licence is issued.</p> into a page  -> must FAIL
#   inject <p>The board wrote "your licence" here.</p> -> must PASS
sp=$(for f in $HTML; do
       perl -0777 -pe 's/<[^>]*>/ /g; s/&quot;/"/g; s/[\x{201C}][^\x{201D}]*[\x{201D}]//g; s/"[^"]*"//g;' "$f" \
         | grep -Ein '\blicenc(e|es|ed|ing)?\b' \
         | sed "s|^|$f:|"
     done 2>/dev/null | cut -c1-160 || true)
if [ -n "$sp" ]; then
  bad "British 'licence' outside a quotation (house style is 'license'):"
  printf '%s\n' "$sp" | sed 's/^/        /'
else
  ok "no 'licence' outside quotations"
fi

# 4 — WCAG 2.1 AA contrast, measured from the tokens in assets/style.css
if command -v python3 >/dev/null 2>&1; then
  if out=$(python3 ../tools/check-contrast.py 2>&1); then
    ok "$out"
  else
    bad "contrast:"
    printf '%s\n' "$out" | sed 's/^/        /'
  fi
else
  bad "python3 not found — cannot verify contrast"
fi

# 5 — generated picker markers present (the generator refuses to run
# without them, and a page missing them silently stops updating)
for f in index.html states/index.html; do
  if grep -q 'STATE-PICKER:BEGIN' "$f" && grep -q 'STATE-PICKER:END' "$f"; then
    ok "picker markers present in $f"
  else
    bad "picker markers missing in $f"
  fi
done

# 6 — .assetsignore invariants (never remove these exclusions)
for pat in 'wrangler.toml' '.assetsignore' '.wrangler' 'predeploy-check.sh'; do
  if grep -qx "$pat" .assetsignore 2>/dev/null; then
    ok ".assetsignore excludes $pat"
  else
    bad ".assetsignore missing exclusion: $pat"
  fi
done

# 7 — the colophon footer, which carries the legal-advice disclaimer and the
# independence statement, on every page without exception. 404.html shipped
# without one until 2026-08-27; the sibling had the identical defect.
nofoot=$(HTML0 | xargs -0 grep -L 'class="colophon"' 2>/dev/null || true)
if [ -n "$nofoot" ]; then
  bad "page(s) missing the colophon footer:"
  printf '%s\n' "$nofoot" | sed 's/^/        /'
else
  ok "colophon footer on all $PAGES pages"
fi

# 8 — skip link and its target (WCAG 2.4.1), on every page
noskip=$(HTML0 | xargs -0 grep -L 'class="skip-link"' 2>/dev/null || true)
nomain=$(HTML0 | xargs -0 grep -L 'id="main"' 2>/dev/null || true)
if [ -n "$noskip" ] || [ -n "$nomain" ]; then
  [ -n "$noskip" ] && { bad "page(s) missing the skip link:"; printf '%s\n' "$noskip" | sed 's/^/        /'; }
  [ -n "$nomain" ] && { bad "page(s) missing id=\"main\":";   printf '%s\n' "$nomain" | sed 's/^/        /'; }
else
  ok "skip link and target on all $PAGES pages"
fi

# 9 — every state page has at least one packet, globbed as <slug>-packet*.txt.
# The bare name is not enough: a second packet is how a page's language or
# supplementary quotations are captured, and checking without it reports a
# false failure.
missing_pk=""
for pg in states/*.html; do
  slug=$(basename "$pg" .html)
  [ "$slug" = "index" ] && continue
  set -- ../tools/packets/"$slug"-packet*.txt
  [ -e "$1" ] || missing_pk="$missing_pk $slug"
done
if [ -n "$missing_pk" ]; then
  bad "state page(s) with no packet:$missing_pk"
else
  ok "every state page has a packet"
fi

# 10 — every published state page is listed on both index surfaces, with the
# date it publishes itself. A page's <dd class="docket-checked"> is the
# authority; the STATES JSON in index.html and the last cell of each row in
# states/index.html are derived from it.
#
# The sibling's version of this check compares the rows that exist. That is
# not what went wrong here. states/index.html held two rows — Ohio and Texas,
# the exemplars written when the index was created — while thirty-six pages
# were live, and the STATES JSON held the same two records, so thirty-four
# states sat published with no row, no record, and a pill tooltip carrying no
# date. Thirty-four nightly builds passed over it, because the skill's closing
# checklist named STATUS.md and the picker and never named the table. A check
# that verified only the rows present would have passed too, every night.
#
# So coverage fails, not only staleness. tools/sync-checked-dates.py repairs a
# stale date; a missing row it only reports, because the row carries a sentence
# written from that state's own page and nothing can generate that.
#
# Tripwire before trusting any change to this, in both directions:
#   delete a <tr> from states/index.html          -> must FAIL
#   change a row's date to one the page disowns   -> must FAIL
#   restore both                                  -> must pass
if sync_out=$(cd .. && python3 tools/sync-checked-dates.py --check 2>&1); then
  ok "every state page has an index row and a JSON record, dates agreeing"
else
  bad "states index disagrees with the pages it lists:"
  printf '%s\n' "$sync_out" | sed 's/^/        /'
fi

# 11 — the generated state picker is current. Check 10 compares the page, the
# STATES JSON and the table cell, but the pill tooltip is rendered *from* the
# JSON by tools/build-state-picker.py. A correct JSON whose picker has not been
# regenerated leaves a stale tooltip live while check 10 passes.
#
# Rather than re-derive the generator's logic here and let the two drift, this
# runs the generator and fails if it changed anything: on a current tree it is
# a no-op. If it fails, the regenerated files are already correct — review the
# diff and commit them.
before=$(shasum index.html states/index.html | shasum)
picker_out=$(cd .. && python3 tools/build-state-picker.py 2>&1)
picker_rc=$?
after=$(shasum index.html states/index.html | shasum)
if [ "$picker_rc" -ne 0 ]; then
  bad "build-state-picker.py failed:"
  printf '%s\n' "$picker_out" | sed 's/^/        /'
elif [ "$before" != "$after" ]; then
  bad "the state picker was stale and has been regenerated — review the diff to index.html and states/index.html, commit it, then re-run this check"
else
  ok "state picker markup is current"
fi

# 12 — nothing but publishable files under the deploy root.
#
# This is an allowlist, and it is an allowlist on purpose. .assetsignore is a
# denylist, complete only as far as whoever last remembered it exists, and the
# portfolio has now been bitten by that shape twice in two days from opposite
# directions: Gathered Work published .claude/scheduled_tasks.lock about a
# minute after the directory holding it first existed, and this repo carried a
# stray site/index.html.tmp — left by a sed -i through the sandbox mount, which
# permits the create and refuses the unlink — that every one of the checks
# above passed over, because they all glob *.html and that is not one. It would
# have shipped, and been served at roomandrecourse.com/index.html.tmp: a stale
# copy of the home page at an address nothing links and nobody would notice.
#
# So the question this asks is not "did someone exclude it?" but "is this a
# kind of file this site publishes?" Editor and tool debris — .tmp, .bak,
# .orig, .rej, .swp, .fuse_hidden* — fails by not being on the list, without
# anyone having had to anticipate it.
#
# anchors/ is exempt where it is published, because it is an evidence tree that
# ships whole by decision and its extensions are open-ended (.ots, .tsr, .tsq,
# .pem). Only Gathered Work publishes one; the exemption is carried in all four
# so the check stays the same file everywhere.
#
# If a legitimate new file type is ever added to the site, widen the list here
# in the same commit that adds it. Do not delete the check to get a deploy out.
#
# Tripwire before trusting any change to this, in both directions:
#   touch index.html.tmp / .fuse_hidden0000 / notes.orig  -> each must FAIL
#   remove them                                           -> must pass
DEPLOYROOT="."
ALLOWED_EXT='html|css|js|svg|png|ico|jpg|jpeg|gif|webp|avif|woff|woff2|ttf|pdf|txt|md|json|jsonl|xml|webmanifest'
ALLOWED_NAME='LICENSE|_redirects|_headers|CNAME'
ALWAYS_OK='.assetsignore|.DS_Store|wrangler.toml|predeploy-check.sh'
# literal (non-glob) lines of .assetsignore name files already kept out of the
# deploy; a denylist entry must not also read as a gate failure.
IGN=$(grep -vE '^[[:space:]]*(#|$)' "$DEPLOYROOT/.assetsignore" 2>/dev/null \
      | grep -v '[*?]' | sed 's|^\./||' || true)
stray=$(find "$DEPLOYROOT" -type f \
          -not -path '*/.wrangler/*' -not -path '*/node_modules/*' \
          -not -path '*/anchors/*'   -not -path '*/.git/*' 2>/dev/null \
        | sed 's|^\./||' \
        | while IFS= read -r f; do
            b=${f##*/}
            printf '%s\n' "$b" | grep -qxE "$ALWAYS_OK" && continue
            [ -n "$IGN" ] && printf '%s\n' "$IGN" | grep -qxF -e "$f" -e "$b" && continue
            # if/else rather than case: bash 3.2, which is what /bin/bash is on
            # the Mac this gate runs on, mis-parses a case statement inside a
            # command substitution and dies on the `;;`. The sandbox's bash 5
            # runs it happily, so this passed there and failed on the host.
            if printf '%s\n' "$b" | grep -q '\.'; then
              printf '%s\n' "${b##*.}" | grep -qxE "$ALLOWED_EXT" || printf '%s\n' "$f"
            else
              printf '%s\n' "$b" | grep -qxE "$ALLOWED_NAME" || printf '%s\n' "$f"
            fi
          done)
if [ -n "$stray" ]; then
  bad "file(s) under the deploy root that this site does not publish:"
  printf '%s\n' "$stray" | sed 's/^/        /'
else
  ok "no unpublishable files under the deploy root"
fi


# 13 — the sitemap, robots.txt and _redirects are current.
#
# Every sitemap in this portfolio was hand-written or crawler-generated until
# 2026-09-05, and every one had drifted: this site published 58 pages and
# offered 42 of them. Nothing said so, because nothing was asking. The three
# files are now derived from the file tree by tools/generate-sitemap.py, and
# this gate re-derives them and refuses a deploy whose committed copies differ from
# what the tree implies — the same shape as check 11, and for the same reason:
# a generated file that can be edited by hand will be.
#
# Same shape as the state-picker check: regenerate in place, then fail if
# anything moved. A sitemap change is a published-surface change and must not
# be deployed unseen, but making a person run the generator by hand before
# every deploy is how a gate earns its way into being skipped. Regenerating
# and then failing keeps both: the work is done for you, and the diff still
# has to be read and committed before anything ships.
#
# Tripwire: delete a line from sitemap.xml -> must FAIL; regenerate -> pass.
before=$(shasum sitemap.xml robots.txt _redirects 2>/dev/null | shasum)
if [ ! -f ../tools/generate-sitemap.py ]; then
  bad "tools/generate-sitemap.py is missing; the sitemap cannot be verified"
else
  out=$(python3 ../tools/generate-sitemap.py 2>&1); rc=$?
  after=$(shasum sitemap.xml robots.txt _redirects 2>/dev/null | shasum)
  if [ "$rc" -ne 0 ]; then
    bad "the sitemap generator failed:"
    printf '%s\n' "$out" | sed 's/^/        /'
  elif [ "$before" = "$after" ]; then
    ok "$(printf '%s' "$out" | head -1)"
  else
    bad "the sitemap was stale and has been regenerated — review the diff to sitemap.xml, robots.txt and _redirects, commit it, then re-run this check"
    printf '%s\n' "$out" | sed 's/^/        /'
  fi
fi


# The shared mobile layer is generated into assets/style.css from
# field-assembly-standard/MOBILE-LAYER.css. A hand-edit to the copy is
# silently undone the next time the layer is applied, so the gate refuses a
# deploy whose copy no longer matches the canonical block. The canonical repo
# is a sibling checkout; when it is absent the check reports that rather than
# failing, so this script still runs on a machine that has only one repo.
ML_TOOL="../../field-assembly-standard/tools/apply-mobile-layer.py"
if [ ! -f "$ML_TOOL" ]; then
  ok "shared mobile layer not verified (field-assembly-standard not checked out)"
elif python3 "$ML_TOOL" --check >/tmp/ml-check.$$ 2>&1; then
  ok "shared mobile layer matches the canonical block"
else
  bad "shared mobile layer has drifted from the canonical block:"
  sed 's/^/        /' /tmp/ml-check.$$
  say "        re-apply with: python3 $ML_TOOL"
fi
rm -f /tmp/ml-check.$$

echo
if [ "$fail" -eq 0 ]; then
  say "ALL CHECKS PASSED — safe to run: npx wrangler deploy"
else
  say "CHECKS FAILED — fix the items above before deploying"
fi
exit $fail
