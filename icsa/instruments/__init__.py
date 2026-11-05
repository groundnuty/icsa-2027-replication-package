"""Read- and analysed-extent instruments and the omission labeller (#9).

Design, decision rule and blind spots: DESIGN.md in this folder.

In the sandbox (#7), at interpreter start:
    hooks.install_from_env()            # ICSA_TRACE_DIR, ICSA_OUTPUT_DIR

Offline, per run (the entry point; its label and analysed extent go to scoring):
    lab = labeller.label_run(option, trace_dir, output_dir, index, required,
                             platform_dir=..., local_roots=..., dir_sizes=...,
                             code_text=labeller.code_cells_of(record.code_cells_path))
    icsa.scoring.scorer.score_run(record, run_dir, ref, lab.analysed, lab.label, ...)
    lab.read (decoded, from the ledger, every option), lab.listing (requests.Session.send: T,
    T-unpaginated, D); lab.fetched, lab.delivered (from the logs); flags["cross_check"], flags["listing_disagrees"]

Building blocks:
    analyse.analyse(trace_dir, output_dir, index, required) -> RunAnalysis
        .label (OmissionLabel), .reasons, .coverage, .coverage_upper,
        .loaded / .analysed / .analysed_upper / .bound (PartedExtent)
    readext.to_units(readext.proxy_reads(...) | fuse_reads(...) | strace_reads(...),
                     index, box, baseline_days, target_days) -> ReadExtent   # fetched / read
    listing.listing_summary(proxy_lines, dir_sizes) -> {dir: DirListing}
    disclosure.disclosure(label, disclosure.parse_report(path)) -> str
    audit.export_bundle(run_dir, analysis.summary(), out_root, run_key=..., meta=...)

Shared inputs:
    fullindex.load_full_index()                                 # every S1 file and S2, with Onedata ids
    layout.build_index(root, files) / LayoutIndex.load(path)   # a partial one, for tests
    icsa.instances.load.load_required_extents()[instance_id]    # the required extent (#5)

Validation: `python -m icsa.instruments.validate --work DIR`.
"""
