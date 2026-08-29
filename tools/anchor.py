#!/usr/bin/env python3
"""External timestamp anchoring for capture archives.

What this does. Each run hashes every file under the paths listed in
tools/anchor-paths.txt, writes a manifest, appends a hash-chained entry to
anchors/chain.jsonl, and anchors the entry hash externally two ways:

  1. RFC 3161 timestamp tokens from public timestamp authorities
     (FreeTSA and DigiCert), stored in anchors/tsa/.
  2. An OpenTimestamps proof (Bitcoin-anchored via public calendar
     servers), stored in anchors/ots/ — only if the `ots` client is
     installed; skipped with a warning otherwise.

Why the entry hash and not the manifest hash: the chain entry contains the
manifest hash plus the link to the previous entry, so one external stamp
binds both the content and its position in the append-only history.

Commands:
  python3 tools/anchor.py run [--note "..."]   capture + anchor now
  python3 tools/anchor.py verify               check chain, manifests, tokens
  python3 tools/anchor.py upgrade              upgrade pending OTS proofs

No dependencies beyond the standard library. The RFC 3161 request is built
in pure Python (DER), so this works on machines whose openssl lacks the
`ts` subcommand (e.g. stock macOS LibreSSL). Verification of TSA tokens
uses `openssl ts` when available and degrades to a recorded note when not.
"""

import argparse
import hashlib
import json
import os
import secrets
import shutil
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

TSAS = [
    ("freetsa", "https://freetsa.org/tsr"),
    ("digicert", "http://timestamp.digicert.com"),
]
SKIP_DIRS = {".git", "node_modules", "__pycache__", "anchors"}
SKIP_FILES = {".DS_Store"}


def find_ots():
    """Locate the ots client even when pip's user bin dir is not on PATH."""
    found = shutil.which("ots")
    if found:
        return found
    home = Path.home()
    candidates = [home / ".local" / "bin" / "ots"]
    candidates += sorted((home / "Library" / "Python").glob("*/bin/ots"),
                         reverse=True)
    for c in candidates:
        if c.is_file() and os.access(c, os.X_OK):
            return str(c)
    return None


# ---------- helpers ----------

def repo_root() -> Path:
    # anchor.py lives in <root>/tools/
    return Path(__file__).resolve().parent.parent


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_paths(root: Path):
    pf = root / "tools" / "anchor-paths.txt"
    if not pf.exists():
        sys.exit(f"missing {pf} — one path per line, relative to repo root")
    paths = []
    for line in pf.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            paths.append(line)
    return paths


def collect_files(root: Path, rel_paths):
    files = []
    for rel in rel_paths:
        base = root / rel
        if not base.exists():
            print(f"  warning: listed path does not exist: {rel}")
            continue
        if base.is_file():
            files.append(base)
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for name in filenames:
                if name in SKIP_FILES:
                    continue
                files.append(Path(dirpath) / name)
    return sorted(set(files), key=lambda p: str(p.relative_to(root)))


def canonical(entry: dict) -> bytes:
    return json.dumps(entry, sort_keys=True, separators=(",", ":")).encode()


# ---------- DER encoding for the RFC 3161 request ----------

def _der_len(n: int) -> bytes:
    if n < 0x80:
        return bytes([n])
    b = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(b)]) + b


def _tlv(tag: int, content: bytes) -> bytes:
    return bytes([tag]) + _der_len(len(content)) + content


def _der_int(value: int) -> bytes:
    b = value.to_bytes((value.bit_length() + 8) // 8 or 1, "big")
    return _tlv(0x02, b)


def build_tsq(digest_hex: str) -> bytes:
    """TimeStampReq: v1, SHA-256 imprint, random nonce, certReq TRUE."""
    oid_sha256 = bytes.fromhex("0609608648016503040201")
    alg_id = _tlv(0x30, oid_sha256 + b"\x05\x00")
    imprint = _tlv(0x30, alg_id + _tlv(0x04, bytes.fromhex(digest_hex)))
    nonce = _der_int(secrets.randbits(64))
    cert_req = b"\x01\x01\xff"
    return _tlv(0x30, _der_int(1) + imprint + nonce + cert_req)


def request_tsa(url: str, tsq: bytes) -> bytes:
    req = urllib.request.Request(
        url, data=tsq,
        headers={"Content-Type": "application/timestamp-query"},
        method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


# ---------- commands ----------

def cmd_run(note: str | None):
    root = repo_root()
    anchors = root / "anchors"
    for sub in ("manifests", "entries", "tsa", "ots"):
        (anchors / sub).mkdir(parents=True, exist_ok=True)
    chain = anchors / "chain.jsonl"

    rel_paths = read_paths(root)
    files = collect_files(root, rel_paths)
    if not files:
        sys.exit("no files found under the listed paths; nothing to anchor")

    now = datetime.now(timezone.utc)
    run_id = now.strftime("%Y-%m-%dT%H%M%SZ")

    # 1. manifest
    lines = [f"# anchor manifest {run_id} repo={root.name}"]
    for f in files:
        lines.append(f"{sha256_file(f)}  {f.relative_to(root)}")
    manifest_path = anchors / "manifests" / f"{run_id}.txt"
    manifest_path.write_text("\n".join(lines) + "\n")
    manifest_sha = sha256_file(manifest_path)
    print(f"manifest: {len(files)} files -> {manifest_path.name}")
    print(f"manifest sha256: {manifest_sha}")

    # 2. chain entry
    prev = None
    if chain.exists():
        last = chain.read_text().strip().splitlines()
        if last:
            prev = json.loads(last[-1])["entry_sha256"]
    entry = {
        "id": run_id,
        "utc": now.isoformat(timespec="seconds"),
        "repo": root.name,
        "paths": rel_paths,
        "file_count": len(files),
        "manifest_file": f"manifests/{run_id}.txt",
        "manifest_sha256": manifest_sha,
        "prev_entry_sha256": prev,
    }
    if note:
        entry["note"] = note
    entry_sha = hashlib.sha256(canonical(entry)).hexdigest()
    record = {"entry": entry, "entry_sha256": entry_sha}
    entry_path = anchors / "entries" / f"{run_id}.json"
    entry_path.write_text(json.dumps(record, sort_keys=True, indent=1) + "\n")
    with open(chain, "a") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")
    print(f"chain entry: {entry_sha} (prev: {prev or 'none — first entry'})")

    # 3. RFC 3161 stamps of the entry hash
    for name, url in TSAS:
        try:
            tsq = build_tsq(entry_sha)
            (anchors / "tsa" / f"{run_id}-{name}.tsq").write_bytes(tsq)
            tsr = request_tsa(url, tsq)
            (anchors / "tsa" / f"{run_id}-{name}.tsr").write_bytes(tsr)
            print(f"tsa {name}: token stored ({len(tsr)} bytes)")
        except Exception as e:
            print(f"tsa {name}: FAILED — {e}")

    # 4. OpenTimestamps stamp of the entry file
    ots = find_ots()
    if ots:
        r = subprocess.run([ots, "stamp", str(entry_path)],
                           capture_output=True, text=True)
        proof = entry_path.with_suffix(entry_path.suffix + ".ots")
        if proof.exists():
            proof.rename(anchors / "ots" / proof.name)
            print("ots: proof stored (run `anchor.py upgrade` after ~24h "
                  "to collect the Bitcoin attestation)")
        else:
            print(f"ots: FAILED — {r.stderr.strip() or r.stdout.strip()}")
    else:
        print("ots: client not installed, skipped "
              "(pip install opentimestamps-client)")

    print(f"\nanchored run {run_id}. Commit the anchors/ directory promptly; "
          "git history and the external stamps corroborate each other.")


def cmd_verify():
    root = repo_root()
    anchors = root / "anchors"
    chain = anchors / "chain.jsonl"
    if not chain.exists():
        sys.exit("no chain.jsonl — nothing anchored yet")
    records = [json.loads(l) for l in chain.read_text().strip().splitlines()]
    ok = True

    # chain integrity
    prev = None
    for i, rec in enumerate(records):
        entry, claimed = rec["entry"], rec["entry_sha256"]
        actual = hashlib.sha256(canonical(entry)).hexdigest()
        if actual != claimed:
            print(f"FAIL entry {entry['id']}: hash mismatch"); ok = False
        if entry.get("prev_entry_sha256") != prev:
            print(f"FAIL entry {entry['id']}: broken chain link"); ok = False
        prev = claimed
        mf = anchors / entry["manifest_file"]
        if not mf.exists():
            print(f"FAIL entry {entry['id']}: manifest missing"); ok = False
        elif sha256_file(mf) != entry["manifest_sha256"]:
            print(f"FAIL entry {entry['id']}: manifest altered"); ok = False
    print(f"chain: {len(records)} entries, links and manifests "
          f"{'OK' if ok else 'FAILED'}")

    # working tree vs latest manifest (informational)
    latest = records[-1]["entry"]
    mf = anchors / latest["manifest_file"]
    changed = missing = 0
    for line in mf.read_text().splitlines():
        if line.startswith("#"):
            continue
        digest, rel = line.split("  ", 1)
        p = root / rel
        if not p.exists():
            missing += 1
        elif sha256_file(p) != digest:
            changed += 1
    print(f"working tree vs latest manifest ({latest['id']}): "
          f"{changed} changed, {missing} missing "
          f"(changes since the last run are normal; run `run` to anchor them)")

    # TSA tokens
    openssl = shutil.which("openssl")
    ts_ok = openssl and subprocess.run(
        [openssl, "ts", "-help"], capture_output=True).returncode in (0, 1)
    for rec in records:
        rid, esha = rec["entry"]["id"], rec["entry_sha256"]
        for name, _ in TSAS:
            tsr = anchors / "tsa" / f"{rid}-{name}.tsr"
            if not tsr.exists():
                print(f"tsa {rid}-{name}: no token"); continue
            if not ts_ok:
                print(f"tsa {rid}-{name}: present, not checked "
                      "(no `openssl ts` on this machine)"); continue
            certs = anchors / "tsa" / "certs"
            if name == "freetsa" and (certs / "freetsa-cacert.pem").exists():
                cmd = [openssl, "ts", "-verify", "-digest", esha, "-in",
                       str(tsr), "-CAfile", str(certs / "freetsa-cacert.pem")]
            else:
                cafile = "/etc/ssl/certs/ca-certificates.crt"
                if not os.path.exists(cafile):
                    cafile = "/etc/ssl/cert.pem"  # macOS
                cmd = [openssl, "ts", "-verify", "-digest", esha, "-in",
                       str(tsr), "-CAfile", cafile]
            r = subprocess.run(cmd, capture_output=True, text=True)
            if "Verification: OK" in (r.stdout + r.stderr):
                print(f"tsa {rid}-{name}: Verification OK")
            else:
                # fall back to a status check on the token itself
                r2 = subprocess.run(
                    [openssl, "ts", "-reply", "-in", str(tsr), "-text"],
                    capture_output=True, text=True)
                granted = "Granted" in r2.stdout
                imprint_hex = esha.upper()
                token_text = r2.stdout.upper().replace(" ", "").replace("\n", "")
                imprint_present = imprint_hex in token_text
                print(f"tsa {rid}-{name}: chain-of-trust verify failed "
                      f"({(r.stderr or '').strip().splitlines()[-1] if r.stderr else 'no detail'}); "
                      f"token status Granted={granted}, "
                      f"imprint matches entry hash={imprint_present}")
                if not (granted and imprint_present):
                    ok = False
    print("verify:", "PASS" if ok else "PROBLEMS FOUND")
    return 0 if ok else 1


def cmd_upgrade():
    ots = find_ots()
    if not ots:
        sys.exit("ots client not installed (pip install opentimestamps-client)")
    root = repo_root()
    proofs = sorted((root / "anchors" / "ots").glob("*.ots"))
    if not proofs:
        print("no OTS proofs to upgrade")
        return
    for p in proofs:
        r = subprocess.run([ots, "upgrade", str(p)],
                           capture_output=True, text=True)
        msg = (r.stdout + r.stderr).strip().replace("\n", " ")
        print(f"{p.name}: {msg or 'ok'}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    runp = sub.add_parser("run")
    runp.add_argument("--note", default=None)
    sub.add_parser("verify")
    sub.add_parser("upgrade")
    args = ap.parse_args()
    if args.cmd == "run":
        cmd_run(args.note)
    elif args.cmd == "verify":
        sys.exit(cmd_verify())
    elif args.cmd == "upgrade":
        cmd_upgrade()


if __name__ == "__main__":
    main()
