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

# 3 — advisory language (the product's hard boundary). Lines that are
# verbatim source quotations are exempt: board materials legitimately say
# "you must submit" etc. A quotation line begins with a double quote
# (straight or curly) after optional whitespace/tags, per house style.
adv=$(grep -Ein 'you should|we recommend|your deadline|be sure to|you qualify|we advise|you need to file' $HTML 2>/dev/null \
      | grep -Ev '^[^:]+:[0-9]+:[[:space:]]*(<[^>]*>)*[[:space:]]*["““]' \
      | cut -c1-160 || true)
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

echo
if [ "$fail" -eq 0 ]; then
  say "ALL CHECKS PASSED — safe to run: npx wrangler deploy"
else
  say "CHECKS FAILED — fix the items above before deploying"
fi
exit $fail
