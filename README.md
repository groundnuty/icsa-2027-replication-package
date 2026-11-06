# Replication package: Where Should the Agent Meet the Data?

Replication package for the paper *Where Should the Agent Meet the Data?*, submitted for double-blind review.
The authors' names, institutions, accounts and host names are removed or replaced by neutral labels throughout; `VERIFICATION.md` says how this was checked.

This repository holds the code of the study, the protocol texts as registered, the instance definitions, the results of the fixed snapshot that the
paper's numbers come from, the coding data of the blind inspection, a sample of whole run traces, and one command that checks the files and regenerates
every analysis table from the shipped results.

## Quick start

```bash
uv sync       # Python 3.12 or newer; installs the locked dependencies from uv.lock
make check    # verify checksums.sha256, regenerate every analysis table, compare each with the shipped file
```

The last line reads `check: all 4 result folders passed`. It takes about 15 minutes on a multi-core machine (about 40 CPU-minutes, under 6 GB of memory) and needs no network after `uv sync`, no campaign store, no model and no
data platform. `make verify` alone checks the files against `checksums.sha256` with the Python standard library.

The study gives LLM agents one data-analysis task (detecting marine heatwaves in a region of sea-surface-temperature data) and changes only where the
agent meets the data, on a research-data platform:

| Option | How the agent reaches the data |
|---|---|
| **T** | file objects read remotely through the platform's REST interface (an fsspec filesystem) |
| **T, complete listing** | as T, with a listing that follows the platform's continuation token; the prompt is byte-identical to T's |
| **D** | whole files downloaded to the sandbox's local disk through the same filesystem |
| **M** | the platform mounted read-only in the sandbox; files opened as local files |
| **M+** | as M, with the data first replicated to the agent's own site; measured separately, against a cold mount |

Everything else is held equal: the prompt (one slot differs by option, `protocol/task-prompt.md` and `protocol/access/`), the instance, the model and
its settings, the caps and the sandbox. Two data layouts are used: **S1**, one file per day, and **S2**, one chunked file. Each run's record holds what
the agent read and what it analysed, measured by instruments outside the agent, and what it reported; `protocol/report-spec.md` defines the report.

There are three ways to use this package:

| Path | What it shows | Needs | Time |
|---|---|---|---|
| **Results only** | every analysis table, regenerated from the shipped scored rows and compared byte for byte | Python 3.12+, `uv`; no network after `uv sync` | minutes |
| **Read the evidence** | the run traces, the coders' decisions and the instruments' validation behind each scored row | a text editor; `jq` helps | as long as you like |
| **New run** | new runs of the agents on your own platform deployment, models and data | a Onedata deployment, model endpoints, the sandbox image, the Copernicus data | hours; see below |

## Repository map

| Path | Contents |
|---|---|
| `README.md`, `VERIFICATION.md`, `ENVIRONMENT.md` | This overview; how the files and the anonymity were checked; the software and hardware the study ran on |
| `Makefile`, `reproduce/` | `make check` and its scripts: `regenerate.py` (the analysis tables), `checksums.py` (`checksums.sha256`), `equality_table.py` |
| `checksums.sha256` | The sha256 of every file in this package |
| `BUILD-REPORT.md`, `MANIFEST.json` | What the anonymising build included and left out, why, and which files it rewrote; every file with its sha256 and purpose |
| `MISSING.md` | What this copy of the package does not hold, and why |
| `protocol/` | The registered protocol texts: the task prompt, the per-option access texts, the frozen parameters, the report specification, the inspection rubric, and every dated amendment (`AMENDMENTS.md`) |
| `data/` | Instance definitions (regions, periods, the instance table), the dataset's checksums and the extent descriptions of S1 and S2 |
| `icsa/` | The study's code: harness, sandbox, campaign scheduler and store, instruments, scoring, fault injection, inspection, cause coding, analysis |
| `snapshot/`, `docs/snapshot-interim/` | The fixed-snapshot tool (cut, merge, analyse, header stamp, cohort recount) and the stage scripts that made the tables |
| `sandbox/`, `hpc_sandbox/` | The agent sandbox (container image definition, hooks, interface) and the executor that ran the same sandbox on HPC nodes without a container daemon |
| `tools/mplus/`, `tools/octave/`, `octave_domain/` | The M+ driver and its plans; the reference detector's equivalence check under GNU Octave, for six blocks and for the whole domain |
| `config/` | The campaign's harness and model configuration |
| `reports/` | The reference detector's validation reports, and the whole-domain Octave run's logs and checksums |
| `RESULTS.md`, `scripts/` | The final results, organised by what the paper reports: each value, the file that holds it, and how to reproduce it; the scripts it calls |
| `results/` | The results of the fixed snapshot, the coding data, the trace sample and the validation and calibration results; `results/README.md` maps each path |
| `evidence/` | Evidence logs of the knowledge plane and the sandbox's slot seam |

## Results only

`make check` runs three steps:

1. `reproduce/checksums.py` verifies every file against `checksums.sha256`.
2. `reproduce/regenerate.py` regenerates each result folder of the fixed snapshot, `results/analysis/<snapshot>/<folder>/`: `out` (the frozen run) and
   `out-coded` (with the coders' inspection labels), and `out-kaug` and `out-coded-kaug`, the same two with the runs that reached the time cap counted
   as K (`PRIMARY.json` names which tables are the primary ones). For each it reads `pipeline/` (one scored row per analysed run, the coded causes,
   the cause flags, the infrastructure export) and `inputs/` (the counted start of each run, the enforcement overhead, the fault-injection fidelity
   rows and H3 table, the coders' inspection labels and coverage, and for a K-augmented folder the capped runs). It then repeats what the snapshot
   tool did after scoring: it recounts the cohort against the snapshot's cut, calls the pre-registered analysis (`icsa.analysis.run.run_all`) with
   the default configuration (for a K-augmented folder with the capped runs added as K rows, as the snapshot's K-augmentation step did; the
   docstring of `regenerate.py` describes it), and stamps each table with the snapshot's header line. The recount and the K-augmentation are each
   checked against the counts the snapshot recorded.
3. It compares every regenerated file with the shipped one under `<folder>/tables/`. Tables must be byte-identical. The manifest is compared field by
   field: the fields that name the checkout and the Python and library versions are reported, not compared, and so is a hash of an input that the
   anonymisation rewrote after the analysis read it. A figure whose bytes differ is reported, not failed, because PNG bytes depend on the plotting
   library's build. The last line reads `check: all N result folders passed`. A folder that ships no `inputs/` (a sensitivity analysis) is listed
   as shipped, not regenerated; a folder that `PRIMARY.json` names must be regenerated.

The scored rows themselves come from the run directories through the scoring pipeline (`icsa/pipeline`, `icsa/scoring`, `snapshot/run.py`); the run
directories are not shipped whole (see below), so this step is checked on the sampled traces, not regenerated.

## Read the evidence

- `results/traces/`: 413 whole runs, eight or nine per option × layout × model (ten were chosen per cell; `MISSING.md` says how the sample was cut to fit), chosen by a seeded order of the run keys alone, from the runs that had ended. Each
  archive holds the run's whole directory (every attempt): the agent's transcript, the code it ran, the instruments' records and the run record; the
  raw read-performance logs are replaced by a per-run summary. Model API signatures, platform file identifiers and host names are replaced by labels;
  `VERIFICATION.md` lists every rule. The run's scored row is the line with its key in `results/analysis/<snapshot>/out/pipeline/scored_rows.jsonl`.
- `results/coding/`: the blind inspection of the runs whose label the instruments could not settle: the coders' decisions with their extents and
  extractions, the agreement between the two coders, the numeric replay of their extents, and the known-answer set that scored the coders. The second
  coder's packets, codebook and answers are included; the key that maps a second-coder packet to its run is not. The human readers' check, its answers and its key are in
  `results/coding/coder_check/`.
- `results/validation/9-instruments/`, `results/faults-live/`, `results/faults-batch/`: the instruments checked against known answers, and the
  fault-injection calibration of the platform's read record per option.
- `reports/refdet/`, `results/reference-validation/`: the reference detector checked against the original implementation.

## New run

A new run needs your own Onedata deployment holding the dataset in both layouts, model endpoints (an OpenAI-compatible endpoint for the open-weight
models, the Anthropic API for the Claude models), and a host that can run the sandbox image. In outline:

1. **Data.** `icsa/ingest/` downloads the Copernicus Marine sea-surface-temperature product, builds S1 and S2 and checks them against
   `data/manifest/`; the data are not redistributed (`ATTRIBUTION.md`).
2. **Instances.** `data/instances/` holds the frozen instance table; `icsa/instances/` holds the code that drew it (eligibility, boxes, design) and the
   reference ground truth per instance.
3. **Platform and sandbox.** `sandbox/` builds the image (its base pinned by digest); `config/harness.toml` points the harness at your platform;
   `docs/harness.md` describes the harness and `sandbox/INTERFACE.md` the sandbox.
4. **Runs.** `python -m icsa.campaign` schedules and runs the blocks; `config/models.toml` sets each model and its settings.
5. **Snapshot and analysis.** `python -m snapshot` cuts the campaign at a time, scores every run and writes the tables, exactly as for the results here.

The hosts, accounts and queue settings of the study's own fleet are left out (`BUILD-REPORT.md`, "Left out on purpose"); they are specific to the
study's infrastructure, and none is needed to regenerate any exhibit.

## What is not here

- **The full run directories and the campaign store.** They hold platform and host identifiers throughout. The trace sample, the scored rows and the
  inputs above are what the analysis reads.
- **Third-party data.** The Copernicus Marine data and files derived from them are not redistributed; `ATTRIBUTION.md` says how to obtain them.
- **An audit of the instruments on the campaign's runs.** The audit planned in the protocol was not run as designed. Its role is filled by the blind
  inspection under `results/coding/` and by the instruments' validation against known answers under `results/validation/9-instruments/`, which is a
  validation of the instruments, not an audit of the runs.

`MISSING.md` lists everything this copy does not hold.

## License

The code is under the MIT License (`LICENSE`). The results, the coding data, the traces and the documentation are under CC BY 4.0
(`LICENSE-CC-BY-4.0.txt`). Third-party data keeps its own terms (`ATTRIBUTION.md`).
