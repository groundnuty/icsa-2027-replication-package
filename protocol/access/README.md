# Access texts (the `{ACCESS}` slot)

**Status: draft, unblocked** (#10 item 3, 31 Oct). The official fsspec client returns only the first page of a listing, 1,000 entries, and never requests the next. T-unpaginated therefore uses a shim that follows the continuation token. It is the one data-path component written for this study.

**Rules:**
- T and T-unpaginated use the **same file**, `T.md`, so their prompts are byte-identical. The only difference between them is in the platform configuration (#7), never in the text.
- All three texts have the same shape: where the data are, the interface, and how to read a file with xarray. T and D are word-identical except for how file content is obtained.
- No text mentions listing, pagination, completeness, checking, or the other options. How to find the files is left to the agent in every option.

**One backend everywhere.** All three texts name the same xarray engine (`h5netcdf`), the only one that opens both file objects (T) and paths (D, M). S1/S2 carry no packing or valid-range attributes (#3), so any decoder gives identical values. Paths are absolute with no trailing slash.

**Slots filled by the code agent** from the deployed configuration (#7):
- `{DATASET_LOCATION}`: in S1, "the directory `<path>`" (the agent finds the daily files); in S2, "the file `<path>`" (no discovery, as the design says S2 has no listing). Identical across options for a given layout. `{MOUNT_LOCATION}` is the same phrase with the mount prefix;
- `{FS_EXPR}`: the expression that yields the preconfigured fsspec filesystem;
- `{MOUNT_ROOT}`: where the mount appears in the sandbox;
- `{SCRATCH}`: the local scratch directory.
