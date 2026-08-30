Copied from licensure-mobility tools/ on 2026-08-29; adapted for
transfer-safeguards (Room & Recourse) on 2026-08-30: check-fidelity.py
allowlist carries roomandrecourse.com and two added advisory constructions;
build-status.py recognizes full pages by "Notice periods and deadlines, as
stated in the sources" and tracks the federal layer instead of the compact;
render-state.py renders the Room & Recourse shell and handles federal.md →
site/federal.html as a special case. capture.py, retain-packet.py,
packet-set.py, check-all.py, pass-health.py, anchor.py, and
build-state-picker.py run unchanged from the sibling. Anchoring begins once
real evidence exists.

make-icons.py is local to this repository (added 2026-08-30). It redraws the
site's raster icons — favicon-16.png, favicon-32.png, favicon.ico,
apple-touch-icon.png, icon-512.png — from the door glyph, in the same
coordinates the hand-authored site/assets/favicon.svg uses, so the icon set can
be regenerated with Pillow and no other tool. Run it after any change to the
glyph, then re-run site/predeploy-check.sh.
