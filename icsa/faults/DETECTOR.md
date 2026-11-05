# Detector specification (version 2) -- FROZEN before any calibration run

Status: written 1 Nov 2026 before any scripted run exists. Changing anything below after a
calibration run has been scored is tuning on the evaluation runs, which issue #11 forbids: if a
change is unavoidable, bump the version, re-run the whole calibration, and report both.

## Inputs (the only inputs)
1. The **record events** of one run (parsed from one record: audit log, Traefik access log, or
   oneclient perf CSV), already attributed to the run by `matcher.py`.
2. The instance's **required set** of days (baseline and target).
3. The **manifest**: static dataset metadata mapping days to files and to the byte span holding each
   day's data (from the HDF5 chunk index), and file paths / REST IDs to files.

The function signature is `detect(events, required, manifest, spec)`. It takes no scenario, no
injected set and no label. Output: which required days it judges NOT read.

## Rule per record
A required day is judged **read** iff:

- **audit** (file level): its file has at least one event of kind `open` or `read` (request types
  `open_file*` or `proxyio_request::remote_read`). Attribute, location, release and listing requests
  do not count (a directory listing touches every file's attributes). In S2 the single file is read
  or not as a whole, so every required day is judged read if the file was opened, else none is.
  Choice: opens count as reads because the log offers nothing finer and a cache-served read may
  leave an open without a read; a file opened and never read is therefore a miss.
- **traefik** (byte level): the UNION of the bytes served by successful content GETs
  (`/data/<id>/content`, status 200 or 206) covers ALL stored bytes of the day's chunk (its data span:
  the decoding unit, the same rule as #9's layout index). Served bytes:
  200 = the whole file (cut to the body size if short); 206 = the Range span (cut to the body size if
  short). A multi-range 206, a 206 with no usable Range header and any response with no logged body size
  are unresolvable and counted (`n_unresolved`), never credited: a multipart body cannot be mapped to its
  ranges from an access log (science, #2, 2 Nov). The scorer reads a run with any unresolved response as
  not observed. Listing requests and other methods do not count. A request for the
  header only (bytes below the first data byte) therefore does not count as reading the data.
- **perf** (byte level): the UNION of the `FsLogic,read` rows' [offset, offset+size) covers ALL stored
  bytes of the day's chunk. `ReadCache,prefetch` rows and `ReadCache,read` rows are ignored: prefetch is
  data the client fetched ahead, not data the agent read.

`missing = required - read`. Events whose target is not in the manifest are counted
(`n_unmapped`), never an error and never credited.

## Records calibrated (final)
Each option is calibrated against two records: the default one (the audit log, file level) and the
switched-on one (Traefik access log keeping the Range header, for T and D; oneclient
`--log-read-write-perf`, for M). This detector fixes the rule per record.
- Thresholds: none. Whole-chunk coverage is structural (a compressed chunk cannot be decoded from part
  of it), not a tuned value.

## Version 2 (1 Nov 2026, science's amendment 12, #11), before any calibration run

Version 1 credited a day when served bytes overlapped its chunk by at least 1 byte. The live check
(`results/faults-live/`, 1 Nov 21:20-22:07Z) showed what a client asks for beyond its application:
oneclient keeps the application's offset and rounds the size up to whole 4 KiB pages (a 15,241 B header
read reached [0,16384), 1,143 B into the chunk; a chunk read reached 2,100 B into the next one), and T's
fsspec client reads 5 MiB past every request. Under v1, page rounding alone would credit header-only reads
and skipped neighbours. Version 2 credits a day only when its whole chunk was served, which no page rounding
can fake; what a client's read-ahead serves whole is decided per scripted run BEFORE it runs
(`masking.py`, `OBSERVABILITY.md`). No calibration run had been scored under version 1.

## Fingerprint
Every output carries a SHA-256 over: this file, the spec parameters, and the source of
`detector.py`, `units.py` and `records/*.py`. Calibration results are only comparable between
outputs with the same fingerprint.
