# Anonymised artifact: Where Should the Agent Meet the Data?

Code, protocol texts, instance definitions, reports and results of the study, anonymised for double-blind review.
Provider and service names are replaced by neutral labels; the table that maps them is not part of the artifact.
Source commit: `bbd0ba6330c2` (history not included). Files with names changed: 229.

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
| `icsa/instruments` | Read- and analysed-extent instruments and omission labeller (instrument audit) |
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

`MANIFEST.json` lists every file with its sha256 and the purpose of the entry it belongs to.

## Not yet present

These entries exist in the build but had no files in the source commit, so this artifact does not hold them yet
(`MISSING.md` repeats the list):

| Path | Purpose |
|---|---|
| `results/traces` | All run traces (by manifest with sha256) |
| `results/runs` | Run records and scored rows |
| `results/analysis` | Analysis outputs: tables, figures and manifest |
| `results/instrument-audit` | Instrument audit |
| `results/calibration` | Fault-injection calibration and read-record calibration |
| `results/coding` | Coding data for the cause analysis |
| `results/reference-validation` | Reference validation results |
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
| `reports/octave_domain/step3/events_mean_series.f64` | A 122 KB raw float64 series of the whole-domain Octave run, a numeric binary like the other binary data files; its sha256 stays in reports/octave_domain/step3/outputs.sha256 and the whole-domain result is in results/reference-validation/octave-domain/domain.json |

## Left out by size

Files at or over 99 MB cannot be pushed to the hosting branch, and the tree must stay under 2 GiB. These were left out (0):

- none

## What ran, and how this tree differs

The code under the paths below was compared with the commits that ran: `icsa/analysis` at `09ecc2c0`, `icsa/campaign` at `d867010d`, `icsa/faults` at `d867010d`, `icsa/harness` at `09ecc2c0`, `icsa/instances` at `09ecc2c0`, `icsa/instruments` at `09ecc2c0`, `icsa/knowledge` at `09ecc2c0`, `icsa/pipeline` at `09ecc2c0`, `icsa/refdet` at `09ecc2c0`, `icsa/sandbox` at `09ecc2c0`, `icsa/scoring` at `09ecc2c0`. 200 files compared.

Files that differ from what ran (before the mapping), 2:

- `icsa/faults/mainaudit/provider.py`
- `icsa/faults/records/audit.py`

Files the mapping rewrote (names and private terms replaced; applying the mapping to the file that ran gives exactly the file shipped here), 66:

- `icsa/analysis/README.md`
- `icsa/analysis/exhibits.py`
- `icsa/analysis/secondary.py`
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
`protocol/AMENDMENTS.md` stops at row 43. A final row of departures (amendment 44) is kept on the study's registry and is not in this draft.

Third-party data (Copernicus Marine files and files derived from them) is not redistributed; see `ATTRIBUTION.md`.

## Reproduce

Set up (Python 3.12 or newer, `uv`): `uv sync`.

| Exhibit | Command | Needs |
|---|---|---|
| Knowledge-plane equality table | `python reproduce/equality_table.py results/knowledge > equality_table.md` | included `results/knowledge/*.json` |
| Contrast tables, bounds, figures | `uv run python -m icsa.analysis.run --rows results/runs/scored_rows.jsonl --infra results/runs/infra.json --causes results/runs/causes.csv --cause-flags results/runs/cause_flags.csv --overhead results/analysis/overhead.json --fidelity-rows results/calibration/adapter_rows.jsonl --h3-table results/calibration/h3_table.csv --inspection-labels results/coding/labels.jsonl --inspection-coverage results/coding/coverage.jsonl --out analysis_out` | the files named, present after the campaign (an input the study did not measure is an empty file, as `icsa/analysis/run.py --help` says) |
| Primary tables of the fixed snapshot | `python -m snapshot --help`, then `snapshot/README.md` | the campaign's store copy; the stage scripts that made the tables are in `docs/snapshot-interim/` |

The anonymity of this archive was checked by `tools/artifact/build.py` on the finished archive, not on its input.
