# Attribution and third-party material

Generated using E.U. Copernicus Marine Service Information; https://doi.org/10.48670/moi-00156

This artifact carries the study's own code, protocol texts, instance definitions, results and reports.
It does NOT redistribute third-party data or third-party code:

- **Copernicus Marine sea-surface-temperature data:** not included. The ingest scripts in `icsa/ingest/` download it
  from the Copernicus Marine Service; the checksums of the files they produce are in `data/manifest/`.
  Files derived from it (for example sea masks) are also left out.
- **The published catalogue and the reference authors' code:** not included; the reference detector in
  `icsa/refdet/` is a re-implementation, and `reports/refdet/` shows how it was checked against the original.

The licence of the code in this artifact is in `LICENSE`.
