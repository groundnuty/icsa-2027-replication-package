"""The M audit reader for main's agent runs: the platform side of H3's agent-run measure on the default record (site_g's file-access audit log).

An incremental, byte-bounded pull of the log (`pull`, `ledger`, `remote`), the runs' lease windows and site_g's op_worker restarts (`windows`), the attribution of
lines to runs by (slot user, lease) (`attribute`), and one record per run (`record`). Design: /mnt/volume2/icsa-2027/lane-teardown/M-AUDIT-DESIGN.md."""
