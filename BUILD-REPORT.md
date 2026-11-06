# Anonymised artifact: Where Should the Agent Meet the Data?

Code, protocol texts, instance definitions, reports and results of the study, anonymised for double-blind review.
Provider and service names are replaced by neutral labels; the table that maps them is not part of the artifact.
Source commit: `6fc798cf6ef1` (history not included). Files with names changed: 264.

## What is included

| Path | Purpose |
|---|---|
| `pyproject.toml` | Python project definition and dependency list |
| `uv.lock` | Locked dependency versions |
| `icsa/__init__.py` | Package marker |
| `icsa/grid.py` | The SST grid and day axis shared by every module |
| `icsa/extent.py` | Extents in day x cell units; baseline and target kept apart |
| `icsa/records.py` | Options, layouts, instances, the run record and the scored row |
| `icsa/paths.py` | Locations of data and run outputs |
| `icsa/ncio.py` | NetCDF reading helpers |
| `icsa/harness` | Agent harness and scheduler: runs an agent in a sandbox under one access option |
| `icsa/campaign` | Campaign store, run blocks, scheduling and export of run state |
| `icsa/sandbox` | Sandbox that enforces the data paths and the network policy |
| `icsa/knowledge` | Knowledge plane: tool definitions and equality check across options |
| `icsa/ingest` | Ingest scripts: download, S1 and S2 layouts, checksums, extent description, upload |
| `icsa/instances` | Instance generator |
| `icsa/refdet` | Reference marine-heatwave detector |
| `icsa/scoring` | Scoring of run records against the reference |
| `icsa/faults` | Fault injection for the platform-record calibration |
| `icsa/dossier` | Dossier of the study's design decisions |
| `icsa/analysis` | Pre-registered analysis pipeline and exhibits |
| `icsa/instruments` | Read- and analysed-extent instruments and omission labeller (the measuring instruments) |
| `icsa/calibration` | Fault-injection calibration of the read record |
| `icsa/pipeline` | Scripted pipeline and concurrency curve |
| `sandbox/Dockerfile` | Sandbox image definition (base image pinned by digest) |
| `sandbox/INTERFACE.md` | Interface specification of the sandbox |
| `sandbox/README.md` | Sandbox overview |
| `sandbox/requirements.txt` | Pinned requirements of the sandbox image |
| `sandbox/hooks` | Instrumentation hooks inside the sandbox |
| `tools/octave` | Octave side of the reference-detector equivalence check |
| `docs/harness.md` | Harness description |
| `protocol` | Task prompt, per-option access texts, frozen parameters and report specification |
| `data/instances` | Instance definitions (boxes, periods, instance table) |
| `data/manifest` | Checksums of the dataset files |
| `data/extent_s1.json` | Extent description of layout S1 |
| `data/extent_s2.json` | Extent description of layout S2 |
| `reports/refdet` | Reference-detector validation: diagnosis, equivalence checks and diagnostics |
| `octave_domain` | Whole-domain Octave reference validation: pre-registration, packing and shard runner code, verifier |
| `reports/octave_domain` | Whole-domain Octave reference validation: shard logs, step outputs and checksums |
| `results/knowledge` | Knowledge-plane equality results per layout |
| `snapshot` | Fixed-snapshot pipeline: cut, fetch, pull, analyse; layout read and coder replay |
| `docs/snapshot-interim` | Stage scripts of the interim and fixed snapshots (freeze, merge, H3 measure, fidelity inputs, reports) |
| `hpc_sandbox/README.md` | HPC sandbox overview |
| `hpc_sandbox/hpcsbx` | HPC sandbox executor: runs an agent under one access option without a container daemon |
| `hpc_sandbox/override` | HPC sandbox overrides of the harness |
| `hpc_sandbox/portmap` | Port mapping helper of the HPC sandbox |
| `hpc_sandbox/bin` | Command shims of the HPC sandbox |
| `hpc_sandbox/pool_launcher.py` | Launcher of the HPC sandbox pool |
| `hpc_sandbox/build_images.py` | Image build for the HPC sandbox |
| `hpc_sandbox/ociunpack.py` | Image unpacking for the HPC sandbox |
| `config/harness.toml` | Harness configuration of the campaign |
| `config/models.toml` | Model configuration of the campaign |
| `icsa/causes` | Cause coding of omitting runs |
| `icsa/inspection` | Blind code inspection: packets, decisions, agreement |
| `icsa/scripted` | Scripted pipeline controls |
| `icsa/codestamp.py` | Code stamp of a run |
| `icsa/cutrequest.py` | Cut request of the snapshot |
| `icsa/frprobe.py` | Data-provider probe |
| `icsa/frsettings.py` | Data-provider settings record |
| `icsa/opwrestart.py` | Provider restart helper |
| `icsa/servedsettings.py` | Served-settings record |
| `tools/mplus` | M+ driver and its plans |
| `octave_domain` | Octave side of the reference-domain criterion: shards, shard-invariance check, criterion and packing scripts |
| `evidence` | Evidence logs of the knowledge plane and the slot seam |
| `README.md` | Repository overview |
| `results/traces` | All run traces (by manifest with sha256) |
| `results/analysis` | Analysis outputs: tables, figures and manifest |
| `results/validation/9-instruments` | Instrument validation: the measuring instruments checked against known answers (this is the validation of the instruments, not an audit of the runs) |
| `results/faults-live` | Fault-injection calibration of the platform's record per option: live runs |
| `results/faults-batch` | Fault-injection calibration of the platform's record per option: batch rescoring |
| `results/coding` | Coding data: the blind inspection (known-answer scores, pair agreement, the numeric replay) and the second coder's packets, from the final snapshot |
| `results/reference-validation` | Reference validation results |

`MANIFEST.json` lists every file with its sha256 and the purpose of the entry it belongs to.

## Work that was not done as designed

The instrument audit of the registered design (a stratified sample read blind, with error rates per instrument) was not run as designed, and no file in this artifact is its result. Its role is filled by the blind inspection: known-answer scores, pair agreement and the numeric replay, shipped as coding data under `results/coding/` and labelled as such. The files under `results/validation/9-instruments` are the validation of the instruments against known answers, not that audit.
## Cut to fit the size limit

The trace sample was cut from the END of its seeded order to keep the tree under 2048 MiB: 413 of the 490 chosen runs stayed (every option x layout x model cell keeps its first 8 to 9 runs). Nothing else was cut.

## Not yet present

These entries exist in the build but had no files in the source commit, so this artifact does not hold them yet
(`MISSING.md` repeats the list):

| Path | Purpose |
|---|---|
| `results/runs` | Run records and scored rows |
| `results/pilot` | Pilot runs and the power re-estimate |
| `notebooks` | Analysis notebooks |

## Left out on purpose

| Path | Reason |
|---|---|
| `tests` | Test suites: their fixtures carry addresses and host names; not in the paper's artifact list |
| `reports/applicability, reports/budget, reports/prompt-cache-measurement` | Working reports, not in the paper's artifact list |
| `day0` | Day-0 platform measurements; not in the paper's artifact list, and full of host and provider detail |
| `bench` | Throughput benchmarks and spend logs, not part of the study |
| `config/protocol-draft` | Superseded draft copy of protocol/ |
| `tools/diag, tools/artifact` | Developer diagnostics and the artifact build itself |
| `data/*.jsonl, data/DOWNLOAD.md, data/UPLOAD.md` | Operational download and upload logs |
| `hpc_sandbox deployment and fleet operations (deploy, bootstrap, caps allocator, rolling restart, node setup, smoke tests, assignment and image records)` | Host-, account- and queue-specific operations of the HPC fleet; the executor itself is included |
| `docs/snapshot-interim fleet loops (provider add, mirrors, fills, restarts, replica, listings)` | Operational loops of the run fleet; the stage scripts that make the tables are included |
| `config/slot_map.json, config/campaign_hosts.example.*, config/provider-watch.example.json` | Host and slot identifiers of the run fleet |
| `tools/b_launch, tools/provider_watch, tools/provider_mon*, tools/newhost, tools/host_split.py` | Fleet operation tools, not needed to regenerate any exhibit |
| `data/instances/sea_masks.npz, *.nc` | Third-party-derived data: scripts only until the terms are confirmed |
| `k76-stub (7.6 GB)` | The known-answer stub, too large for the draft; the run outputs it was made from are included under results/coding/k/k76-runs |
| `reports/octave_domain/step3/events_mean_series.f64` | A 122 KB raw float64 series of the whole-domain Octave run, a numeric binary like the other binary data files; its sha256 stays in reports/octave_domain/step3/outputs.sha256 and the whole-domain result is in results/reference-validation/octave-domain/domain.json |

## Left out by size

Files at or over 95 MB cannot be pushed to the hosting branch, and the tree must stay under 2 GiB. These were left out (0):

- none

## What ran, and how this tree differs

The code under the paths below was compared with the commits that ran: `icsa/analysis` at `09ecc2c0`, `icsa/campaign` at `d867010d`, `icsa/faults` at `d867010d`, `icsa/harness` at `09ecc2c0`, `icsa/instances` at `09ecc2c0`, `icsa/instruments` at `09ecc2c0`, `icsa/knowledge` at `09ecc2c0`, `icsa/pipeline` at `09ecc2c0`, `icsa/refdet` at `09ecc2c0`, `icsa/sandbox` at `09ecc2c0`, `icsa/scoring` at `09ecc2c0`. 200 files compared.

Files that differ from what ran (before the mapping), 2:

- `icsa/faults/mainaudit/provider.py`
- `icsa/faults/records/audit.py`

Files the mapping rewrote (names and private terms replaced; applying the mapping to the file that ran gives exactly the file shipped here), 64:

- `icsa/analysis/exhibits.py`
- `icsa/campaign/boverride.py`
- `icsa/campaign/budget.py`
- `icsa/campaign/cli.py`
- `icsa/campaign/config.py`
- `icsa/campaign/credlife.py`
- `icsa/campaign/endpoint_caps.py`
- `icsa/campaign/endpoints.py`
- `icsa/campaign/hosts.py`
- `icsa/campaign/livecheck.py`
- `icsa/campaign/operator_queue.py`
- `icsa/campaign/opwcmd.py`
- `icsa/campaign/progress.py`
- `icsa/campaign/remote.py`
- `icsa/campaign/scheduler.py`
- `icsa/campaign/slot_equality.py`
- `icsa/faults/README.md`
- `icsa/faults/calibrate.py`
- `icsa/faults/fidelity.py`
- `icsa/faults/ledger.py`
- `icsa/faults/mainaudit/__init__.py`
- `icsa/faults/mainaudit/__main__.py`
- `icsa/faults/mainaudit/attribute.py`
- `icsa/faults/mainaudit/ledger.py`
- `icsa/faults/mainaudit/pull.py`
- `icsa/faults/mainaudit/record.py`
- `icsa/faults/mainaudit/remote.py`
- `icsa/faults/mainaudit/solo.py`
- `icsa/faults/mainaudit/watch.py`
- `icsa/faults/mainaudit/windows.py`
- `icsa/faults/records/traefik.py`
- `icsa/harness/adapters.py`
- `icsa/harness/config.py`
- `icsa/harness/health.py`
- `icsa/harness/knowledge.py`
- `icsa/harness/loop.py`
- `icsa/harness/real_sandbox.py`
- `icsa/harness/roundtrip.py`
- `icsa/harness/run.py`
- `icsa/harness/runner.py`
- `icsa/harness/slot_lease.py`
- `icsa/harness/slot_users.py`
- `icsa/harness/slots.py`
- `icsa/instances/run.py`
- `icsa/instruments/DESIGN.md`
- `icsa/instruments/analyse.py`
- `icsa/instruments/confirm.py`
- `icsa/instruments/fullindex.py`
- `icsa/instruments/hooks.py`
- `icsa/instruments/sim/httpserve.py`
- `icsa/knowledge/launch.py`
- `icsa/knowledge/live_equality.py`
- `icsa/knowledge/pin.py`
- `icsa/knowledge/writer.py`
- `icsa/sandbox/config.py`
- `icsa/sandbox/earlyoom.py`
- `icsa/sandbox/forwarder.py`
- `icsa/sandbox/gate.py`
- `icsa/sandbox/mock_onedata.py`
- `icsa/sandbox/netpool.py`
- `icsa/sandbox/reap.py`
- `icsa/sandbox/route.py`
- `icsa/sandbox/sandbox.py`
- `icsa/scoring/scorer.py`


## Notes on included files

- `reports/refdet/diag/box_domains.md`: **Superseded.** This diagnostic describes the box set used before the eligibility redraw (the old boxes: its first instance has 3,344 sea
Departures from the registered design are recorded as amendment rows of the study's registry; this README does not restate them. `protocol/AMENDMENTS.md` in this artifact holds the rows up to 44.

Third-party data (Copernicus Marine files and files derived from them) is not redistributed; see `ATTRIBUTION.md`.

## The primary results

The primary tables of this draft are the ones named by the file below.

The file `PRIMARY.json` of the result set `final-20261106T0900Z` (under `results/analysis/`) reads, exactly:

```json
{
 "format": "icsa-snapshot-primary-v1",
 "frozen_beside": {
  "coded_tables": "out-coded",
  "tables": "out"
 },
 "k_augmented": {
  "capped_runs_applied": 6,
  "capped_runs_by_option": {
   "D": 1,
   "M": 5
  },
  "coded_computed": true,
  "computed": true,
  "correction_file_sha256": "3b75f137d2a6e3bb78c9f5b19289965470ba7ec3d6a289427309afbe27eb8584",
  "held_aside_earlier_done_copy": 2,
  "runs_applying_by_rule": 6,
  "table_note": "**K-aug:** the frozen tables, with these runs counted as time-capped by count only, without measures. **6 runs** whose earliest analysable attempt ran past the 8.17 h cap and was marked an infrastructure failure by the dispatcher, as its record couldn't be read; under the registered definition a cap is never an infrastructure failure. They were selected by that rule before the final's tables were read, and their later attempts are held aside as duplicates. The tables in `out/` and `out-coded/` leave them out, and a sensitivity counts their retries instead.",
  "unscorable_file_sha256": null,
  "unscorable_memory_runs": 0
 },
 "primary_coded_tables": "out-coded-kaug",
 "primary_tables": "out-kaug",
 "sensitivities": {
  "out-050": {
   "complete_in_sens_seal": false,
   "complete_in_this_seal": false,
   "dir_in_sens_seal": null,
   "note": "computed on the frozen basis, with the capped correction and without K-aug, at the default 00:50Z cut: compare with `out/` and `out-coded/`, not with the primary `out-kaug/`"
  },
  "out-lab504": {
   "complete_in_sens_seal": false,
   "complete_in_this_seal": false,
   "dir_in_sens_seal": null,
   "note": "computed on the frozen basis, with the capped correction and without K-aug, the flagged Lab-504 runs left out: compare with `out/` and `out-coded/`, not with the primary `out-kaug/`"
  },
  "out-retries": {
   "complete_in_sens_seal": false,
   "complete_in_this_seal": false,
   "dir_in_sens_seal": "final-20261106T0900Z-sens/out-retries",
   "note": "computed on the frozen basis WITHOUT the capped correction (the retries count in place of the capped attempts) and without K-aug: compare with `out/` and `out-coded/`, not with the primary `out-kaug/`"
  }
 },
 "side_tables": {
  "fidelity-extra": true
 },
 "why": "science #34 03:30Z (option B by Route D): out-kaug/ is the primary, out/ is the frozen analysis beside it"
}
```

Beside each, every result directory (`out`, `out-coded`, `out-kaug`, `out-coded-kaug`, and any sensitivity directory present) holds its `tables/`, the per-run rows, causes, flags and counts of `pipeline/`, and its `SNAPSHOT.json`; a K-aug directory has a `NOTE-K-AUG.txt` that says how the capped runs are counted.

## Which results are final

- **The final results are in the seal `final-20261106T0900Z`**, the state at the registered final time; the sensitivities were run on it afterwards.
- **Within a seal, the primary tables are `out-kaug/` and `out-coded-kaug/`.** They are the registered pipeline's tables with five time-capped runs counted as time-capped, as the registered definition of an infrastructure failure requires. `out/` and `out-coded/` are the frozen pipeline's output without that correction, kept beside them.
- **Side tables marked "added after seeing the data"** (under `side-added-after-data/`) and the sensitivities (the 00:50Z cohort cut, retries in place of the capped runs, runs retried after a gateway timeout) are not registered analyses.

## Protocol and departures

The registered protocol is in `protocol/`. Every change is a dated row in `protocol/AMENDMENTS.md`, made before the data it governs unless the row says otherwise. Row 43 sets the final snapshot; **row 44 lists every departure during the final night**, added after the final.

## Data

The data are not included; the ingest scripts rebuild them. Source: the Copernicus Marine Service product SST_BAL_SST_L4_REP_OBSERVATIONS_010_016, https://doi.org/10.48670/moi-00156. Generated using E.U. Copernicus Marine Service Information; https://doi.org/10.48670/moi-00156.

## What the checks let through

The scans that keep names, hosts, addresses, secrets and key-like strings out of this artifact are strict everywhere. A few narrow rules, each counted, let through strings that look like keys and are not:
(1) a long mixed-case string made only of words, numbers, short ids and model sizes (a container name, a quoted path, an argument list) is not read as a key, in the trace sample, `results/`, `reports/` and `MANIFEST.json`;
(2) the elements of a JSON string list are also read run together, to catch a token split over elements, and that joined reading is skipped when fewer than two elements look random (each element is still scanned alone), in the trace sample;
(3) a dashed string of six decimal pairs (a date and time) is not a MAC address, in the trace sample;
(4) a string with a `/` and a `-` or `_` cannot be base64 of either alphabet, so it is a path, in the trace sample, `results/`, `reports/` and `MANIFEST.json`;
(5) the name of a file the run created, directly after the words `for new file` in an oneclient log, in the trace sample;
(6) a MAC-like string that mixes `:` and `-` is a time range, anywhere; (7) the path column of the lines of a `*.sha256` file is not read as a key.
Exact-match checks for secret files, the token shapes (GitHub, Anthropic, Onedata, JWT, PEM, key=value) and every other rule are unchanged, long Onedata access tokens in the data are replaced by labels, and every build plants known cases at these paths and stops if one does not behave as planned.
What these rules let through in this draft, counted by the scan that preceded this text: word-like identifiers: 4,357 lines; joined lists with fewer than two random elements: 145 lists; six decimal pairs: 4 lines; path shapes: 362 lines; names of files created in the mount: 1 lines; time ranges with mixed separators: 1 lines; path columns of sha256 lists: 0 lines.

## Reproduce

See `README.md`, "Quick start" and "Results only".

