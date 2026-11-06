# Verification

Three things are checked: that the files are the ones published, that the tables follow from the shipped results, and that the package is anonymous
and holds no secret.

## Files

`checksums.sha256` holds the sha256 of every file; `make verify` (`reproduce/checksums.py`, standard library) recomputes them; `sha256sum -c checksums.sha256` does the same. `MANIFEST.json` lists every
file of the anonymising build with its sha256 and the purpose of the entry it belongs to.

## Tables

`make check` regenerates every analysis table of each result folder of the fixed snapshot from `results/analysis/<snapshot>/<folder>/pipeline/` and
`.../<folder>/inputs/` and compares it byte for byte with `.../<folder>/tables/` (README, "Results only"). The analysis is deterministic: its bootstrap is seeded from the configuration.
Each `.../<folder>/inputs/inputs.json` names the source of every input in the snapshot and its sha256; the recount of the cohort is checked against
the totals the snapshot recorded, and the K-augmentation against the counts the snapshot's K step logged. The tables' `manifest.json` is compared field by field: the fields that name the checkout and the Python
and library versions are reported, not compared, and an input hash is compared only when the shipped input still has that hash.

Six tables per result folder are shipped as regenerated from the anonymised inputs, not as the snapshot wrote them: `assignment_by_option`
(CSV and Markdown), `slot_shares` (CSV and Markdown), `backend_shares.md` and `mixed_fixed_effects.md`. They name run slots and model backends, and
the anonymisation replaced those names after the tables were made: the CSVs, sorted by name, came out in another row order, and in the Markdown
tables the anonymisation spells a label with a hyphen where the data files spell the same label with an underscore. Their rows and values are
unchanged. Run on the snapshot before anonymisation, `make check` gives all 123 files of each folder byte-identical, these six included.

## Code

The code was compared with the code that ran. `BUILD-REPORT.md`, "What ran, and how this tree differs", names the commit that ran for each part of
`icsa/`, lists the files that differ from it before anonymisation, and lists the files that the anonymisation rewrote: applying the same mapping to the
file that ran gives exactly the file shipped here. The fixed snapshot records the code it ran (`results/analysis/<snapshot>/<folder>/SNAPSHOT.json`, `snapshot_code`).

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

**Rules that relax the scan.** Each is counted by the scan, and each has test cases ("canaries") that must still fail the build. Token shapes and
the exact-match secret checks are never relaxed, and code (everything outside `results/`, `reports/` and `MANIFEST.json`) gets only rules 6 to 8.

In the trace sample (`results/traces/`):
1. the joined view of a JSON string list (its elements run together, to catch a token split over elements) is not read by the entropy and MAC rules
   unless at least two of its elements look random; each element is still scanned alone with every rule;
2. a dashed string of six pairs of decimal digits (a date and time) is not taken for a MAC address;
3. in the platform client's logs, the name right after `for new file ` is the name of a file the run created, not a key.

In the trace sample and in every file under `results/` and `reports/` and in `MANIFEST.json`:

4. an identifier made only of words, numbers, short identifiers and hex identifiers (a container name, a quoted path, an argument list) is not taken
   for a key;
5. a candidate with a `/` together with a `-` or `_`, and no `+`, cannot be base64 of either alphabet, so it is read as a path, not a key.

Anywhere:

6. in files named `*.sha256`, on lines of exactly `<64 hex digits> <path>`, the path is not read by the entropy rule;
7. a MAC candidate that mixes `:` and `-` (a time range such as `10:24:54-11:03:30`) is not a MAC;
8. an IPv6 candidate of at most six digits and colons next to a hyphen and a digit (`::-1`, a slice in code) is not an address (not counted).

Names, hosts, addresses and secrets are still checked on every line these rules touch.

The scan prints counts per check, never a found value. Its result for this copy: every check passed.
