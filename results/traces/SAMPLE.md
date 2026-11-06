# The trace sample of this draft

A sample of 413 runs of the 490 drawn (10 for each option x layout x model cell that has runs, 49 cells): to keep the draft under its size limit the sample was cut from the END of the seeded order, so every cell keeps its first 8 to 9 runs and 77 runs of the highest ranks are left out.

## How the runs were chosen

By position alone. The planned run keys of each cell were put in a seeded order (seed `icsa-2027-draft-sample-1`; the order depends on the keys and the seed and on nothing else: no label, outcome, size or any derived field is read), and the first runs of that order that had ended by the staging cut-off were taken.

Staging cut-off: 2026-11-06T08:15Z, the time of the last copy of run directories to the staging host. The final tables are cut at 2026-11-06T09:00Z: the staging cut-off is earlier than that, so a run that ended between the two counts as not ended by the staging cut-off (its position was skipped). 
A run that ended unfinished, on a cap or an error, counts as ended and is in the sample when its position comes up. Only a run still in flight or not started at the cut-off was skipped, and the next in the seeded order was taken: 2 positions were skipped as not ended by the staging cut-off (of 2450 planned runs, 2445 had ended). 3 chosen runs ended without a pulled run directory and appear as a note file.

## What each run holds

Transcripts, code cells, run records, gate requests and the other trace files of the run directory, with real names, hosts, addresses and paths replaced by neutral labels (the same value has the same label in every file) and no number changed (checked for every file). Text files over 64 KiB are gzipped; transcripts and code cells stay plain files.
Three kinds of opaque long strings are replaced by short labels derived from the string itself (the same string has the same label everywhere): Onedata list-files cursors (`cur-...`, they carry a file name; 72541 replacements in this sample), Onedata file ids (`guid-...`, they carry a file and a space id; 37639) and the model API's signature on thinking blocks in transcripts (`sig-...`, an opaque integrity value of no use to a reader; 857).
The raw perf CSVs of the M option are left out; each run directory has `perf_summary.json` instead (counts, sums and quantiles of duration and size per class and operation, the number of distinct files, the time span, and the size and sha256 of the raw CSV so that it can be matched later).
Trace files dropped to fit the size limit: none.
Files left out by decision: none.
The narrow rules of the scans that apply to these files, and how many strings each let through, are stated in the README of this artifact.

## The rest of the traces

All raw traces come with the later artifact. For its planning: the raw run directories of the whole campaign were about 88.8 GiB in 2,089 run directories, of which about a fifth is the raw perf CSVs (stat only, measured on 5 Nov).
