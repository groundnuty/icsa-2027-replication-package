# Verification

Three things are checked: that the files are the ones published, that the tables follow from the shipped results, and that the package is anonymous
and holds no secret.

## Files

`SHA256SUMS` holds the sha256 of every file; `make verify` (`reproduce/checksums.py`, standard library) recomputes them. `MANIFEST.json` lists every
file of the anonymising build with its sha256 and the purpose of the entry it belongs to.

## Tables

`make check` regenerates every analysis table of the fixed snapshot from `results/analysis/pipeline/` and `results/analysis/inputs/` and compares it
byte for byte with `results/analysis/tables/` (README, "Results only"). The analysis is deterministic: its bootstrap is seeded from the configuration.
`results/analysis/inputs/inputs.json` names the source of every input in the snapshot and its sha256, and the recount of the cohort is checked against
the totals the snapshot recorded.

## Code

The code was compared with the code that ran. `BUILD-REPORT.md`, "What ran, and how this tree differs", names the commit that ran for each part of
`icsa/`, lists the files that differ from it before anonymisation, and lists the files that the anonymisation rewrote: applying the same mapping to the
file that ran gives exactly the file shipped here. The fixed snapshot records the code it ran (`results/analysis/SNAPSHOT.json`, `snapshot_code`).

## Anonymity and secrets

The package was built from the study's repository by an anonymising build, and the finished archive was scanned again.

**What the build rewrites** (contents and file names, the same real value to the same label in every file):

| What | Becomes |
|---|---|
| names of people, institutions, accounts, hosts and users | `author_n`, `institution_n`, `handle_n`, `hostalias_n`, `user_n` |
| names of the platform's providers and sites | neutral site labels (`site-…`), or `provider_n` |
| IPv4 / IPv6 / other addresses | documentation addresses (RFC 5737), `ipv6-n`, `addr-n` |
| host names, URL hosts | `host-n.invalid` |
| e-mail addresses | `email-n@example` |
| home directories | `~` |
| repository owners in references | `source.invalid/owner_n` |
| platform file identifiers in logs, model API thinking signatures in transcripts | `guid-…`, `sig-…` (labels derived from the value alone) |

Never rewritten: `uv.lock` (its URLs are bound to hashes). The build fails if a rewrite changes a number in a data file, or if a `.py`, `.toml` or `.json`
file that parsed before no longer parses.

**What the scan checks** on every file, in plain text and in decoded views (escapes, percent and HTML coding, base64 and hex, UTF-16/32), and inside
containers (zip, tar, gzip, PDF, PNG text chunks, notebooks):
- any IP or MAC address other than the documentation addresses the build handed out; host names and URL hosts outside a short public allowlist;
  e-mail shapes; home paths; repository handles;
- the private list of the study's real names, institutions, accounts, host and user names and provider names, matched regardless of case, accents and
  separators (the list itself is not part of the package, and a file of its shape inside the package fails the build);
- secrets: token shapes (API keys, platform tokens, JWT, PEM blocks, `key = value` assignments, long high-entropy strings), and every file of the
  study's credential directories, by name and by the sha256 of its content.

**Rules that apply to trace files only** (`results/traces/`), each counted in the build report, each with test cases ("canaries") that must still fail
the build:
1. a JSON list is not read as one joined string by the entropy and address rules unless at least two of its elements look random (each element is still
   scanned alone);
2. an identifier made only of words, numbers, short identifiers and hex identifiers is not taken for a key;
3. six dashed groups of decimal digits (a timestamp) are not taken for a MAC address.

One more narrow rule: in files named `*.sha256`, on lines of exactly `<64 hex digits> <path>`, the path is not read by the entropy rule; names, hosts,
addresses and secrets are still checked there. Exact-match secret checks have no exception anywhere.

The scan prints counts per check, never a found value. Its result for this copy: every check passed.
