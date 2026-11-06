# Results

Every result here comes from the study's fixed snapshot: the one sealed copy of the campaign that the paper's numbers are computed from.
Earlier (interim) snapshots were used only to rehearse the pipeline and are not part of this package. `<snapshot>` below is the fixed snapshot's folder name.

| Path | What it holds | Made by |
|---|---|---|
| `analysis/<snapshot>/PRIMARY.json` | Which result folder's tables are the primary ones. `<folder>` is one of `out` (the frozen run), `out-coded` (with the coders' inspection labels), `out-kaug`, `out-coded-kaug` (the same, with the runs that reached the time cap counted as K), or a sensitivity folder | the snapshot's driver |
| `analysis/<snapshot>/<folder>/tables/` | The analysis tables and figures of the fixed snapshot, with their manifest. Every table starts with the snapshot's header line | `icsa.analysis.run.run_all`, called by `snapshot/run.py` |
| `analysis/<snapshot>/<folder>/pipeline/` | The inputs of those tables: one scored row per analysed run, the coded causes, the cause flags, the infrastructure export, the outcome-less counts | the scoring pipeline (`icsa/pipeline`, `icsa/scoring`) |
| `analysis/<snapshot>/<folder>/inputs/` | The remaining inputs the analysis read: counted start per run (for the cohort), enforcement overhead, fault-injection fidelity rows and H3 table, the coders' inspection labels and coverage; `inputs.json` lists their sources and sha256 | the snapshot's frozen inputs |
| `analysis/<snapshot>/<folder>/SNAPSHOT.json` | The snapshot's own record: its time, cap, cut, inputs and the code it ran | `snapshot/run.py` |
| `exhibits/` | The figures and the fault-type fidelity table that the paper shows, made from the tables above | `docs/snapshot-interim/paper_exhibits.py` |
| `coding/` | Blind inspection: the coders' decisions with their extents and extractions, pair agreement, the numeric replay of the coders' extents, the known-answer packets and scores, the second coder's sheet and packets (and the second coder's answers, when they are in) | `icsa/inspection`, `snapshot/coderreplay.py`, `snapshot/codersheet.py` |
| `traces/` | A sample of whole run traces, up to ten per option × layout × model (fewer where the sample was cut to fit; `BUILD-REPORT.md` says), chosen by a seeded order of the run keys alone (no label, outcome or derived field is read); one compressed archive per run, anonymised like every other file | the package's anonymising build (not shipped) |
| `mplus/` | The M+ measurement: provisioning time and bytes per layout, time to first compute, and the break-even, with its summary table | `tools/mplus` |
| `knowledge/` | Knowledge-plane equality per layout | `icsa/knowledge` |
| `validation/9-instruments/` | Validation of the read- and analysed-extent instruments against known answers (a validation of the instruments, not an audit of the runs) | `icsa/instruments` |
| `faults-live/`, `faults-batch/` | Fault-injection calibration of the platform's read record per option: live runs and batch rescoring | `icsa/faults`, `icsa/calibration` |
| `reference-validation/octave-domain/` | Whole-domain check of the reference detector against the original implementation under GNU Octave | `octave_domain/` |

Not every path is filled in every copy of this package: `MISSING.md` at the top lists what this copy does not yet hold.
