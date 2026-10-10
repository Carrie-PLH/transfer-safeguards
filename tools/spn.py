#!/usr/bin/env python3
"""Internet Archive Save Page Now capture worker for Room & Recourse.

Requests captures for state-page sources that have none, and reports what
happened. Since 2026-10-06 it also records each confirmed capture in the page's
own change log (`record`, called by `run`); see "Recording a capture on
the page" below.

Ported from gathered work/tools/spn.py (2026-09-04). That script is the
original and governs the shared doctrine below; this is an independent copy
per this portfolio's rule against a shared library across repos, not a
wrapper around it. Changing the doctrine here does not change it there, and a
real fix to the shared logic has to be made in both places by hand.

Credentials live outside the repo in ~/.config/ia/spn.env, shared across the
whole Field Assembly portfolio's Save Page Now tooling (one Internet Archive
account, one nightly budget, four repos' scripts drawing on it), as

    IA_ACCESS_KEY=...
    IA_SECRET_KEY=...

Generate them at https://archive.org/account/s3.php. Save Page Now stopped
accepting anonymous saves; an unauthenticated request returns 401, which is
why this script exists at all.

Usage
-----
    python3 tools/spn.py plan   [--budget N] [--max-attempts M] [--slug SLUG] [--retry-blocked]
    python3 tools/spn.py run    [--budget N] [--max-attempts M] [--slug SLUG] [--retry-blocked] [--no-record]
    python3 tools/spn.py record [--slug SLUG] [--dry-run]
    python3 tools/spn.py status [--slug SLUG]
    python3 tools/spn.py --self-test

--budget is a target number of *captures*, not attempts. A run keeps working
down the candidate list until that many sources are confirmed stored, so a
night of heavy refusals costs more attempts rather than fewer captures.
--max-attempts bounds that chase; it defaults to three times the budget, which
is the safety valve, not the goal. A run that stops at the ceiling short of its
target has not failed — it has recorded that the far side was refusing.

A source that fails rests for RETRY_AFTER_DAYS (7) before it is eligible again,
and when it does return it takes its ordinary place behind sources that have
never been attempted. A host refusing the archiver last night will almost
certainly refuse tonight, and retrying it nightly spends the run on the least
promising sources on the list while pages with no captures at all wait. This is
separate from blocking: BLOCK_AFTER (3) consecutive hard failures retires a
source from the rotation altogether until --retry-blocked asks for it.

Run it host-side (Desktop Commander from a Cowork session; directly, in
Claude Code Desktop, where the session already runs on the Mac), never from
the sandbox shell: the sandbox does not share the Mac's home directory and
cannot read the key file.

What counts as a capture
------------------------
A source needs a capture when a state page links it and carries no
web.archive.org link for it. The page is the record; there is no separate
capture ledger to drift out of sync. The ledger this script does keep
(tools/spn-ledger.json) records *attempts*, so that sources whose hosts refuse
the archiver are not retried nightly forever.

A capture is only ever reported OK when Save Page Now reports status "success"
AND the captured response was HTTP 200. A stored 403 or a WAF interstitial is a
refusal page wearing a capture's clothes; recording one as evidence would be
worse than recording nothing.

Recording a capture on the page (2026-10-06)
--------------------------------------------
Carrie decided on 2026-10-06, for every collection, that the pass writes the
change-log entry itself: in gathered work no session had been writing them,
and 594 confirmed captures sat in the ledger with nothing on the page. The
wording is fixed, so nothing about the entry needs a judgement; what stays
with a person is reviewing, which the entry never claims.

`record` writes, for every page with ledger-confirmed captures the page does
not yet link, one dated entry in this repo's own change-log dialect (the
REPO-SPECIFIC block below says where it goes and what it looks like). `run`
calls it at the end of a pass for the pages it captured on, so a night's
captures and their entries land together; `--no-record` leaves the
ledger-only behaviour for a session that wants to write the entry by hand.

The entry says what it is: an automated capture pass, no human review
claimed, nothing above it changed. It names each source by the page's own
link text and links the capture. It never carries a reviewer's name, never
touches a date, a quotation or the docket, and never rewrites an earlier
entry -- a build entry's "Internet Archive captures: to be added." stays as
history.

A page whose change log is not found exactly once where this tool expects
it is skipped and reported, never guessed at. `record` is idempotent: a
capture already linked from the page is not a candidate, so running it
twice writes nothing the second time. The entry is dated with the UTC date,
the same clock the ledger stamps attempts with. The paths it writes (the
markdown and the page) are printed so the committing session can stage
them by path, as the portfolio's commit rule requires.
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# This path is how the script decides what to capture: pointed at a directory
# that does not exist it captures nothing, which looks exactly like a pass
# with nothing to do.
STATES = os.path.join(ROOT, "site", "states")
LEDGER_PATH = os.path.join(ROOT, "tools", "spn-ledger.json")
ENV_PATH = os.path.expanduser("~/.config/ia/spn.env")

SAVE_URL = "https://web.archive.org/save"
STATUS_URL = "https://web.archive.org/save/status/"

# The publisher's other sites, linked from every footer's "More from Field
# Assembly" column (field-assembly-standard/tools/cross-links.py, 2026-10-09),
# and byreassembly.com, where the "Built by Reassembly" credit moved on
# 2026-10-06. Family, not sources: none of them will ever appear in a packet.
FAMILY_HOSTS = {"boardandborder.com", "www.boardandborder.com",
                "rulesandrecord.com", "www.rulesandrecord.com",
                "roomandrecourse.com", "www.roomandrecourse.com",
                "gatheredwork.com", "www.gatheredwork.com",
                "ai-learningevidence.com", "www.ai-learningevidence.com",
                "glp-1evidence.com", "www.glp-1evidence.com",
                "provisionrecord.com", "www.provisionrecord.com",
                "materialsmonitor.com", "www.materialsmonitor.com",
                "learnthings.online", "www.learnthings.online",
                "byreassembly.com", "www.byreassembly.com"}

# Hosts that are ours or infrastructure, never sources to capture.
SKIP_HOSTS = {"roomandrecourse.com", "www.roomandrecourse.com",
              "fieldassembly.net", "www.fieldassembly.net",
              "web.archive.org"} | FAMILY_HOSTS

# Consecutive hard failures before a source is left alone.
BLOCK_AFTER = 3

# --budget counts captures, not attempts, so a run needs a ceiling on how many
# sources it will burn chasing that target. Three times the budget absorbs the
# usual refusal rate without letting a bad night run unbounded.
ATTEMPT_CEILING_FACTOR = 3

# Days a failed source rests before it is eligible again. A host that refused
# last night will almost certainly refuse tonight, and retrying it nightly
# spends the run's attempts on the least promising sources on the list.
RETRY_AFTER_DAYS = 7

# Failure kinds that mean the far side refused the archiver. Retrying these on a
# nightly cadence accomplishes nothing but noise.
HARD_FAILURES = {"error:no-request", "error:blocked", "error:forbidden",
                 "http-403", "http-202"}

# Conditions about this Internet Archive account on this night, not about the
# source. Save Page Now enforces a daily cap per account; when it trips, every
# source attempted afterwards fails for a reason that has nothing to do with
# its host. Counting those as hard failures would march unrelated sources
# toward BLOCK_AFTER, and recording them as FAILED would rest each one for
# RETRY_AFTER_DAYS — both punishing a source for the pass's own appetite.
# A run that meets this stops instead: see the run loop. (2026-09-04)
ACCOUNT_LIMIT = {"error:too-many-daily-captures"}

POLL_INTERVAL = 6
POLL_LIMIT = 70          # ~7 minutes before a job is called a timeout
PACE_SECONDS = 12        # between sources; SPN caps concurrent sessions
SESSION_LIMIT_WAIT = 90
SESSION_LIMIT_TRIES = 6


# --------------------------------------------------------------------------
# credentials

def load_auth():
    if not os.path.exists(ENV_PATH):
        sys.exit("No credentials at %s — see the module docstring." % ENV_PATH)
    values = {}
    with open(ENV_PATH, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip()
    access = values.get("IA_ACCESS_KEY", "")
    secret = values.get("IA_SECRET_KEY", "")
    if not access or not secret:
        sys.exit("IA_ACCESS_KEY / IA_SECRET_KEY missing or empty in %s" % ENV_PATH)
    return "LOW %s:%s" % (access, secret)


# --------------------------------------------------------------------------
# page scanning

def page_links(html_text):
    return re.findall(r'href="(https?://[^"]+)"', html_text)


def scan_page(path):
    """Return (sources_needing_capture, already_captured) for one page."""
    with open(path, encoding="utf-8") as fh:
        text = fh.read()

    captured = set()
    sources = []
    for href in page_links(text):
        href = href.replace("&amp;", "&")
        host = urllib.parse.urlparse(href).netloc
        if href.startswith("https://web.archive.org/web/"):
            # https://web.archive.org/web/<timestamp>/<original url>
            tail = href.split("/", 5)
            if len(tail) == 6:
                captured.add(tail[5])
            continue
        if host in SKIP_HOSTS or not host:
            continue
        if href not in sources:
            sources.append(href)

    needed = [u for u in sources if u not in captured]
    return needed, captured


def scan_all(slug=None):
    out = {}
    pages = [(name[:-5], os.path.join(STATES, name))
             for name in sorted(os.listdir(STATES))
             if name.endswith(".html") and name != "index.html"]

    # The federal layer is a published page carrying first-party sources
    # (eCFR, CMS) exactly as a state page does, and the review rotation
    # already treats it as one under the slug "federal". Scoping this tool to
    # site/states/ alone left those sources with no archive coverage at all.
    # Widened 2026-09-04 on Carrie's decision.
    federal = os.path.join(ROOT, "site", "federal.html")
    if os.path.exists(federal):
        pages.append(("federal", federal))

    for this_slug, path in sorted(pages):
        if slug and this_slug != slug:
            continue
        needed, captured = scan_page(path)
        if needed or captured:
            out[this_slug] = {"needed": needed, "captured": len(captured)}
    return out


# --------------------------------------------------------------------------
# ledger

def load_ledger():
    if os.path.exists(LEDGER_PATH):
        with open(LEDGER_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    return {"sources": {}}


def save_ledger(ledger):
    ledger["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    with open(LEDGER_PATH, "w", encoding="utf-8") as fh:
        json.dump(ledger, fh, indent=2, sort_keys=True)
        fh.write("\n")


def is_blocked(ledger, url):
    rec = ledger["sources"].get(url)
    return bool(rec and rec.get("consecutive_hard_failures", 0) >= BLOCK_AFTER)


def last_attempt_at(ledger, url):
    """When this source was last attempted, or None if never (or unparseable)."""
    rec = ledger["sources"].get(url)
    stamp = rec.get("last_attempt") if rec else None
    if not stamp:
        return None
    try:
        return datetime.strptime(stamp, "%Y-%m-%dT%H%M%SZ").replace(
            tzinfo=timezone.utc)
    except ValueError:
        return None


def is_cooling(ledger, url, now=None):
    """True when this source failed recently enough to still be resting.

    A source that refused the archiver is not retried the following night. It
    waits out RETRY_AFTER_DAYS and then rejoins the candidate list in its
    ordinary place, so a stubborn host never displaces forward progress on
    sources that have never been tried at all.
    """
    rec = ledger["sources"].get(url)
    if not rec or rec.get("last_result") != "FAILED":
        return False
    when = last_attempt_at(ledger, url)
    if when is None:
        return False
    now = now or datetime.now(timezone.utc)
    return (now - when).total_seconds() < RETRY_AFTER_DAYS * 86400


def note_attempt(ledger, url, slug, result, detail=""):
    rec = ledger["sources"].setdefault(url, {})
    rec["page"] = slug
    rec["last_attempt"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    rec["last_result"] = result
    rec["attempts"] = rec.get("attempts", 0) + 1
    if detail:
        rec["last_detail"] = detail
    if detail in ACCOUNT_LIMIT:
        # Not the source's doing. Record the attempt honestly, but do not let
        # it rest the source (is_cooling reads last_result) and do not count it
        # toward blocking.
        rec["last_result"] = "SKIPPED"
    elif result == "OK":
        rec["consecutive_hard_failures"] = 0
    elif detail in HARD_FAILURES:
        rec["consecutive_hard_failures"] = rec.get("consecutive_hard_failures", 0) + 1
    return rec


# --------------------------------------------------------------------------
# Save Page Now

def post(url, auth, data=None, timeout=120):
    body = urllib.parse.urlencode(data).encode() if data else None
    req = urllib.request.Request(url, data=body)
    req.add_header("Accept", "application/json")
    req.add_header("Authorization", auth)
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")
    except Exception as exc:                                  # noqa: BLE001
        return 0, str(exc)


def submit(url, auth):
    """Submit one URL. Returns (job_id, failure_detail)."""
    for _ in range(SESSION_LIMIT_TRIES):
        code, body = post(SAVE_URL, auth, {"url": url})
        try:
            payload = json.loads(body)
        except ValueError:
            payload = {}
        job = payload.get("job_id")
        if job:
            return job, None
        # Both of these are "come back later", not "this source is unarchivable":
        # the session cap, and a plain 429 after a heavy run.
        if "user-session-limit" in body or code == 429:
            time.sleep(SESSION_LIMIT_WAIT)
            continue
        return None, "submit-%s" % code
    return None, "submit-throttled"


def capture(url, auth):
    """Capture one URL. Returns (capture_url_or_None, detail)."""
    job, failure = submit(url, auth)
    if not job:
        return None, failure

    final = None
    for _ in range(POLL_LIMIT):
        time.sleep(POLL_INTERVAL)
        _, body = post(STATUS_URL + job, auth)
        try:
            payload = json.loads(body)
        except ValueError:
            continue
        if payload.get("status") in ("success", "error"):
            final = payload
            break

    if final is None:
        return None, "timeout"
    if final.get("status") == "error":
        return None, final.get("status_ext") or "error"

    http_status = final.get("http_status")
    timestamp = final.get("timestamp")
    if http_status and int(http_status) != 200:
        # Stored, but what was stored is a refusal or a challenge page.
        return None, "http-%s" % http_status
    if not timestamp:
        return None, "no-timestamp"
    return "https://web.archive.org/web/%s/%s" % (timestamp, url), "ok"


def playback_ok(capture_url):
    """Confirm the capture actually plays back before it is reported."""
    for attempt in range(4):
        try:
            req = urllib.request.Request(capture_url, method="HEAD")
            req.add_header("User-Agent", "Mozilla/5.0")
            return urllib.request.urlopen(req, timeout=60).status == 200
        except Exception:                                     # noqa: BLE001
            time.sleep(25 * (attempt + 1))
    return False



# --------------------------------------------------------------------------
# recording captures on the page (ported from gathered work/tools/spn.py,
# 2026-10-06; the dialect-specific parts are marked REPO-SPECIFIC below)

def html_escape(text, quote=False):
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return text.replace('"', "&quot;") if quote else text


def html_unescape(text):
    return (text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
                .replace("&quot;", '"').replace("&#39;", "'").replace("&rsquo;", "\u2019")
                .replace("&rarr;", "\u2192"))


def source_name(page_text, url):
    """What the page itself calls this source: its link text, preferring a
    descriptive name over the bare host/path shorthand some pages also use.
    Falls back to the URL without scheme. Nothing is fetched."""
    hrefs = re.findall(r'<a href="%s"[^>]*>(.*?)</a>'
                       % re.escape(html_escape(url)), page_text, flags=re.S)
    names = []
    for raw in hrefs:
        name = html_unescape(re.sub(r"<[^>]+>", "", raw)).strip()
        if name and name not in names:
            names.append(name)
    bare = re.sub(r"^https?://(www\.)?", "", url)
    host = bare.split("/")[0]
    for name in names:
        if name != bare and not name.startswith(host + " ") \
                and not name.startswith(host + "/"):
            return name
    return names[0] if names else bare


def display_date(iso):
    """2026-10-06 -> 'Oct 6, 2026', the house display form."""
    y, m, d = iso.split("-")
    months = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
    return "%s %d, %s" % (months[int(m) - 1], int(d), y)


def entry_body(dates, today):
    """The prose every dialect shares: what the pass was, what it did not
    touch, and how each capture was confirmed. Returns text up to and
    including 'Captures added: '."""
    dates = sorted(dates)
    if dates == [today]:
        lead = ("Captures requested this date by an automated capture pass; "
                "no human review is claimed for this entry.")
    elif len(dates) == 1:
        lead = ("Captures requested on %s by an automated capture pass and "
                "recorded this date; no human review is claimed for this entry."
                % dates[0])
    else:
        lead = ("Captures requested by automated capture passes between %s and "
                "%s and recorded this date; no human review is claimed for this "
                "entry." % (dates[0], dates[-1]))
    return (lead + " No quotation, date, finding or link above was changed by "
            "it. Each capture below was requested through Save Page Now and "
            "then confirmed to play back. Captures added: ")


def items_md(page_text, captures):
    return "; ".join("%s \u2192 [%s](%s)" % (source_name(page_text, url), cap, cap)
                     for _, url, cap in sorted(captures))


def items_html(page_text, captures):
    return "; ".join('%s \u2192 <a href="%s" target="_blank" rel="noopener">%s</a>'
                     % (html_escape(source_name(page_text, url)),
                        html_escape(cap, quote=True), html_escape(cap))
                     for _, url, cap in sorted(captures))


def unrecorded(ledger, slugs=None):
    """{slug: [(requested_date, source_url, capture_url), ...]} for every
    ledger-confirmed capture its page does not yet link. The page is the
    record, so this is exactly scan_page's `needed` intersected with OK."""
    out = {}
    for slug, info in scan_all().items():
        if slugs is not None and slug not in slugs:
            continue
        needed = set(info["needed"])
        rows = []
        for url, rec in ledger["sources"].items():
            if rec.get("page") == slug and rec.get("last_result") == "OK" \
                    and rec.get("capture") and url in needed:
                rows.append((rec.get("last_attempt", "")[:10], url, rec["capture"]))
        if rows:
            out[slug] = rows
    return out


def record_pages(ledger, slugs=None, dry_run=False, today=None):
    """Write the entries. Returns (written_paths, skipped) where skipped is a
    list of (slug, reason). A page is skipped, never guessed at, when its
    change log is not where this tool expects it."""
    today = today or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    written, skipped = [], []
    for slug, rows in sorted(unrecorded(ledger, slugs).items()):
        html_path, md_path = page_paths(slug)
        if not (os.path.exists(html_path) and os.path.exists(md_path)):
            skipped.append((slug, "page or markdown source missing"))
            continue
        with open(html_path, encoding="utf-8") as fh:
            page = fh.read()
        with open(md_path, encoding="utf-8") as fh:
            md = fh.read()
        dates = {d for d, _, _ in rows}
        new_md = insert_md(md, md_entry(page, rows, dates, today))
        if new_md is None:
            skipped.append((slug, "markdown change log not found exactly once "
                            "where expected -- write this one by hand"))
            continue
        new_html = produce_html(page, rows, dates, today)
        if new_html is None:
            skipped.append((slug, "page change log not found exactly once "
                            "where expected -- write this one by hand"))
            continue
        print("%-7s %-24s %d capture(s)" % ("WOULD" if dry_run else "RECORD",
                                           slug, len(rows)))
        if dry_run:
            continue
        with open(md_path, "w", encoding="utf-8") as fh:
            fh.write(new_md)
        if new_html is RERENDER:
            rerender(slug)
        else:
            with open(html_path, "w", encoding="utf-8") as fh:
                fh.write(new_html)
        with open(html_path, encoding="utf-8") as fh:
            check = fh.read()
        missing = [cap for _, _, cap in rows
                   if cap not in check and html_escape(cap) not in check]
        if missing:
            skipped.append((slug, "entry written to %s but %d capture link(s) "
                            "are not on the rendered page -- inspect before "
                            "committing" % (os.path.relpath(md_path, ROOT), len(missing))))
        written.extend([os.path.relpath(md_path, ROOT), os.path.relpath(html_path, ROOT)])
    return written, skipped


def report_recording(written, skipped, dry_run=False):
    for slug, reason in skipped:
        print("SKIPPED %-24s %s" % (slug, reason))
    if dry_run:
        print("\nDry run: nothing written.")
    elif written:
        print("\nRecorded on %d page(s). Stage these paths with the ledger:"
              % (len(written) // 2))
        for path in written:
            print("  %s" % path)
    else:
        print("\nNothing to record: every confirmed capture is already on its page.")


RERENDER = object()


# REPO-SPECIFIC (Room & Recourse). states/<slug>.md (and federal.md for the
# federal layer) is canonical and the page is a pure product of
# tools/render-state.py, enforced by the deploy gate's parity check. So the
# entry goes into the markdown and the page is re-rendered, never edited.
# The log is "## 04 -- Change log", NEWEST entry first, so a new entry goes
# directly under the heading. Entries open with the ISO date and an em dash;
# an automated entry carries no reviewer line and no corrections trailer,
# matching the nightly review's own entries.

MD_DIR = os.path.join(ROOT, "states")
RENDER = os.path.join(ROOT, "tools", "render-state.py")
LOG_HEADING = "## 04 \u2014 Change log\n\n"


def page_paths(slug):
    if slug == "federal":
        return (os.path.join(ROOT, "site", "federal.html"), os.path.join(ROOT, "federal.md"))
    return (os.path.join(STATES, slug + ".html"), os.path.join(MD_DIR, slug + ".md"))


def md_entry(page, rows, dates, today):
    return ("%s \u2014 Internet Archive captures recorded. %s%s."
            % (today, entry_body(dates, today), items_md(page, rows)))


def insert_md(md, entry):
    if md.count(LOG_HEADING) != 1:
        return None
    return md.replace(LOG_HEADING, LOG_HEADING + entry + "\n\n")


def produce_html(page, rows, dates, today):
    return RERENDER


def rerender(slug):
    import subprocess
    subprocess.run([sys.executable, RENDER, slug], check=True)


# --------------------------------------------------------------------------
# commands

def select(ledger, slug, retry_blocked):
    """Every candidate source, in stable order. The budget is applied by the
    caller as a target number of *captures*, not a slice of this list."""
    fresh = []
    due = []
    skipped_blocked = []
    skipped_cooling = []
    for page_slug, info in scan_all(slug).items():
        for url in info["needed"]:
            if is_blocked(ledger, url) and not retry_blocked:
                skipped_blocked.append((page_slug, url))
                continue
            if is_cooling(ledger, url) and not retry_blocked:
                skipped_cooling.append((page_slug, url))
                continue
            (due if last_attempt_at(ledger, url) else fresh).append(
                (page_slug, url))
    fresh.sort()
    due.sort()
    # Never-attempted sources go first. Sources whose rest period has expired
    # follow, so a retry rides along with the night's run rather than heading it.
    return fresh + due, skipped_blocked, skipped_cooling


def cmd_plan(args):
    ledger = load_ledger()
    picked, blocked, cooling = select(ledger, args.slug, args.retry_blocked)
    ceiling = args.max_attempts or (args.budget * ATTEMPT_CEILING_FACTOR)
    print("Target: %d capture(s), attempting at most %d source(s).\n"
          "%d candidate(s) available, in this order:\n"
          % (args.budget, ceiling, len(picked)))
    for slug, url in picked[:ceiling]:
        print("  %-14s %s" % (slug, url))
    if len(picked) > ceiling:
        print("  … and %d more beyond the attempt ceiling."
              % (len(picked) - ceiling))
    if blocked:
        print("\n%d source(s) held back after %d consecutive hard failures "
              "(--retry-blocked to include):\n" % (len(blocked), BLOCK_AFTER))
        for slug, url in blocked:
            detail = ledger["sources"][url].get("last_detail", "")
            print("  %-14s %-8s %s" % (slug, detail, url))
    if cooling:
        print("\n%d source(s) resting until %d days after their last failure:\n"
              % (len(cooling), RETRY_AFTER_DAYS))
        for slug, url in cooling:
            detail = ledger["sources"][url].get("last_detail", "")
            print("  %-14s %-8s %s" % (slug, detail, url))


def cmd_status(args):
    ledger = load_ledger()
    total_needed = 0
    for slug, info in scan_all(args.slug).items():
        blocked = sum(1 for u in info["needed"] if is_blocked(ledger, u))
        total_needed += len(info["needed"])
        flag = "  (%d blocked)" % blocked if blocked else ""
        print("%-14s captured %2d   needs %2d%s"
              % (slug, info["captured"], len(info["needed"]), flag))
    print("\n%d source(s) outstanding across all pages." % total_needed)


def cmd_run(args):
    auth = load_auth()
    ledger = load_ledger()
    picked, blocked, cooling = select(ledger, args.slug, args.retry_blocked)
    ceiling = args.max_attempts or (args.budget * ATTEMPT_CEILING_FACTOR)

    if not picked:
        print("Nothing to capture.")
        if blocked:
            print("%d source(s) held back as blocked." % len(blocked))
        if cooling:
            print("%d source(s) resting after a recent failure." % len(cooling))
        return

    print("Target: %d capture(s) from %d candidate(s), "
          "attempting at most %d." % (args.budget, len(picked), ceiling))
    if cooling:
        print("%d source(s) resting until %d days after their last failure; "
              "they are not attempted tonight." % (len(cooling), RETRY_AFTER_DAYS))
    print()
    results = {"ok": [], "failed": []}
    attempts = 0

    for slug, url in picked:
        if len(results["ok"]) >= args.budget or attempts >= ceiling:
            break
        attempts += 1
        capture_url, detail = capture(url, auth)

        if capture_url and not playback_ok(capture_url):
            capture_url, detail = None, "no-playback"

        if capture_url:
            rec = note_attempt(ledger, url, slug, "OK", "ok")
            rec["capture"] = capture_url
            results["ok"].append((slug, url, capture_url))
            print("OK      %-14s %s" % (slug, url))
            print("        -> %s" % capture_url)
        else:
            rec = note_attempt(ledger, url, slug, "FAILED", detail)
            if detail in ACCOUNT_LIMIT:
                save_ledger(ledger)
                print("STOP    %-14s %-22s %s" % (slug, detail, url))
                print("\nThe account's daily capture limit was reached. Every "
                      "source attempted after this point would fail for a "
                      "reason that is not about the source, so the run stops "
                      "here. Nothing is blocked and nothing is resting on "
                      "account of it; the remaining candidates were simply not "
                      "reached. Do not re-run tonight, and do not raise the "
                      "budget to compensate - the cap is the finding.")
                break
            hard = rec.get("consecutive_hard_failures", 0)
            note = "  [blocked after %d]" % hard if hard >= BLOCK_AFTER else ""
            results["failed"].append((slug, url, detail))
            print("FAILED  %-14s %-22s %s%s" % (slug, detail, url, note))

        save_ledger(ledger)
        time.sleep(PACE_SECONDS)

    print("\n%d captured, %d failed, %d attempted."
          % (len(results["ok"]), len(results["failed"]), attempts))
    if len(results["ok"]) < args.budget:
        if attempts >= ceiling:
            print("Stopped at the attempt ceiling of %d before reaching the "
                  "target of %d capture(s). The far side refused more than "
                  "usual tonight; the shortfall is not an error."
                  % (ceiling, args.budget))
        else:
            print("Candidate list exhausted at %d capture(s); nothing further "
                  "was available to attempt." % len(results["ok"]))
    pages = sorted({slug for slug, _, _ in results["ok"]})
    if not pages:
        return
    if args.no_record:
        print("\n--no-record: captures are in the ledger but NOT on any page. "
              "Run `spn.py record` or write the entries by hand for: %s"
              % ", ".join(pages))
        return
    print("\nRecording tonight's captures on their pages:")
    written, skipped = record_pages(ledger, set(pages))
    report_recording(written, skipped)


def cmd_record(args):
    ledger = load_ledger()
    slugs = {args.slug} if args.slug else None
    written, skipped = record_pages(ledger, slugs, dry_run=args.dry_run)
    report_recording(written, skipped, dry_run=args.dry_run)


SAMPLE_SLUG = "x"
SAMPLE_PAGE = '<p class="mw">Sources: <a href="https://x.gov/a?b=1&amp;c=2">Policy A</a>, <a href="https://x.gov/b">x.gov/b</a>, <a href="https://x.gov/b">Guide &amp; Notes</a>, <a href="https://web.archive.org/web/20260101000000/https://x.gov/done">done</a>, <a href="https://x.gov/done">Done page</a>.</p>\n'
SAMPLE_MD = '# X\n\n## Docket\n\n**Sources last checked.** 2026-09-01\n\n## 04 — Change log\n\n2026-09-16 — Deepened. Text.\n\n2026-09-01 — Baseline page built. Internet Archive: not yet submitted. Reviewer: Carrie Schluter, reviewed 2026-09-01. Corrections: hello@fieldassembly.net.\n'
SAMPLE_MD_BAD = '# X\n\n## Docket\n\nText.\n\n## 04 — Change log\n\n## 04 — Change log\n\n'


def REPO_CHECKS(check, page, rows, entry, new_md):
    check(entry.startswith("2026-10-06 \u2014 Internet Archive captures recorded. "), "md ISO em-dash form")
    check("Corrections" not in entry, "no trailer on an automated entry")
    check(new_md.index(entry) < new_md.index("2026-09-16"), "md entry newest-first, under the heading")
    check(new_md.count(LOG_HEADING) == 1 and LOG_HEADING + entry + "\n\n2026-09-16" in new_md, "md spacing")
    check(page_paths("federal")[1].endswith("federal.md") and page_paths("federal")[0].endswith(os.path.join("site", "federal.html")), "federal paths")
    check(produce_html(page, rows, {"2026-10-01"}, "2026-10-06") is RERENDER, "page is re-rendered, not edited")


_SAVED = {}

def _fake_render(slug):
    # Stands in for render-state.py: the page is the links plus the markdown
    # change log's capture links, which is all the post-check reads.
    html_path, md_path = page_paths(slug)
    md = open(md_path, encoding="utf-8").read()
    caps = re.findall(r"\((https://web\.archive\.org/web/[^)]+)\)", md)
    body = SAMPLE_PAGE + "".join('<a href="%s">c</a>' % html_escape(c, quote=True) for c in caps)
    open(html_path, "w", encoding="utf-8").write(body)


def SETUP_TREE(tmp, page, md):
    global STATES, MD_DIR, rerender
    _SAVED.update(STATES=STATES, MD_DIR=MD_DIR, rerender=rerender)
    STATES = os.path.join(tmp, "site", "states"); MD_DIR = os.path.join(tmp, "states")
    os.makedirs(STATES); os.makedirs(MD_DIR)
    open(os.path.join(STATES, "x.html"), "w", encoding="utf-8").write(page)
    open(os.path.join(MD_DIR, "x.md"), "w", encoding="utf-8").write(md)
    rerender = _fake_render


def RESTORE_TREE():
    global STATES, MD_DIR, rerender
    STATES, MD_DIR, rerender = _SAVED["STATES"], _SAVED["MD_DIR"], _SAVED["rerender"]


# --------------------------------------------------------------------------
# self-test: the recording path against a throwaway tree (no network)

def self_test():
    import shutil
    import tempfile
    checks = 0

    def check(cond, what):
        nonlocal checks
        checks += 1
        if not cond:
            sys.exit("self-test FAILED: %s" % what)

    page = SAMPLE_PAGE
    rows = [("2026-10-01", "https://x.gov/a?b=1&c=2",
             "https://web.archive.org/web/20261001010000/https://x.gov/a?b=1&c=2"),
            ("2026-10-03", "https://x.gov/b",
             "https://web.archive.org/web/20261003010000/https://x.gov/b")]
    check(source_name(page, "https://x.gov/a?b=1&c=2") == "Policy A", "name: plain")
    check(source_name(page, "https://x.gov/b") == "Guide & Notes", "name: prefer descriptive")
    check(source_name(page, "https://x.gov/nolink") == "x.gov/nolink", "name: fallback")
    check(display_date("2026-10-06") == "Oct 6, 2026", "display date")
    b1 = entry_body({"2026-10-06"}, "2026-10-06")
    check(b1.startswith("Captures requested this date by an automated capture pass;"), "body: today")
    b2 = entry_body({"2026-10-03"}, "2026-10-06")
    check(b2.startswith("Captures requested on 2026-10-03 by an automated capture pass and recorded this date;"), "body: one date")
    b3 = entry_body({"2026-10-01", "2026-10-03"}, "2026-10-06")
    check("between 2026-10-01 and 2026-10-03 and recorded this date;" in b3, "body: range")
    md_items = items_md(page, rows)
    check("Policy A \u2192 [https://web.archive.org/web/20261001010000/https://x.gov/a?b=1&c=2](https://web.archive.org/web/20261001010000/https://x.gov/a?b=1&c=2)" in md_items, "md items")
    check("Guide & Notes \u2192 [" in md_items, "md items: unescaped text")
    h_items = items_html(page, rows)
    check('Guide &amp; Notes \u2192 <a href="https://web.archive.org/web/20261003010000/https://x.gov/b" target="_blank" rel="noopener">' in h_items, "html items escaped")

    entry = md_entry(page, rows, {"2026-10-01", "2026-10-03"}, "2026-10-06")
    check("Reviewer" not in entry and "Carrie" not in entry, "no reviewer name")
    check("no human review is claimed" in entry, "entry says automated")
    new_md = insert_md(SAMPLE_MD, entry)
    check(new_md is not None and entry in new_md, "md insertion")
    check(new_md.replace(entry + "\n\n", "").replace("\n\n" + entry + "\n", "\n") == SAMPLE_MD, "md history untouched")
    check(insert_md(SAMPLE_MD_BAD, entry) is None, "md skip when log not found once")
    REPO_CHECKS(check, page, rows, entry, new_md)

    # End to end against a throwaway tree: write, verify, idempotent.
    tmp = tempfile.mkdtemp()
    try:
        SETUP_TREE(tmp, page, SAMPLE_MD)
        ledger = {"sources": {u: {"page": SAMPLE_SLUG, "last_result": "OK",
                                  "last_attempt": d + "T010000Z", "capture": c}
                              for d, u, c in rows}}
        ledger["sources"]["https://x.gov/failed"] = {"page": SAMPLE_SLUG, "last_result": "FAILED",
                                                     "last_attempt": "2026-10-03T010000Z"}
        need = unrecorded(ledger)
        check(sorted(need) == [SAMPLE_SLUG] and len(need[SAMPLE_SLUG]) == 2, "unrecorded: OK only, unlinked only")
        html_path, md_path = page_paths(SAMPLE_SLUG)
        before_md = open(md_path, encoding="utf-8").read()
        written, skipped = record_pages(ledger, dry_run=True, today="2026-10-06")
        check(written == [] and open(md_path, encoding="utf-8").read() == before_md, "dry run writes nothing")
        written, skipped = record_pages(ledger, today="2026-10-06")
        check(skipped == [], "no skips: %r" % skipped)
        check(len(written) == 2 and written[0].endswith(".md") and written[1].endswith(".html"), "written paths")
        after_html = open(html_path, encoding="utf-8").read()
        check(all(c in after_html or html_escape(c) in after_html for _, _, c in rows), "captures linked on page")
        check(unrecorded(ledger) == {}, "idempotent: nothing left")
        written, skipped = record_pages(ledger, today="2026-10-06")
        check(written == [] and skipped == [], "idempotent: second run writes nothing")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        RESTORE_TREE()
    print("self-test: %d checks passed" % checks)


def main():
    if sys.argv[1:] == ["--self-test"]:
        self_test()
        return
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for name, handler in (("plan", cmd_plan), ("run", cmd_run),
                          ("record", cmd_record), ("status", cmd_status)):
        sp = sub.add_parser(name)
        sp.add_argument("--slug", help="limit to one state page")
        if name == "run":
            sp.add_argument("--no-record", action="store_true",
                            help="leave tonight's captures in the ledger only; "
                                 "do not write the change-log entries")
        if name == "record":
            sp.add_argument("--dry-run", action="store_true",
                            help="show which pages would get an entry; write nothing")
        if name in ("plan", "run"):
            sp.add_argument("--budget", type=int, default=20,
                            help="captures to obtain, not sources to attempt "
                                 "(default 20)")
            sp.add_argument("--max-attempts", type=int, default=None,
                            help="ceiling on sources attempted while chasing "
                                 "the budget (default: %dx the budget)"
                                 % ATTEMPT_CEILING_FACTOR)
            sp.add_argument("--retry-blocked", action="store_true",
                            help="include sources held back as blocked")
        sp.set_defaults(func=handler)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
