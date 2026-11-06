# Work that was not done as designed

The instrument audit of the registered design (a stratified sample read blind, with error rates per instrument) was not run as designed, and no file in this artifact is its result. Its role is filled by the blind inspection: known-answer scores, pair agreement and the numeric replay, shipped as coding data under `results/coding/` and labelled as such. The files under `results/validation/9-instruments` are the validation of the instruments against known answers, not that audit.

# Entries with no files in the source commit

- `results/traces`: All run traces (by manifest with sha256)
- `results/runs`: Run records and scored rows
- `results/analysis`: Analysis outputs: tables, figures and manifest
- `results/coding`: Coding data: the blind inspection (known-answer scores, pair agreement, the numeric replay) and the second coder's packets, from the final snapshot
- `results/reference-validation`: Reference validation results
- `results/pilot`: Pilot runs and the power re-estimate
- `notebooks`: Analysis notebooks

# Left out on purpose

- `tests`: Test suites: their fixtures carry addresses and host names; not in the paper's artifact list
- `reports/applicability, reports/budget, reports/prompt-cache-measurement`: Working reports, not in the paper's artifact list
- `day0`: Day-0 platform measurements; not in the paper's artifact list, and full of host and provider detail
- `bench`: Throughput benchmarks and spend logs, not part of the study
- `config/protocol-draft`: Superseded draft copy of protocol/
- `tools/diag, tools/artifact`: Developer diagnostics and the artifact build itself
- `data/*.jsonl, data/DOWNLOAD.md, data/UPLOAD.md`: Operational download and upload logs
- `hpc_sandbox deployment and fleet operations (deploy, bootstrap, caps allocator, rolling restart, node setup, smoke tests, assignment and image records)`: Host-, account- and queue-specific operations of the HPC fleet; the executor itself is included
- `docs/snapshot-interim fleet loops (provider add, mirrors, fills, restarts, replica, listings)`: Operational loops of the run fleet; the stage scripts that make the tables are included
- `config/slot_map.json, config/campaign_hosts.example.*, config/provider-watch.example.json`: Host and slot identifiers of the run fleet
- `tools/b_launch, tools/provider_watch, tools/provider_mon*, tools/newhost, tools/host_split.py`: Fleet operation tools, not needed to regenerate any exhibit
- `data/instances/sea_masks.npz, *.nc`: Third-party-derived data: scripts only until the terms are confirmed
- `k76-stub (7.6 GB)`: The known-answer stub, too large for the draft; the run outputs it was made from are included under results/coding/k/k76-runs
- `reports/octave_domain/step3/events_mean_series.f64`: A 122 KB raw float64 series of the whole-domain Octave run, a numeric binary like the other binary data files; its sha256 stays in reports/octave_domain/step3/outputs.sha256 and the whole-domain result is in results/reference-validation/octave-domain/domain.json

# Left out by size

- none
