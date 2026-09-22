# Capture recipes

A recipe records how one state's sources are read, in enough detail that
reading them again produces the same text. One JSON file per packet, named for
the slug, executed by `tools/capture.py`. This file documents the recipe format
exactly as **this repository's** `capture.py` implements it. It was adapted on
2026-09-22 from the sibling copies in `sped-safeguards/tools/recipes/README.md`
and `licensure mobility/tools/recipes/README.md` (FA-Q-20260908-03), and it
differs from both where this repo's `capture.py` differs; the differences are
listed at the end. When this file and `capture.py` disagree, `capture.py` is
right and this file is stale: fix it in the same commit.

Read `tools/capture.py`'s module docstring and the comments above each option
for the reasoning; read the CLAUDE.md sections "Capture traps", "Recipe
slicing" and "Two helpers for the recipe backfill" before writing a recipe.

## Why this exists

Before recipes, the method of capture lived only as prose in a packet's capture
notes ("pdftotext -raw for the PDF", "the workspace web_fetch tool"). Prose
cannot be re-run, so two passes over an unchanged source produced two different
texts, and the retained-versus-unchanged signal in the packet history carried
no information. A recipe makes capture deterministic: the nightly executes it
instead of reconstructing a method from a paragraph of English.

## Why a sidecar, not the SOURCE header

`retain-packet.py` compares SOURCE header lines between passes and reports any
difference as a finding, because a moved or re-dated document is a change even
when its text is not. A recipe in that line would make every recipe correction
look like source movement. The header describes the document; the recipe
describes how this project reads it. The recipe's digest is written into the
packet's capture notes, which are excluded from the body hash, so a capture can
always be traced to the recipe that produced it.

## Shape

```json
{
  "recipe_version": 1,
  "state": "south-dakota",
  "sources": [
    {
      "n": 1,
      "title": "ARSD chapter 44:73:11, Residents' Rights (...)",
      "url": "https://sdlegislature.gov/api/Rules/44%3A73",
      "source_date": "no single date for the chapter; ...",
      "transport": "curl",
      "user_agent": "browser",
      "extractor": "json-doc",
      "scope": "Html",
      "slice": {"from": "CHAPTER 44:73:11 RESIDENT'S RIGHTS", "to": "CHAPTER 44:73:12"},
      "filters": [],
      "notes": "Why this source is captured this way."
    }
  ]
}
```

Top level: `recipe_version` must be `1`; `state` must equal the file's slug
(lint checks it); `sources` is a non-empty list.

Per source, required: `n`, `title`, `url` (or `urls`), `transport`,
`extractor`. Sources are
numbered `1..n` in order and must match the standing packet's numbering and
titles — the sources are whatever the standing packet says they are.

Per source, optional: `source_date`, `scope`, `filters`, `notes`, `slice`,
`pages`, `user_agent`, `http_version`, `compressed`, `ca_bundle`, `attended`.
Each is described below. Nothing else is read.

`title`, `url` (or every entry of `urls`, joined with ` ; `) and
`source_date` populate the SOURCE header line the packet
prints (`SOURCE n: <title> | <url> | source date: <source_date> | retrieved:
<day>`); an absent `source_date` prints as "none published". `url` is the
address actually fetched, so for an API source it is the API address, and the
human-readable page belongs in `notes`. `notes` is prose for a human; it is
printed under the source in the capture notes and affects neither the capture
nor the digest.

## transport — how the bytes are obtained

| value | runs where | when to use |
|---|---|---|
| `curl` | in `capture.py` | anything a plain HTTPS request can reach |
| `web_fetch` | session tool | the host rejects curl and the session fetch tool reaches it |
| `chrome` | session tool | last resort, when the content is genuinely not in any response curl can get |

There is no `curl-cffi` transport in this repo (Board & Border has one).

The two session readers are tool calls, not subprocesses. A recipe naming one
makes `capture.py` stop, print the URL, and exit 3; fetch it with the named
reader, save the text, and re-run with `--supply N=path`. The extractor, slice
and filters still run here, and the packet marks the source "(fetched by the
session reader and supplied)". Record in `notes` exactly what was supplied (for
example `document.querySelector('main').innerText`, unedited) so the next
session supplies the same thing: a hand-trimmed supply is a hand capture.

**An empty body is not proof that a browser is needed.** Before reaching for
`chrome`, grep the raw curl response for `__NEXT_DATA__`, for other JSON
islands, and for a sentence you expect to find; and look at what the page's own
script fetches, because the content may sit one address over as plain JSON
(South Dakota's legislature, below). Bisect on `http_version` before concluding
a host refuses curl (Arizona). Prefer `curl` wherever it works: a source
reachable only through a session reader moves whenever that reader's extraction
changes, with no source change behind it.

## urls — one source served as several pages (added 2026-09-22)

A packet source can be one document published as several pages: Idaho's
source 2 is six Idaho Code sections, one legislature.idaho.gov page each, cited
on the page as one source. FA-D-20260922-02 extends the recipe rather than
renumbering published citations:

```json
"urls": ["https://.../SECT39-1301/", "https://.../SECT39-1302/"]
```

- `urls` replaces `url`; lint rejects a source carrying both, a list shorter
  than two, a page listed twice, and `urls` on any transport but `curl` or on
  an `attended` source (a joined source has no single thing to supply).
- Pages are fetched in the declared order. Each is extracted on its own, so an
  html-text `scope` applies within each page; concatenating raw HTML would keep
  only the first page's match.
- The extracted pages are joined, each under a fixed marker line
  `=== page k of N of this source: <url> ===`. The marker is structure, like a
  SOURCE header; never quote it.
- `slice` and `filters` then run once over the joined text.
- The list, in order, joins the digest; a single-`url` source hashes as before.

## Attended sources and byte supply (added 2026-09-22)

Some sources can only be obtained by a real browser, and when the extractor
needs the raw bytes (a PDF, a DOCX) the session cannot relay them through a
tool-call return: on 2026-09-15 a 19,631-byte mass.gov PDF came back as 19,148
bytes of base64 that decoded without error (FA-Q-20260915-01). FA-D-20260922-01
puts the human step at the transport and never at the extraction:

- **`"attended": true`** marks a source whose bytes are obtained in an attended
  session — a browser download the owner approves, or the owner saving the
  file. An unattended run does not fetch it: it prints `ATTENDED-ONLY` for that
  source and exits **4**, distinct from a capture failure (1) and from a
  session-reader fetch not supplied (3). The other sources still capture and the
  packet is still written; do not promote it, because it is short. `transport`
  still records how the bytes are obtained (`chrome` for a browser download).
  `attended` is not in the digest: who fetched the bytes does not change them.
- **`--supply-file N=PATH --supply-sha256 N=HEX`** hands `capture.py` the bytes
  from disk. They go through exactly the path a curl fetch's bytes would: the
  pinned pdftotext modes, pdfplumber or docx for binary extractors, and the
  same UTF-8 decode curl uses for html-text, next-data, json-doc and none. The
  packet notes record `sha256 <hex>` for the source.
- The SHA-256 is **required** and must be computed where the bytes were
  obtained — in the browser over the response it received
  (`crypto.subtle.digest`), or by the owner over the file the browser saved
  (`shasum -a 256`). Never hash the relayed file to make a check pass; a
  mismatch means the file is not what the reader saw, so re-obtain it.
- For the PDF extractors the file must also carry `%PDF-` in its first 1 KB and
  `%%EOF` in its last 1 KB, and a pdftotext probe must exit 0. Truncation, the
  one corruption actually observed, fails all three.
- A text `--supply` is refused (exit 2) for an attended source read by a binary
  extractor, and a source cannot be given both `--supply` and `--supply-file`.
  `--supply` itself is unchanged: a session reader's text for a chrome or
  web_fetch source, used as extracted text for a binary extractor (Florida) or
  run through html-text/none as before.

What an attended session does, per source: obtain the file through the browser
with the owner's approval; record the SHA-256 from the reader side; run
`tools/.venv/bin/python tools/capture.py <slug> --supply-file N=<file>
--supply-sha256 N=<hex> --out tools/packets/review/<slug>-<day>.txt` (with
`--supply` for any chrome text sources); then the verification below.

## extractor — how bytes become text

Exactly these eight names (`EXTRACTORS` in `capture.py`):

| extractor | input | notes |
|---|---|---|
| `pdftotext-raw` | PDF | poppler `-raw -enc UTF-8`; follows the content stream (reads Arizona's two-column AAC in column order) |
| `pdftotext-layout` | PDF | poppler `-layout -enc UTF-8`; keeps spacing, interleaves two-column pages (Missouri, Louisiana) |
| `pdfplumber` | PDF | pinned pdfplumber build; no recipe here uses it today |
| `html-text` | HTML | text under one CSS selector; tables pipe-delimited |
| `next-data` | HTML | a Next.js `__NEXT_DATA__` island inside the page, pathed into |
| `json-doc` | JSON | a bare JSON response body, pathed into (added 2026-09-22) |
| `docx` | DOCX / legacy DOC | paragraphs, then tables pipe-joined |
| `none` | text | the bytes as text, unextracted — for a session reader's already-flattened text |

There is no `pdftotext-plain` in this repo (both siblings have one). The
pdftotext flags and the poppler/pdfplumber builds are pinned in `capture.py`
and `capture-core.py`, never named in a recipe: a flag a recipe can vary is a
flag that will vary. `tools/.venv/bin/python tools/capture.py --preflight`
checks the pins against what this repo's recipes use.

**html-text.** Drops `script`, `style`, `noscript` and `svg`, then comments and
hidden elements (`display:none`, `visibility:hidden`, the `hidden` attribute;
not `aria-hidden`), then decodes Cloudflare-obfuscated email addresses, then
takes the node matched by `scope`. Block elements become line breaks; every
table row becomes one line with ` | ` between cells. It takes no `links` option
here (the siblings have one): link targets are not emitted.

**next-data** and **json-doc** share one path reader (`resolve_json_paths`), so
they cannot drift in how they read a path; the only difference is where the
JSON comes from. `next-data` requires a literal `<script id="__NEXT_DATA__"
type="application/json">` in an HTML response and fails with "no __NEXT_DATA__
island in this response" otherwise. `json-doc` requires the whole response body
to be JSON and fails with "response body is not JSON" otherwise. They are kept
separate because each failure is a true diagnosis of a different publisher, and
the self-test pins both directions. A path landing on a string is treated as
HTML and run through the html-text extraction (tables still pipe-delimited); a
path landing on an object or list is rendered as plain `key: value` lines, never
composed into sentences. South Dakota is the `json-doc` case:
sdlegislature.gov's rule pages are a Vue shell to curl, but
`https://sdlegislature.gov/api/Rules/<article>` (colons URL-encoded) returns
the article as JSON with the rule text, a Word HTML export, in `Html`.

**docx.** A pre-2007 binary `.doc` is detected and routed to a converter in
`capture-core.py`, which prints the converter's name to stderr (record it in
`notes`); a converted `.doc` yields prose only, with no table pass. West
Virginia's Secretary of State serves the real document only as `Format=WORD`,
which is why that state uses `docx`.

**none.** Use when a session reader has already flattened the page (Montana's
rules.mt.gov sources, South Dakota source 4). If the reader returns rendered
HTML instead, name `html-text` and supply the HTML.

## scope — what part of the document

| extractor | scope |
|---|---|
| `html-text` | required: a CSS selector (`select_one`, so the first match), or `body` for the whole document. State `body` explicitly when you mean it; an unstated scope is one nobody checked. A fragment with no `<body>` needs a real selector (Alaska's BASIS print fragment needs `div.statute`) |
| `next-data` | required: a dotted path into the island, `[i]` for list indices, or a non-empty list of such paths concatenated in order |
| `json-doc` | required: the same dotted-path vocabulary, into the response body (`Html` for sdlegislature.gov) |
| `docx` | optional: `paragraphs-only` omits tables; anything else (default `paragraphs-and-tables`) includes them |
| PDF extractors, `none` | not allowed; lint rejects it |

Find the contact facts — phone, fax, email, mailing address — before settling
a scope. They are often outside the body-copy node, and the fidelity checker
vouches for a contact only if the packet holds it. Where they sit in a sibling
of the body copy with no smaller common ancestor, the scope has to be `body`
(Minnesota source 3).

## slice — which span of a long document

```json
"slice": {"from": "<anchor>", "to": "<anchor>", "from_occurrence": 2, "to_occurrence": 1}
```

Only those four keys. `from` is required; `to` is exclusive and optional (omit
it to run to the end); both occurrences default to 1 and must be positive
integers; `to_occurrence` needs a `to`. Each anchor must be at least 12
characters (`MIN_ANCHOR`). Anchors are literal and case-sensitive, and every run
of whitespace in an anchor matches any run of whitespace in the document. A
miss is an error, never a fallback to the whole document. The slice runs after
extraction and before the filters. The full rules, and why a superset beats a
tidy slice on two-column documents, are in CLAUDE.md "Recipe slicing".
`tools/propose-slice.py <slug>` drafts anchors; read every one.

## pages — which pages of a PDF

`"pages": [first, last]`, 1-based and inclusive, PDF extractors only. For a
packet that should hold only the part of a bound document the page rests on
(Alabama, Arizona, Louisiana, Utah use it).

## filters — an ordered, closed vocabulary

Each name is a function in `capture.py`'s `FILTERS`, applied in the order
listed. Order matters: `unwrap-hard-wraps` before `strip-page-numbers` will
swallow a page number into the paragraph above it.

| filter | what it does |
|---|---|
| `trim-lines` | trailing whitespace off every line |
| `collapse-blank-runs` | three or more newlines become one blank line |
| `strip-zero-width` | removes U+200B, U+FEFF and U+2060 (CMS editor exhaust); soft hyphens kept |
| `strip-page-numbers` | drops lines that are a bare page number (arabic or roman, optional "page", optional "of N") |
| `strip-running-headers` | drops a head recurring at page breaks, splitting one fused to an interrupted sentence (implementation in `capture-core.py`) |
| `unwrap-hard-wraps` | rejoins lines broken at the document's own column width, derived from its line lengths |
| `join-wrap-hyphens` | `-\n` followed by a lowercase letter becomes `-`, keeping the hyphen; never on a typeset-hyphenated PDF (Arizona's AAC) |
| `pipe-table-cells` | normalizes an existing ` \| ` cell delimiter; infers nothing |
| `normalize-bullets` | a leading bullet glyph becomes `- ` |
| `normalize-apostrophes` | curly quotes and dashes to ASCII |
| `normalize-ligatures` | compatibility ligatures to component letters |

After the filters, any form feed left over becomes a line break
(`form_feed_to_linebreak`), so no packet carries a control character.

**Do not use `normalize-apostrophes` or `normalize-ligatures`.** They change the
publisher's characters, which puts punctuation in the evidence that the source
never printed; a page quoting the source's own curly apostrophe then fails
against a packet that straightened it. Character tolerance belongs in the
comparison, not the stored capture. Adding a filter is a code change with a
self-test; an open-ended filter field would be prose again.

## Transport options (curl only)

Each is opt-in per source, pinned to a value defined in `capture.py`, and joins
the recipe digest only when set, so a recipe that does not use it keeps the
digest already recorded in every packet it produced. Lint rejects each on a
non-curl transport.

| field | values | why |
|---|---|---|
| `user_agent` | `none` (default), `browser` | some hosts 403 a request with no user-agent; the browser string is pinned in `USER_AGENTS` |
| `http_version` | `"1.1"` only | apps.azsos.gov refuses curl's HTTP/2 and serves HTTP/1.1; des.az.gov sends a Cloudflare challenge on h2 only. Bisect on this before calling a host unreachable |
| `compressed` | `false` (omit for the default, on) | drops `--compressed` for a host whose gzip stream makes curl exit 23 with a complete body |
| `ca_bundle` | a name in `tools/certs/` (no `.pem`) | a host serving its leaf without the intermediate; verification still happens, against pinned anchors. Never `--insecure`. See `tools/certs/README.md` |

A response that comes back a few KB long with "Just a moment..." or an
Incapsula `_Incapsula_Resource` script in it is a challenge page, not the
source, and is a failed fetch. `capture.py` fails on any status other than 200.

## The digest

`--digest <slug>` prints a 12-hex hash over `n`, `url`, `transport`,
`extractor`, `scope`, `filters`, and the optional fields above when set, plus
`urls`, `slice` and `pages`. Title, `source_date`, `notes` and `attended` are
excluded: a digest
that moves when prose moves teaches people to ignore it. The packet's capture
notes record it, and `retain-packet.py` refuses a `--transport` naming a digest
the capture does not declare.

## Commands

Run under the repo's venv, not bare `python3`:

```
tools/.venv/bin/python tools/capture.py <slug>                     capture every source
tools/.venv/bin/python tools/capture.py <slug> --source 2          one source only
tools/.venv/bin/python tools/capture.py <slug> --supply 2=raw.txt  hand it a session fetch
tools/.venv/bin/python tools/capture.py <slug> --supply-file 2=doc.pdf --supply-sha256 2=<hex>
                                                            hand it bytes from an attended session
tools/.venv/bin/python tools/capture.py <slug> --out capture.txt   default: stdout
tools/.venv/bin/python tools/capture.py <slug> --date YYYY-MM-DD   the ASSEMBLED/retrieved day
tools/.venv/bin/python tools/capture.py --lint [<slug>]            validate recipes
tools/.venv/bin/python tools/capture.py --digest <slug>            recipe digest
tools/.venv/bin/python tools/capture.py --self-test
tools/.venv/bin/python tools/capture.py --preflight                pins vs. this repo's recipes
```

Exit codes: 0 clean, 1 capture failure, 2 usage or recipe error, 3 a source
needs a session fetch that was not supplied, 4 an `attended` source was not
supplied (ATTENDED-ONLY). When several apply: 1, then 3, then 4.

## Verifying a new recipe

The five steps, all passing, before a recipe is kept (the sibling CLAUDE.md
"Verifying a new recipe" sections carry the full account):

```
tools/.venv/bin/python tools/capture.py --lint <slug>
tools/.venv/bin/python tools/capture.py <slug> --out tools/packets/review/<slug>-<day>.txt
tools/.venv/bin/python tools/capture.py <slug> --out <scratch>/<slug>-again.txt     # byte-identical
python3 tools/check-fidelity.py states/<slug>.md ${(@f)"$(python3 tools/packet-set.py <slug> --review tools/packets/review/<slug>-<day>.txt)"}
python3 tools/check-fidelity.py site/states/<slug>.html ${(@f)"$(python3 tools/packet-set.py <slug> --review tools/packets/review/<slug>-<day>.txt)"}
```

That is zsh, the Mac's shell: `${(@f)...}` splits the one-per-line output on
newlines only. packet-set prints absolute paths under "Field Assembly", so any
split on spaces breaks them; `packet-set.py --args` is withdrawn and exits 2
for that reason (FA-Q-20260913-01). In bash 3.2:
`IFS=$'\n' read -r -d '' -a P < <(python3 tools/packet-set.py <slug> --review <capture>)`
then pass `"${P[@]}"`. For a supplied source, the second run proves nothing
about the supply; take the supply twice from independent navigations and
compare hashes, and say so in `notes`. Then retain and promote:

```
python3 tools/retain-packet.py tools/packets/review/<slug>-<day>.txt --result rebuild \
    --transport "curl + tools/capture.py recipe <digest>"
python3 tools/retain-packet.py --verify
python3 tools/check-all.py
```

If fidelity fails, diagnose before touching the recipe (the four categories are
in the sibling CLAUDE.md "When a new recipe's fidelity check fails"). Never edit
a packet to make a check pass.

## Drafting aids

`tools/draft-recipe.py <slug>` writes the mechanical half from the standing
packet's SOURCE headers and silently skips a header it cannot parse — check the
source count. `tools/propose-slice.py <slug>` proposes anchors. Both are drafts,
not authorities.

## Supplements

A supplemental packet `tools/packets/<slug>-packet-<kind>.txt` takes a recipe
named `<slug>-<kind>.json` whose `state` is `<slug>-<kind>`; `texas-moved.json`
(for `texas-packet-moved.txt`) is the one here today.

## Where this repo's capture.py differs from the siblings'

Checked against the code on 2026-09-22. Present in a sibling, absent here:
the `curl-cffi` transport and its `impersonate`, `warm` and `pace` fields and
`crawl_delay` (Board & Border); the `pdftotext-plain` extractor (both); the
`links` field on `html-text`/`next-data` (both); and `body_url` with the
`document` scope (Rules & Record). Present here and in neither sibling:
`http_version`, `urls`, `attended`, and `--supply-file`/`--supply-sha256`
(written here first on 2026-09-22 to be ported verbatim, FA-D-20260922-01/-02). `json-doc` was
ported from Board & Border on 2026-09-22 without its `links` pass-through;
gathered work and Rules & Record do not have it.
