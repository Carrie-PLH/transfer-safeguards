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
    python3 tools/spn.py run    [--budget N] [--max-attempts M] [--slug SLUG] [--retry-blocked] [--no-record] [--no-confirm]
    python3 tools/spn.py confirm [--slug SLUG] [--no-record]
    python3 tools/spn.py record [--slug SLUG] [--dry-run]
    python3 tools/spn.py status [--slug SLUG]
    python3 tools/spn.py --self-test

--budget is a target number of *captures stored*, not attempts. A run keeps
working down the candidate list until that many sources have a capture stored
by Save Page Now, so a night of heavy refusals costs more attempts rather than
fewer captures. Those captures are confirmed by the *following* pass, so one
night's run reports what it stored and the next reports what it confirmed.
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

Playback is confirmed on the pass *after* the one that stored the capture
(owner decision FA-D-20261116-01, 2026-11-16). Reading a capture back seconds
after it stored put the read inside the window in which web.archive.org's
replay path was throttling this machine, so a capture that had in fact stored
was discarded as unreadable and its source rested a week for a condition that
was not its doing. A capture read back the next night is hours old, whatever
throttle was running has had a night to lapse, and a refusal then is far more
likely to be about the capture.

So a source passes through three ledger states, and only the second is a
capture on the record:

    PENDING   stored by Save Page Now with HTTP 200 and a timestamp, not yet
              read back. Never written to a page, never counted as a capture,
              and never captured again while it stands.
    OK        read back HTTP 200. Now a capture, and now eligible for an entry.
    FAILED    a definite refusal, at submission or at the read.

The confirmation can fail for unrelated reasons that must not be recorded
alike (2026-11-15):

* The capture does not play back -- `no-playback`. The ordinary refusal. The
  source rests RETRY_AFTER_DAYS and rejoins the list in its own place.
* web.archive.org is rate-limiting this account's playback reads (HTTP 429) --
  `playback-429`. Nothing has been learned about the capture or its host, so
  the attempt is recorded SKIPPED, the source neither rests nor moves toward
  BLOCK_AFTER, and the run stops, exactly as it does on the daily capture cap.

Submission has an account condition of its own, handled the same way since
2026-11-15: a 401 from Save Page Now (`submit-401`) means this account's keys
are missing, stale or wrong. It too is recorded SKIPPED and stops the run,
rather than resting a source that refused nothing. Until that day it was in
neither set, so a stale-key morning cost eighteen sped-safeguards sources a
week each and left 395 submit-401 records across Gathered Work.

Until 2026-11-15 `playback_ok` caught every exception alike and returned a
bare False, so a 429 was indistinguishable from an unplayable capture. The
cost was not theoretical. In Gathered Work that night a pass recorded four
duquesne sources as FAILED/no-playback and rested each a week, and two of the
four had a stored HTTP 200 capture at the moment they were written off. A
capture submitted while the limit holds may well be stored; this script claims
nothing about it either way and will attempt the source again rather than
record an unconfirmed one.

Recording a capture on the page (2026-10-06)
--------------------------------------------
Carrie decided on 2026-10-06, for every collection, that the pass writes the
change-log entry itself: in gathered work no session had been writing them,
and 594 confirmed captures sat in the ledger with nothing on the page. The
wording is fixed, so nothing about the entry needs a judgement; what stays
with a person is reviewing, which the entry never claims.

`record` writes, for every page with ledger-confirmed captures the page does
not yet link, one dated entry in this repo's own change-log dialect (the
REPO-SPECIFIC block below says where it goes and what it looks like). `run` calls it at the
start of a pass, for the captures that pass has just confirmed -- so an entry
follows its capture by one night, which is the cost of confirming a capture
that is old enough to be read back honestly; `--no-record` leaves the
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
#
# playback-429 joined on 2026-11-15, for the same reason and after the same
# kind of mistake. web.archive.org rate-limits playback reads per account, and
# playback_ok caught every exception alike, so a 429 read exactly like a
# capture that would not play back: the run recorded FAILED, rested the source
# a week, and discarded a capture that had in fact stored. Found in Gathered
# Work, where four duquesne sources were rested that way before the pass was
# stopped, and two of the four had a stored HTTP 200 capture at the time. A
# rate limit is about the night, not the source.
#
# submit-401 joined on 2026-11-15, the same day and for the same reason as
# playback-429. Save Page Now stopped accepting anonymous saves, so a 401 on
# submission means this account's keys are missing, stale or wrong -- a fact
# about the account, never about the source. It sat in neither set, so every
# 401 was recorded FAILED and rested its source a week: on the morning the
# owner's keys went stale, one sped-safeguards pass rested eighteen sources
# that way, and 395 sources across Gathered Work carried a submit-401 record.
# None of them had refused anything.
ACCOUNT_LIMIT = {"error:too-many-daily-captures", "playback-429", "submit-401"}

# Why a run stopped, in the words the stop deserves. Keyed by the ACCOUNT_LIMIT
# detail that tripped it, because the two conditions call for different things
# from whoever reads the output.
ACCOUNT_LIMIT_NOTE = {
    "error:too-many-daily-captures":
        "The account's daily capture limit was reached. Every source "
        "attempted after this point would fail for a reason that is not "
        "about the source, so the run stops here. Nothing is blocked and "
        "nothing is resting on account of it; the remaining candidates were "
        "simply not reached. Do not re-run tonight, and do not raise the "
        "budget to compensate - the cap is the finding.",
    "playback-429":
        "web.archive.org is rate-limiting this account's playback reads "
        "(HTTP 429). A capture cannot be confirmed while that holds, and "
        "every source attempted after this point would fail for the same "
        "reason, which is not about the source, so the run stops here. "
        "Nothing is blocked and nothing is resting on account of it; the "
        "remaining candidates were simply not reached. Note that a capture "
        "submitted under this condition may well have stored even though it "
        "could not be confirmed - this pass claims nothing about it either "
        "way, and a later pass will attempt the source again. Wait for the "
        "limit to clear rather than re-running tonight, and do not raise the "
        "budget to compensate - the limit is the finding.",
    "submit-401":
        "Save Page Now refused the submission with HTTP 401, which means this "
        "account's keys are missing, stale or wrong -- nothing about the "
        "source. Every source attempted after this point would be refused the "
        "same way, so the run stops here. Nothing is blocked and nothing is "
        "resting on account of it; the remaining candidates were simply not "
        "reached. Generate fresh keys at https://archive.org/account/s3.php, "
        "write them to ~/.config/ia/spn.env as IA_ACCESS_KEY and "
        "IA_SECRET_KEY, and run again. Do not raise the budget and do not "
        "keep attempting sources in the hope that one slips through - the "
        "refusal is the finding.",
}

# Polling cadence for a submitted job. Widened from 6s/70 polls on 2026-11-16:
# the window is the same ~7 minutes at 2.5x fewer requests against
# web.archive.org, which is the host doing the throttling. A pass used to send
# up to seventy status polls per capture, which was the bulk of its own load.
POLL_INTERVAL = 15
POLL_LIMIT = 28          # ~7 minutes before a job is called a timeout
PACE_SECONDS = 12        # between sources; SPN caps concurrent sessions
SESSION_LIMIT_WAIT = 90
SESSION_LIMIT_TRIES = 6

# How long a stored capture may wait to be confirmed before the pass stops
# waiting on it. A read that is throttled never expires a pending, however old
# -- that would charge a source for a condition that is not its doing. Only an
# inconclusive read this long after the capture stored writes it off.
PENDING_EXPIRY_DAYS = 30

# Column width for a slug in this repository's own output.
SLUG_WIDTH = 14


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


def note_attempt(ledger, url, slug, result, detail="", message="", bump=True):
    """Record one attempt. `bump` is False for a confirmation, which is the
    second half of an attempt already counted, not a new one."""
    rec = ledger["sources"].setdefault(url, {})
    rec["page"] = slug
    rec["last_attempt"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    rec["last_result"] = result
    if bump:
        rec["attempts"] = rec.get("attempts", 0) + 1
    if detail:
        rec["last_detail"] = detail
    if message:
        # What Save Page Now actually said. Recorded since 2026-11-16 because
        # it was being thrown away: `error:no-request` is the largest failure
        # class in the portfolio and appears nowhere in SPN's documented
        # status_ext table, so nothing on disk said what it meant.
        rec["last_message"] = message[:500]
    if detail in ACCOUNT_LIMIT:
        # Not the source's doing. Record the attempt honestly, but do not let
        # it rest the source (is_cooling reads last_result) and do not count it
        # toward blocking.
        rec["last_result"] = "SKIPPED"
    elif result in ("OK", "PENDING"):
        # A stored capture means the host served the archiver, whether or not
        # the capture has been read back yet.
        rec["consecutive_hard_failures"] = 0
    elif detail in HARD_FAILURES:
        rec["consecutive_hard_failures"] = rec.get("consecutive_hard_failures", 0) + 1
    return rec


def is_pending(ledger, url):
    """True when a capture is stored for this source but not yet confirmed."""
    rec = ledger["sources"].get(url)
    return bool(rec and rec.get("last_result") == "PENDING" and rec.get("capture"))


def is_confirmed(ledger, url, page=None):
    """True when a capture for this source has been read back (OK) -- for
    `page`, if given, which must be the page the ledger record belongs to. If
    that page does not link it yet, the capture is waiting for its change-log
    entry, not for another capture: capturing again would overwrite the
    confirmed record with a new PENDING one and the entry would never be
    written (the repeat-capture loop found 2026-11-21).

    The page test matters because the ledger keeps one record per URL, and a
    source several pages link (a system-wide policy, a state code) belongs to
    whichever page captured it first. Another page linking the same URL gets
    no entry from that record, so for it the source is still a candidate."""
    rec = ledger["sources"].get(url)
    return bool(rec and rec.get("last_result") == "OK" and rec.get("capture")
                and (page is None or rec.get("page") == page))


def pending_records(ledger, slug=None):
    """[(url, rec)] awaiting confirmation, oldest submission first."""
    rows = [(url, rec) for url, rec in ledger["sources"].items()
            if rec.get("last_result") == "PENDING" and rec.get("capture")
            and (slug is None or rec.get("page") == slug)]
    rows.sort(key=lambda row: (row[1].get("capture_submitted", ""), row[0]))
    return rows


def pending_expired(rec, now=None):
    """True when a pending has sat unconfirmable past PENDING_EXPIRY_DAYS.

    Read from the submission stamp, never from last_attempt: a confirmation
    attempt must not renew the clock on the capture it failed to read.
    """
    stamp = rec.get("capture_submitted") or rec.get("last_attempt")
    if not stamp:
        return False
    try:
        when = datetime.strptime(stamp, "%Y-%m-%dT%H%M%SZ").replace(
            tzinfo=timezone.utc)
    except ValueError:
        return False
    now = now or datetime.now(timezone.utc)
    return (now - when).total_seconds() > PENDING_EXPIRY_DAYS * 86400


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
    """Capture one URL. Returns (capture_url_or_None, detail, message).

    `message` is whatever Save Page Now said about a refusal. It was being
    discarded until 2026-11-16, which is why `error:no-request` -- the largest
    failure class in the portfolio -- is classified from its code alone.
    """
    job, failure = submit(url, auth)
    if not job:
        return None, failure, ""

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
        return None, "timeout", ""
    message = str(final.get("message") or "").strip()
    if final.get("status") == "error":
        return None, final.get("status_ext") or "error", message

    http_status = final.get("http_status")
    timestamp = final.get("timestamp")
    if http_status and int(http_status) != 200:
        # Stored, but what was stored is a refusal or a challenge page.
        return None, "http-%s" % http_status, message
    if not timestamp:
        return None, "no-timestamp", message
    return "https://web.archive.org/web/%s/%s" % (timestamp, url), "ok", message


def playback_ok(capture_url, tries=1):
    """Confirm a capture plays back. Returns a (played, detail) pair, because
    the ways a read can come back negative call for opposite handling:

        (True,  None)             plays back, HTTP 200 -- a capture
        (False, "no-playback")    a definite HTTP refusal; the ordinary
                                  failure, which rests the source a week
        (False, "playback-429")   web.archive.org is rate-limiting this
                                  machine's replay reads. Nothing has been
                                  learned about the capture, so the source
                                  must not pay for it.
        (False, "inconclusive")   the read itself failed -- network, timeout.
                                  Also says nothing about the capture.

    One read by default since 2026-11-16. The caller now reads a capture back
    on the pass after the one that stored it, so there is no propagation delay
    left to wait out, and four reads per capture multiplied this pass's own
    load on the exact path doing the throttling. `tries` is kept for an
    attended confirmation of a capture made minutes ago, where a 404 may still
    be propagation. A 429 is remembered across tries and decides the verdict:
    once the far side is refusing reads, a later 404 says nothing either.
    """
    rate_limited = False
    unread = False
    tries = max(1, tries)
    for attempt in range(tries):
        try:
            req = urllib.request.Request(capture_url, method="HEAD")
            req.add_header("User-Agent", "Mozilla/5.0")
            if urllib.request.urlopen(req, timeout=60).status == 200:
                return True, None
            return False, "no-playback"
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                rate_limited = True
            if attempt + 1 < tries:
                time.sleep(25 * (attempt + 1))
        except Exception:                                     # noqa: BLE001
            unread = True
            if attempt + 1 < tries:
                time.sleep(25 * (attempt + 1))
    if rate_limited:
        return False, "playback-429"
    return False, ("inconclusive" if unread else "no-playback")


def confirm_pending(ledger, slug=None, now=None):
    """Read back every capture awaiting confirmation. Returns a result dict.

    Four outcomes, three of which are not the capture's fault:

        confirmed   plays back HTTP 200. Now, and only now, a capture.
        unplayable  a definite HTTP refusal. The ordinary failure: the source
                    rests RETRY_AFTER_DAYS and is captured again later.
        left        the read was throttled or inconclusive. Nothing was
                    learned, so the pending stands and nothing rests. A 429
                    stops the confirmation pass, because every later read
                    would be refused alike -- but it does not stop the capture
                    pass that follows, which runs against the authenticated
                    save path rather than the replay path.
        expired     inconclusive for longer than PENDING_EXPIRY_DAYS, so it is
                    written off rather than carried forever. A throttled read
                    never expires one.
    """
    now = now or datetime.now(timezone.utc)
    out = {"confirmed": [], "unplayable": [], "expired": [], "left": [],
           "stopped": None}
    for url, rec in pending_records(ledger, slug):
        page = rec.get("page", "")
        capture_url = rec["capture"]
        submitted = rec.get("capture_submitted", "")
        played, why = playback_ok(capture_url)
        if played:
            fresh = note_attempt(ledger, url, page, "OK", "ok", bump=False)
            fresh["capture"] = capture_url
            if submitted:
                fresh["capture_submitted"] = submitted
            out["confirmed"].append((page, url, capture_url))
        elif why == "no-playback":
            note_attempt(ledger, url, page, "FAILED", "no-playback", bump=False)
            out["unplayable"].append((page, url, capture_url))
        elif why == "playback-429":
            out["left"].append((page, url, why))
            out["stopped"] = why
            break
        elif pending_expired(rec, now):
            note_attempt(ledger, url, page, "FAILED", "pending-expired",
                         bump=False)
            out["expired"].append((page, url, capture_url))
        else:
            out["left"].append((page, url, why))
    return out


def run_confirmation(ledger, slug=None):
    """Confirm earlier captures and report. Returns the slugs confirmed."""
    rows = pending_records(ledger, slug)
    if not rows:
        print("No captures are awaiting confirmation.\n")
        return set()
    print("Confirming %d capture(s) stored by an earlier pass." % len(rows))
    out = confirm_pending(ledger, slug)
    save_ledger(ledger)
    for page, url, _ in out["confirmed"]:
        print("CONFIRM   %-*s %s" % (SLUG_WIDTH, page, url))
    for page, url, _ in out["unplayable"]:
        print("UNPLAYED  %-*s %s" % (SLUG_WIDTH, page, url))
    for page, url, _ in out["expired"]:
        print("EXPIRED   %-*s %s" % (SLUG_WIDTH, page, url))
    for page, url, why in out["left"]:
        print("PENDING   %-*s %-14s %s" % (SLUG_WIDTH, page, why, url))
    print("%d confirmed, %d did not play back, %d expired, %d still pending."
          % (len(out["confirmed"]), len(out["unplayable"]),
             len(out["expired"]), len(out["left"])))
    if out["stopped"] == "playback-429":
        print("\nweb.archive.org is rate-limiting this machine's playback "
              "reads (HTTP 429), so confirmation stops here. The captures "
              "above stay pending: nothing is lost, nothing rests, and a "
              "later pass reads them again. The capture pass is unaffected -- "
              "it uses the authenticated save path, not the replay path. Do "
              "not re-read them tonight; the limit is the finding.")
    print()
    return {page for page, _, _ in out["confirmed"]}


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
                # The date the capture was made, not the date it was
                # confirmed: a confirmation rewrites last_attempt, and the
                # entry's claim is about when the capture was requested.
                when = (rec.get("capture_submitted")
                        or rec.get("last_attempt") or "")[:10]
                rows.append((when, url, rec["capture"]))
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
    skipped_pending = []
    for page_slug, info in scan_all(slug).items():
        for url in info["needed"]:
            if is_pending(ledger, url) or is_confirmed(ledger, url, page_slug):
                # A confirmed (OK) source lands here only when its page entry
                # was not written -- a page `record` skipped, or --no-record.
                # It needs that entry, not a second capture.
                # A capture is already stored for this source and is waiting to
                # be read back. Capturing it again would spend the budget on a
                # source that already has what it needs, and --retry-blocked
                # deliberately does not override this.
                skipped_pending.append((page_slug, url))
                continue
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
    return fresh + due, skipped_blocked, skipped_cooling, skipped_pending


def cmd_plan(args):
    ledger = load_ledger()
    picked, blocked, cooling, pending = select(ledger, args.slug,
                                               args.retry_blocked)
    ceiling = args.max_attempts or (args.budget * ATTEMPT_CEILING_FACTOR)
    print("Target: %d capture(s), attempting at most %d source(s).\n"
          "%d candidate(s) available, in this order:\n"
          % (args.budget, ceiling, len(picked)))
    for slug, url in picked[:ceiling]:
        print("  %-*s %s" % (SLUG_WIDTH, slug, url))
    if len(picked) > ceiling:
        print("  \u2026 and %d more beyond the attempt ceiling."
              % (len(picked) - ceiling))
    if pending:
        print("\n%d source(s) already hold a capture awaiting confirmation; "
              "they are not candidates:\n" % len(pending))
        for slug, url in pending:
            print("  %-*s %s" % (SLUG_WIDTH, slug, url))
    if blocked:
        print("\n%d source(s) held back after %d consecutive hard failures "
              "(--retry-blocked to include):\n" % (len(blocked), BLOCK_AFTER))
        for slug, url in blocked:
            detail = ledger["sources"][url].get("last_detail", "")
            print("  %-*s %-8s %s" % (SLUG_WIDTH, slug, detail, url))
    if cooling:
        print("\n%d source(s) resting until %d days after their last failure:\n"
              % (len(cooling), RETRY_AFTER_DAYS))
        for slug, url in cooling:
            detail = ledger["sources"][url].get("last_detail", "")
            print("  %-*s %-8s %s" % (SLUG_WIDTH, slug, detail, url))


def cmd_status(args):
    ledger = load_ledger()
    total_needed = 0
    total_pending = 0
    for slug, info in scan_all(args.slug).items():
        blocked = sum(1 for u in info["needed"] if is_blocked(ledger, u))
        pending = sum(1 for u in info["needed"] if is_pending(ledger, u))
        total_needed += len(info["needed"])
        total_pending += pending
        flags = []
        if pending:
            flags.append("%d awaiting confirmation" % pending)
        if blocked:
            flags.append("%d blocked" % blocked)
        flag = "  (%s)" % ", ".join(flags) if flags else ""
        print("%-*s captured %2d   needs %2d%s"
              % (SLUG_WIDTH, slug, info["captured"], len(info["needed"]), flag))
    print("\n%d source(s) outstanding across all pages." % total_needed)
    if total_pending:
        print("%d of them already hold a capture awaiting confirmation by the "
              "next pass; they are not captured again." % total_pending)


def record_confirmed(ledger, pages, no_record):
    """Write change-log entries for the captures this pass confirmed."""
    if not pages:
        return
    if no_record:
        print("\n--no-record: confirmed captures are in the ledger but NOT on "
              "any page. Run `spn.py record` or write the entries by hand "
              "for: %s" % ", ".join(sorted(pages)))
        return
    print("\nRecording newly confirmed captures on their pages:")
    written, skipped = record_pages(ledger, set(pages))
    report_recording(written, skipped)


def cmd_run(args):
    auth = load_auth()
    ledger = load_ledger()

    # Confirmation first. The captures read here were stored by an earlier
    # pass and are hours old, which is the whole point of separating the two
    # halves (FA-D-20261116-01).
    confirmed_pages = set()
    if args.no_confirm:
        print("--no-confirm: earlier captures are left awaiting confirmation.\n")
    else:
        confirmed_pages = run_confirmation(ledger, args.slug)

    # Write the entries for what was just confirmed *before* choosing what to
    # capture. Until 2026-11-21 this ran at the end of the pass, so a source
    # confirmed a minute earlier still looked uncaptured to select(), was
    # captured again, and its OK record was overwritten with PENDING before
    # the recording step could see it: confirmed nightly, never on a page.
    record_confirmed(ledger, confirmed_pages, args.no_record)

    picked, blocked, cooling, pending = select(ledger, args.slug,
                                               args.retry_blocked)
    ceiling = args.max_attempts or (args.budget * ATTEMPT_CEILING_FACTOR)

    if not picked:
        print("Nothing to capture.")
        if pending:
            print("%d source(s) awaiting confirmation by a later pass."
                  % len(pending))
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
    if pending:
        print("%d source(s) already hold a capture awaiting confirmation; "
              "they are not captured again." % len(pending))
    print()
    results = {"stored": [], "failed": []}
    attempts = 0

    for slug, url in picked:
        if len(results["stored"]) >= args.budget or attempts >= ceiling:
            break
        attempts += 1
        capture_url, detail, message = capture(url, auth)

        if capture_url:
            rec = note_attempt(ledger, url, slug, "PENDING", "stored")
            rec["capture"] = capture_url
            rec["capture_submitted"] = rec["last_attempt"]
            results["stored"].append((slug, url, capture_url))
            print("STORED  %-*s %s" % (SLUG_WIDTH, slug, url))
            print("        -> %s" % capture_url)
        else:
            rec = note_attempt(ledger, url, slug, "FAILED", detail, message)
            if detail in ACCOUNT_LIMIT:
                save_ledger(ledger)
                print("STOP    %-*s %-22s %s" % (SLUG_WIDTH, slug, detail, url))
                print("\n" + ACCOUNT_LIMIT_NOTE[detail])
                break
            hard = rec.get("consecutive_hard_failures", 0)
            note = "  [blocked after %d]" % hard if hard >= BLOCK_AFTER else ""
            results["failed"].append((slug, url, detail))
            print("FAILED  %-*s %-22s %s%s" % (SLUG_WIDTH, slug, detail, url, note))
            if message:
                print("        said: %s" % message[:200])

        save_ledger(ledger)
        time.sleep(PACE_SECONDS)

    print("\n%d stored, %d failed, %d attempted."
          % (len(results["stored"]), len(results["failed"]), attempts))
    if len(results["stored"]) < args.budget:
        if attempts >= ceiling:
            print("Stopped at the attempt ceiling of %d before reaching the "
                  "target of %d capture(s). The far side refused more than "
                  "usual tonight; the shortfall is not an error."
                  % (ceiling, args.budget))
        else:
            print("Candidate list exhausted at %d stored capture(s); nothing "
                  "further was available to attempt." % len(results["stored"]))
    if results["stored"]:
        print("None of them is a capture on the record yet: each is in the "
              "ledger as PENDING, on no page, until the next pass reads it "
              "back.")


def cmd_confirm(args):
    ledger = load_ledger()
    pages = run_confirmation(ledger, args.slug)
    record_confirmed(ledger, pages, args.no_record)


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

    # ---------------------------------------------------------------- 429
    # A rate-limited playback read is not a verdict on the capture. These
    # checks pin the distinction the 2026-11-15 Gathered Work case turned on.
    check(set(ACCOUNT_LIMIT) <= set(ACCOUNT_LIMIT_NOTE),
          "every ACCOUNT_LIMIT detail has a stop message")

    saved_urlopen, saved_sleep = urllib.request.urlopen, time.sleep
    try:
        time.sleep = lambda _s: None

        def raise_code(code):
            def _open(req, timeout=None):
                raise urllib.error.HTTPError(
                    req.full_url, code, "test", {}, None)
            return _open

        urllib.request.urlopen = raise_code(429)
        check(playback_ok("https://web.archive.org/web/1/https://x.gov/a")
              == (False, "playback-429"), "429 playback reads as playback-429")

        urllib.request.urlopen = raise_code(404)
        check(playback_ok("https://web.archive.org/web/1/https://x.gov/a")
              == (False, "no-playback"), "404 playback reads as no-playback")

        class _Resp:
            status = 200

        urllib.request.urlopen = lambda req, timeout=None: _Resp()
        check(playback_ok("https://web.archive.org/web/1/https://x.gov/a")
              == (True, None), "200 playback reads as a capture")
    finally:
        urllib.request.urlopen, time.sleep = saved_urlopen, saved_sleep

    # A playback-429 attempt is recorded, but costs the source nothing.
    led = {"sources": {}}
    rec = note_attempt(led, "https://x.gov/a", "x", "FAILED", "playback-429")
    check(rec["last_result"] == "SKIPPED", "playback-429 records SKIPPED")
    check(rec.get("consecutive_hard_failures", 0) == 0,
          "playback-429 does not count toward blocking")
    check(not is_cooling(led, "https://x.gov/a"),
          "playback-429 does not rest the source")
    check(not is_blocked(led, "https://x.gov/a"),
          "playback-429 does not block the source")

    # A refused submission is the account's fault too, and costs no more.
    led3 = {"sources": {}}
    rec3 = note_attempt(led3, "https://x.gov/c", "x", "FAILED", "submit-401")
    check(rec3["last_result"] == "SKIPPED", "submit-401 records SKIPPED")
    check(rec3.get("consecutive_hard_failures", 0) == 0,
          "submit-401 does not count toward blocking")
    check(not is_cooling(led3, "https://x.gov/c"),
          "submit-401 does not rest the source")

    # The ordinary refusal still rests the source, which is the contrast.
    led2 = {"sources": {}}
    note_attempt(led2, "https://x.gov/b", "x", "FAILED", "no-playback")
    check(is_cooling(led2, "https://x.gov/b"), "no-playback still rests")

    # ------------------------------------------------ deferred confirmation
    # A capture is stored on one pass and confirmed on the next
    # (FA-D-20261116-01). These checks pin that a pending is not a capture, is
    # never captured again, and that only a definite refusal costs its source.
    led4 = {"sources": {}}
    rec4 = note_attempt(led4, "https://x.edu/p", "x", "PENDING", "stored")
    rec4["capture"] = "https://web.archive.org/web/1/https://x.edu/p"
    rec4["capture_submitted"] = rec4["last_attempt"]
    check(is_pending(led4, "https://x.edu/p"), "a stored capture reads as pending")
    check(not is_cooling(led4, "https://x.edu/p"), "a pending does not rest its source")
    check(rec4["consecutive_hard_failures"] == 0, "a stored capture clears hard failures")

    saved_scan = globals()["scan_all"]
    try:
        globals()["scan_all"] = lambda slug=None: {
            "x": {"needed": ["https://x.edu/p", "https://x.edu/q"], "captured": 0}}
        check(unrecorded(led4) == {}, "a pending is never written to a page")
        picked, _b, _c, pend = select(led4, None, False)
        check([u for _, u in pend] == ["https://x.edu/p"],
              "select holds a pending source back")
        check("https://x.edu/p" not in [u for _, u in picked],
              "a pending source is never captured again")
        _p2, _b2, _c2, pend2 = select(led4, None, True)
        check([u for _, u in pend2] == ["https://x.edu/p"],
              "--retry-blocked does not override a pending")
        # Repeat-capture loop (2026-11-21): a source confirmed this pass but
        # not yet on its page must not be captured again, or its OK record
        # is overwritten with PENDING and its entry is never written.
        rec5 = note_attempt(led4, "https://x.edu/q", "x", "OK", "playback")
        rec5["capture"] = "https://web.archive.org/web/2/https://x.edu/q"
        check(is_confirmed(led4, "https://x.edu/q"), "an OK capture reads as confirmed")
        picked5, _b5, _c5, pend5 = select(led4, None, False)
        check("https://x.edu/q" not in [u for _, u in picked5],
              "a confirmed source awaiting its entry is never captured again")
        check(sorted(u for _, u in pend5) == ["https://x.edu/p", "https://x.edu/q"],
              "select holds a confirmed-but-unrecorded source back")
        rec5["page"] = "y"
        picked6, _b6, _c6, _p6 = select(led4, None, False)
        check("https://x.edu/q" in [u for _, u in picked6],
              "a source confirmed for another page stays a candidate here")
    finally:
        globals()["scan_all"] = saved_scan

    saved_urlopen, saved_sleep = urllib.request.urlopen, time.sleep
    try:
        time.sleep = lambda _s: None

        class _Ok:
            status = 200

        def _raise(code):
            def _open(req, timeout=None):
                raise urllib.error.HTTPError(req.full_url, code, "t", {}, None)
            return _open

        # Confirmed: a pending becomes a capture, keeping its submission date
        # and without recounting the attempt.
        led5 = json.loads(json.dumps(led4))
        urllib.request.urlopen = lambda req, timeout=None: _Ok()
        out = confirm_pending(led5)
        check([p for p, _, _ in out["confirmed"]] == ["x"], "200 confirms a pending")
        rec5 = led5["sources"]["https://x.edu/p"]
        check(rec5["last_result"] == "OK", "a confirmed pending records OK")
        check(rec5["capture_submitted"] == rec4["capture_submitted"],
              "confirmation keeps the capture's own date")
        check(rec5["attempts"] == rec4["attempts"],
              "confirmation does not recount the attempt")

        # Throttled: the pending stands, nothing rests, confirmation stops.
        led6 = json.loads(json.dumps(led4))
        urllib.request.urlopen = _raise(429)
        out = confirm_pending(led6)
        check(out["stopped"] == "playback-429", "a throttled read stops confirmation")
        check(led6["sources"]["https://x.edu/p"]["last_result"] == "PENDING",
              "a throttled read leaves the pending standing")
        check(not is_cooling(led6, "https://x.edu/p"), "a throttled read rests nothing")

        # A definite refusal is the one outcome that costs the source.
        led7 = json.loads(json.dumps(led4))
        urllib.request.urlopen = _raise(404)
        out = confirm_pending(led7)
        check([p for p, _, _ in out["unplayable"]] == ["x"], "404 is unplayable")
        check(is_cooling(led7, "https://x.edu/p"),
              "an unplayable capture rests its source")

        # An unreadable network is inconclusive: it stands while young and is
        # written off once stale, and a throttle never expires one.
        def _down(req, timeout=None):
            raise OSError("network down")

        led8 = json.loads(json.dumps(led4))
        urllib.request.urlopen = _down
        out = confirm_pending(led8)
        check([w for _, _, w in out["left"]] == ["inconclusive"],
              "a failed read is inconclusive")
        check(led8["sources"]["https://x.edu/p"]["last_result"] == "PENDING",
              "an inconclusive read leaves the pending standing")

        led9 = json.loads(json.dumps(led4))
        led9["sources"]["https://x.edu/p"]["capture_submitted"] = "2026-01-01T000000Z"
        out = confirm_pending(led9)
        check([p for p, _, _ in out["expired"]] == ["x"], "a stale pending expires")
        check(led9["sources"]["https://x.edu/p"]["last_detail"] == "pending-expired",
              "expiry is recorded as such")

        led10 = json.loads(json.dumps(led4))
        led10["sources"]["https://x.edu/p"]["capture_submitted"] = "2026-01-01T000000Z"
        urllib.request.urlopen = _raise(429)
        out = confirm_pending(led10)
        check(out["expired"] == [] and
              led10["sources"]["https://x.edu/p"]["last_result"] == "PENDING",
              "a throttled read never expires a pending, however old")
    finally:
        urllib.request.urlopen, time.sleep = saved_urlopen, saved_sleep

    check(PENDING_EXPIRY_DAYS > RETRY_AFTER_DAYS,
          "a pending outlives the rest period of the source it belongs to")
    check(POLL_INTERVAL * POLL_LIMIT >= 400,
          "the widened poll cadence still covers a slow job")
    check("pending-expired" not in HARD_FAILURES,
          "an expired pending is not counted as a host refusal")

    print("self-test: %d checks passed" % checks)


def main():
    if sys.argv[1:] == ["--self-test"]:
        self_test()
        return
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for name, handler in (("plan", cmd_plan), ("run", cmd_run),
                          ("confirm", cmd_confirm), ("record", cmd_record),
                          ("status", cmd_status)):
        sp = sub.add_parser(name)
        sp.add_argument("--slug", help="limit to one state page")
        if name == "run":
            sp.add_argument("--no-confirm", action="store_true",
                            help="do not confirm earlier captures first; "
                                 "capture only")
        if name in ("run", "confirm"):
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
