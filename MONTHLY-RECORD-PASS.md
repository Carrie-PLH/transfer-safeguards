# Monthly change record pass — Room & Recourse

The complete instruction set for the `rr-monthly-change-record` scheduled task.
Everything below the `---` is the prompt. A pass run from a reconstructed
version of these instructions is worse than no pass: it would write into the
record while missing the constraints that make the writes trustworthy.

One of four copies, one per collection, under this portfolio's rule against a
shared library across repositories. The copies are kept identical except where
the collection genuinely differs, so a real fix has to be made in each by hand.

The pass produces a triage draft and reports. **It does not write the issue,
edit any page, touch `site/`, or deploy.** Writing a change-record entry is a
judgement about what a change means to a reader, and that stays with a session
that has Carrie in it (FA-D-20260831-09). An unattended pass may exercise a
method; it may not redefine one.

---

Run the monthly change record pass for Room & Recourse (roomandrecourse.com).

## Constraints

- Work directly. Do not spawn subagents.
- Do not perform general repository exploration.
- Treat `tools/record-digest.py` output as the evidence and the only evidence.
- Never edit a published page or anything under `site/`.
- Never run `anchor.py run`, `capture.py`, `retain-packet.py`, or any deploy.
- Never edit or delete anything under `tools/packets/history/` or `anchors/`.
- Never write a finding you did not read in the captures the tool names.
- Do not create empty commits.

Base path: `/Users/carries/Projects/Field Assembly/transfer-safeguards`

This collection publishes `site/states/`, one page per state.

## 1. Read the repository before reporting on it

```bash
python3 ../field-assembly-standard/tools/portfolio-status.py
```

Report what it prints about this repo. If it will not run, say so and continue.

## 2. Confirm the tool still passes its own tests

```bash
python3 tools/record-digest.py --self-test
python3 tools/record-digest.py --tripwire alabama
```

Both must pass. If either fails, stop: write no draft, commit nothing, and
report the failure prominently. A triage tool that cannot prove it reacts is not
evidence, and a draft built on it would carry a machine's authority into a
public page.

## 3. Run the triage for last month

The default window is the previous calendar month, so no dates are needed when
this runs on the first of the month.

```bash
python3 tools/record-digest.py
python3 tools/record-digest.py --draft > change-record/drafts/<YYYY-MM>.md
```

Use last month's year and month in the filename. Create
`change-record/drafts/` if it does not exist. A non-zero exit means a manifest
named a capture that is not on disk: report that prominently, keep the draft,
and say the series is incomplete.

A candidate reported as `no superseded capture recorded` is a question about the
retention series rather than a finding about any source. Report it as such and
do not write it into an issue.

## 4. Triage each candidate, and change nothing

For every candidate finding, open the two captures the tool names under
`tools/packets/history/<slug>/` and decide which of the three drift kinds it is.
Only the third belongs in a public issue:

- a page quoting words no source published;
- a page stating a fact the capture never reached, usually a narrow recipe scope
  rather than any movement by the publisher;
- a quotation the source now states in different words.

Two signals decide most of it. **The transport line.** Where the tool reports
that the capture method changed between the two captures, read it as extraction
before reading it as movement — that is what separates a real revision from
extraction noise. **Addresses and stated dates.** A changed URL is independent
of extraction, so a moved document is a finding on its own even where the text
verifies; and a publisher's own revision date moving is the publisher saying it
revised the document.

Append your reading to the draft under each candidate as
`TRIAGE: <kind> — <one sentence, and the capture you read>`. Do not rewrite the
tool's evidence lines, and do not delete a candidate you decided against —
record the decision.

## 5. Commit the draft

```bash
git status --short
```

If anything appears outside `change-record/`, leave it untouched and name it in
the report. Then stage that path only:

```bash
git add change-record/
git commit -m "change record: <YYYY-MM> triage draft"
git push origin main
```

If push fails, leave the commit in place, report the error verbatim, and do not
force-push, rebase, or resolve divergence.

## 6. Report

Keep it brief:

- what `portfolio-status.py` said about this repo;
- self-test and tripwire results;
- passes in the window, by result;
- candidates, with your triage kind for each;
- the drift events attributable to this project's own extraction or filters;
- the draft's path, and the commit and push results;
- what a session with Carrie in it has to do next.

Say plainly that the issue is unwritten. The draft is evidence and a set of
TODOs; publishing needs a person.

## What the pass must never publish

The retained captures, the diffs and the manifests sit outside `site/` under the
tier boundary and stay there. An issue quotes specific superseded and current
wording; it never carries this report, a diff, or a manifest line. Issues
publish at `/changes/`, which is separate from any reader-facing records page.
