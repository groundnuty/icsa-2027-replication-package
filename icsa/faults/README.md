# icsa.faults: fault-injection calibration of the platform record (#11, harness only)

No live calibration run exists yet. What is here, and what each piece may and may not see:

| module | role |
|---|---|
| `scenarios.py` | fault catalogue; the injected omission is a pure function of the scenario parameters + the required set. Imports no record/parser/detector (tested). Paired draws across option x layout |
| `observability.py`, `OBSERVABILITY.md` | per fault x layout x option x record x condition: observable / unobservable_by_design / n/a / unknown_until_live, written by hand BEFORE any run |
| `records/` | pluggable parsers to one `AccessEvent`: `audit` (op_worker 25.0's real line format, checked on site-g), `traefik` (v3.5.3 JSON, path + Range + run key), `perf` (oneclient CSV); each raises `RecordFormatError` above 2 unparsable lines |
| `calibrate.py` | the calibration runner: `plan` (seal + claim once), `run` (one sandbox per run, lease + run key required, resumable, pause file), `pull` (our lines via dsk.sh, filtered at source), `score` (by slot user, run key, own perf CSV; rows for fidelity and #14) |
| `live_check.py` | the live check before calibration: one S1 file read by T, D and M through the real sandbox as leased slot users; evidence in `results/faults-live/` |
| `matcher.py` | run-to-record attribution; overlaps are *ambiguous* and the run is excluded; perf CSV located by sidecar identity |
| `DETECTOR.md`, `detector.py` | frozen spec, **version 2** (amendment 12): byte records credit a day only when the union of served bytes covers its whole chunk; `detect(events, required, manifest, spec)` only; output carries a spec+source fingerprint |
| `masking.py` | per-run masking verdicts for the `observable_per_instance` cells (T's read-ahead), from the scenario and static metadata only, sealed into the claimed plan before any run; `python -m icsa.faults.masking` regenerates the model's numbers |
| `units.py` | `Required`, static `Manifest` (day -> file, data byte span; built from the HDF5 chunk index) |
| `script.py` | executes a read plan against a `ByteReader` (T/M ranges, D downloads); live readers come with #7 |
| `matrix.py` | the calibration matrix (>= 60 faulted, 30 controls per option x layout x condition), seeded interleaved order; `calibration_plan(..., required=, manifests=)` seals the masking verdicts |
| `ledger.py` | the matrix runs once: `matrix.calibration_plan` claims it (id + sha) in a ledger; a re-run, extension or re-draw is refused, and every result carries the id and sha. A failed run is an infrastructure failure, not an added run: it gets a replacement from the same row and seed, at most 3 attempts, before any cell is scored; one that fails them all stays lost and leaves its cell incomplete |
| `fidelity.py` | scoring (run level: a non-served omitted day flagged; unit level over non-served omitted days; both masked shares beside every recall, enforced by `check_shares`), Wilson / cluster-bootstrap tables, record-content table, rows for #14's adapter; `h3_table` applies the decision rule (pass / fail / not_testable) |

Record definitions are final: each option is calibrated against the audit log and against its switched-on record. Live calibration waits for: the audit log switched on at site-g (operator), the #3 data on site-g, the Traefik access log / oneclient `--log-read-write-perf` switched on (operator), #7 sandbox + readers, #5 instances (required sets).
