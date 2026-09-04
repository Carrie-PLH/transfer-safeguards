#!/usr/bin/env python3
"""Internet Archive Save Page Now capture worker for Room & Recourse.

Requests captures for state-page sources that have none, and reports what
happened. It never edits a page: writing the change-log entry is a judgement
call and stays with the session that runs this.

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
    python3 tools/spn.py run    [--budget N] [--max-attempts M] [--slug SLUG] [--retry-blocked]
    python3 tools/spn.py status [--slug SLUG]

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

# Hosts that are ours or infrastructure, never sources to capture.
SKIP_HOSTS = {"roomandrecourse.com", "www.roomandrecourse.com",
              "fieldassembly.net", "www.fieldassembly.net",
              "web.archive.org"}

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
                 "error:too-many-daily-captures", "http-403", "http-202"}

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
    if result == "OK":
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
    print("\nPages to record:")
    pages = sorted({slug for slug, _, _ in results["ok"]})
    for slug in pages:
        print("  %s" % slug)
    if not pages:
        print("  (none)")
    print("\nCaptures are NOT yet recorded on any page. Write the change-log "
          "entries from the results above.")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for name, handler in (("plan", cmd_plan), ("run", cmd_run), ("status", cmd_status)):
        sp = sub.add_parser(name)
        sp.add_argument("--slug", help="limit to one state page")
        if name != "status":
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
