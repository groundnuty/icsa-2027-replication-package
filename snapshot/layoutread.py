"""`layout_read`: which layout's files a run read, the same definition for every option (#34, science's request of 5 Nov, comment 6646904218).

    python -m snapshot.layoutread read <seal>      # <seal>/layout/layout_read.csv, counts_by_reason.json, layout_read.meta.json
    python -m snapshot.layoutread h3   <seal>      # the H3 reading beside the primary: <seal>/layout/h3-own/
    python -m snapshot.layoutread own  <seal>      # the own-layout-only analysis beside every contrast: <seal>/layout/out-own/ and beside/
    python -m snapshot.layoutread all  <seal>      # the three, in this order

A run reads one layout (its own: the directory its layout is stored in) and may read the other's sibling directory. The frozen detector
(`icsa.faults.detector`) maps a read against the run's OWN manifest only, so a sibling read is `n_unmapped` there and invisible. This tool maps
every read against BOTH layouts' manifests (`data/manifest/s1_sha256.txt`, `s2_sha256.txt`: S1 is `s1z/<name>`, S2 is `s2z/sst_s2.nc`).

Per run, the analysed attempt's evidence, from the frozen inputs of a sealed snapshot, never the live campaign:
- T, T-unpaginated, D: the gate's `gate_requests.jsonl`: `tag=content`, `decision=allow`, GET, status 200 or 206, the bytes it sent, by file. The file id
  is the one the gate saw (`/data/<id>/content`); it is turned into a path by the ids of the run's OWNER provider (`M/providers.json`), never site_g's for a
  B run.
- M, M+: oneclient's performance log: the `FsLogic` `read` rows (bytes asked of the client, by file path). `ReadCache` rows are prefetch and never count.
- every option, beside that: the run's own audit lines (`<audit root>/<provider>/runs/<block>__<run>/<attempt>/lines.log.gz`, what extract attributed to
  the run's lease). They carry no bytes (request, user, uuid, path), so a layout is read there by at least one `open_file*` or `remote_read` on one of its
  files, the events the frozen detector counts. Listings and attribute lookups never count.

A layout is READ by a run when it has more than 0 content bytes or at least one audit open or read. `layout_read` is over the union of the run's sources:
`own` (own layout only), `other` (the sibling only), `both`, `none` (a source we can trust shows no read in either layout). No size threshold: `bytes_own`
and `bytes_other` are in the file for anyone who wants one. When no source stands, `layout_read` is EMPTY with the reasons, never guessed; `other_seen` says
whether the partial evidence already shows a sibling read (the run is then certainly `other` or `both`). A read that maps to no file of either manifest
(an id or a path the manifests do not hold) makes the value empty too, unless both layouts were already seen.

Nothing here writes outside `<seal>/layout/`, prints a value or a count by option: stdout is the number of rows written and exit codes. It reads, and
changes, no file of the frozen tree (`icsa/`) or of the pinned H3 measure."""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import argparse         # noqa: E402
import csv              # noqa: E402
import gzip             # noqa: E402
import hashlib          # noqa: E402
import json             # noqa: E402
import os               # noqa: E402
import re               # noqa: E402
import subprocess       # noqa: E402
from collections import Counter     # noqa: E402
from dataclasses import dataclass   # noqa: E402
from pathlib import Path            # noqa: E402

SCHEMA = "layout_read/1"
OWN, OTHER, BOTH, NONE, EMPTY = "own", "other", "both", "none", ""
REST_OPTIONS = ("T", "T-unpaginated", "D")
MOUNT_OPTIONS = ("M", "M+")
COLUMNS = ("run_key", "layout", "layout_read", "bytes_own", "bytes_other", "source", "reason",
           "block", "run", "instance", "model", "seed", "option", "provider", "environment", "attempt_dir", "other_seen", "n_audit_own", "n_audit_other", "audit_layout_read",
           "bytes_own_perf", "bytes_other_perf", "perf_layout_read", "layout_read_with_perf", "source_with_perf", "reason_with_perf", "other_seen_with_perf", "audit_lines_excluded",
           "backend", "slot", "bytes_between_sites", "bytes_to_sandbox", "gate_transfers_status")
SHARE_COLUMNS = ("block_group", "option", "model", "backend", "environment", "runs", "share")
SITE_BA_SLOTS = ("gemma-107",)       # the site_ba model slots (`site_ba_extra.py`'s `extra-slots.json` on the run VM); `frozen/site_ba-slots.txt` of a seal, one slot per line, replaces this default
STALL_COLUMNS = ("run_key", "block", "run", "instance", "layout", "model", "seed", "option", "provider", "host", "environment", "attempt_dir", "max_read_gap_s", "max_read_gap_source",
                 "n_read_events", "max_read_duration_s", "gap_reason", "hung_task_lines", "hung_reason", "stall_evidence", "lease_start", "lease_end")
OPEN_READ_S = 300.0                  # a read call open this long (a FUSE-level stall: the read itself, not the model's thinking) ...
STALL_GAP_S = 300.0                  # science, #34 05:06Z: the totals the terminal may show are the M runs with a gap of at least 5 minutes ...
BYPASS_COLUMNS = ("run_key", "block", "run", "instance", "model", "seed", "option", "provider", "environment", "layout", "status", "reason", "nonzero", "bypass_files", "bypass_events",
                  "audit_unmapped_events", "n_gate_requests", "n_gate_files", "n_audit_open_read", "n_audit_files", "gate_unmapped_requests", "audit_lines_excluded", "bypass_file_list")
_REAL_CONTENT = re.compile(r"/data/([^/]+)/content$")
H3_REASONS = {OTHER: "layout_read_other", BOTH: "layout_read_both"}
H3_SIBLING_SEEN = "layout_read_sibling_seen"
DEFAULT_DATA_ROOT = Path("/mnt/volume2/icsa-2027")
DEFAULT_AUDIT_ROOT = DEFAULT_DATA_ROOT / "snap-h3"
DEFAULT_PIN = DEFAULT_AUDIT_ROOT / "pin.txt"
DEFAULT_PROVIDER_TABLE = DEFAULT_DATA_ROOT / "lane-snap4" / "providers.tsv"


DEFINITIONS_MD = """# What `layout/` holds (static text: no value, no count)

Written by `snapshot.layoutread read` into every snapshot's sealed directory. Everything in `layout/` is sealed with the rest of the snapshot.

## layout_read.csv: which layout's files a run read
- One row per scored run (the rows of `out-coded/pipeline/scored_rows.jsonl`, else `out/`). `layout` is the run's own layout (S1: `s1z/`, daily files; S2: `s2z/`, one file).
- **`layout_read` (the MAIN field)** is defined the same for every option: the gate's content bytes by file for T, T-unpaginated and D, and for ALL options (M and M+ included) the run's own
  provider audit lines mapped against BOTH layouts' manifests (an `open_file*` or `remote_read` on a file; the lines carry no bytes). A layout is READ when it has more than 0 content bytes or at least
  one audit open or read; no size threshold (`bytes_own`, `bytes_other` are the gate's bytes, for T, T-unpaginated and D only). Values: `own` (only the run's own layout), `other` (only the sibling's),
  `both`, `none` (a source that stands shows no read in either layout), empty (no source stands: see `reason`; never guessed).
- `other_seen=1`: the partial evidence of an empty run already shows a sibling read (it is certainly `other` or `both`).
- **M's oneclient performance-log bytes are beside it, never in it:** `bytes_own_perf`, `bytes_other_perf` (FsLogic read rows; prefetch never counts), `perf_layout_read` (perf alone) and
  **`layout_read_with_perf`** (the union of the main sources and the perf log; equal to `layout_read` for T, T-unpaginated and D), with `source_with_perf`, `reason_with_perf`, `other_seen_with_perf`.
- Audit lines are used only when the sealed audit record stands behind them (observed, the analysed attempt's, the same number of lines now as when it was sealed); otherwise `reason` says why.
- `environment`: `vm`, `hpc` or `unknown`, from the run's owner provider (the winning attempt's store; lane-snap's provider table: a `site_a` line is HPC; site_g and every other listed provider are the run VMs;
  an unlisted provider is `unknown`).

## bypass.csv: the bypass count (reported, never a filter on the primary)
- For each REST run (T, T-unpaginated, D) whose gate log and audit lines both stand (`status=compared`): `bypass_files` = files the provider's audit shows the slot user opening or reading that the gate
  log has no content request for (a gate request of any method or status counts as served); `bypass_events` = those audit opens and reads; `audit_unmapped_events` = audit opens or reads of a path in neither
  manifest; `nonzero` = 1 when either is above 0. Other statuses: `no_gate`, `no_audit`, `uncertain` (a gate request for a file no manifest holds), `not_applicable` (M, M+: no gate), `no_owner`, `no_attempt_dir`.
  `bypass_summary.json` is the totals.

## m_stalls.csv: M's stall fields (one row per M run; M+ and the REST options have none)
- `max_read_gap_s`: the longest single gap between two read events of the run. `max_read_gap_source` says where it comes from: `perf` (oneclient's performance log: the `FsLogic` `read` rows; the
  prefetch rows are not reads; a gap is not taken across two log files; the log's `Time` is a time of day, a drop of more than 12 h is midnight, a smaller step back is a clock step and no gap),
  else `audit` (the run's audit lines, `remote_read`, with the exclusion windows left out), else `none` (empty, with `gap_reason`: fewer than two reads, no source that stands). `n_read_events`.
- `max_read_duration_s`: the longest single `FsLogic` read CALL of the run (the perf log's `Duration [us]`; the `Time` column is the call's END, so a read was open from `Time - Duration`). Perf only.
- `stall_evidence` (only for a run whose `max_read_gap_s` is 300 s or more): what shows the gap was a stall and not the model thinking. `open_read`: a read call was open 300 s or more at the FUSE level
  (`max_read_duration_s >= 300`); a hang in a lookup or an open is not a read call and is not seen here. `hung_task`: `hung_task_lines` is above 0 (host level, inside the lease window). `both`. `none`:
  both are known and neither shows it (the model thinking, a computation, or a hang the logs do not carry). `unknown`: neither shows it and one of the two could not be had. Empty: no gap of 5 minutes.
- `hung_task_lines`: how many kernel lines `blocked for more than ...` the run's HOST logged inside its lease window (`lease_start`..`lease_end`, inclusive; every task of the host, not only the
  agent's), from the copy of the host's kernel journal the driver froze into `frozen/kernel-hung/<provider>__<host>.log` (host = the audit record's `host`, `-` for none). An empty log is 0, a value; a
  log that is missing is unknown (`hung_reason` = `no_kernel_log`), as is one whose journal starts after the lease (`journal_starts_after_the_lease`, from `<log>.since`), one with a line whose stamp
  cannot be read (`kernel_log_stamp_unreadable`), and a run with no lease window (`no_lease_window`). `hung_task_lines` is EMPTY then, never 0. `m_stalls_summary.json` has the totals.

## backend_shares.csv: where the models ran, per option x model
- One row per (`block_group`, `option`, `model`, `backend`, `environment`): `runs` and its `share` of the (block group, option, model) cell; layouts are merged; scored runs only. `block_group` is `primary` for
  the analysis's primary blocks (main and pagination: one analysis) and the block's own name for any other (the pilot).
- `backend` is where the MODEL ran, from the winning attempt's run record (`backend` and `slot`, also in layout_read.csv): `site_a` (an HPC slot), `site_ba` (an HPC slot listed in `frozen/site_ba-slots.txt`,
  default `gemma-107`), `site_b`, `anthropic`, or `unrecorded`. `environment` is where the run's DISPATCHER ran (`vm`, `hpc` or `unknown`: the owner provider, as in layout_read.csv). The two are different things.
- The primary analysis's own `tables/backend_shares.csv` (per model, option and layout, by the row's `backend` only) is unchanged; this is the table beside it with the site_ba split and the environment.

## gate_bytes.csv and bytes_relation.csv: the gate's bytes beside the bytes between the sites (H2)
- `bytes_between_sites` (also a column of layout_read.csv, from the scored row) is the sidecar's counter and is NOT measured on HPC: it is EMPTY there, never 0. `bytes_to_sandbox` is the content bytes
  the GATE sent to the sandbox (`sandbox.gate_transfers.bytes_to_sandbox` of the run record), kept per run for the gated options (T, T-unpaginated, D) on BOTH environments in `gate_bytes.csv`;
  `gate_transfers_status` says `ok` or why it is empty (`unavailable`: the gate died, restarted or could not write; `no_run_record`, `no_gate_transfers`, `not_recorded`, or the run's own
  `no_owner` / `no_attempt_dir`). The two are separate columns and are never mixed.
- `bytes_relation.csv`: on the VM runs of a gated option where BOTH exist, per option and layout: the runs, how many have both, how many lack either, the sums, the ratio of the sums
  (between sites / to sandbox), the median, minimum and maximum of the per-run ratio, the runs where they are equal, and the Pearson correlation. HPC runs are not in it.
- `bytes-measured/` (own step): H2's bytes contrast on the units whose compared options were ALL measured (below). `beside/h2_bytes.csv` has the bytes rows of `h4_directions.csv` of the primary and of
  this variant side by side. `layout/bytes_units.json` says how many units qualify (`primary_qualifying` for the primary blocks; `qualifying_lenient` counts the units with at least one measured run per option,
  which is what the primary's own mean of the measured seeds would use).

## h3-own/: the H3 reading beside the primary
- A copy of `h3/platform_rows.jsonl` in which both records of every run with `layout_read` `other` or `both` (or `other_seen`) are `not_observed` with the reason `layout_read_other`, `layout_read_both` or
  `layout_read_sibling_seen`, then the PINNED H3 measure, unchanged, on it (`measure/`; counted by reason by the measure itself). The primary `h3/measure/` is untouched. `h3_own.json` is its account.

## own-only/, env-vm/, env-hpc/: the frozen analysis on a subset of UNITS
- A UNIT is instance x layout x model. The primary blocks (`main` and `pagination`) are one group, so T-unpaginated (block `pagination`) belongs to the unit of the T, D and M runs of `main`; the pilot is its own.
  Subsets are of units, never of runs, so the model mix and the pairing across options do not change.
- `own-only`: a unit leaves, for levels and contrasts alike, when ANY of its runs (T-unpaginated included) has `layout_read` `other` or `both` (or `other_seen`). Units with no evidence stay and are counted.
  `own-only-strict` (only if asked): a unit also leaves when any of its runs has an empty `layout_read`.
- `bytes-measured`: only the units whose compared options (the options of the pre-registered contrasts: T, D and M) were all MEASURED for the bytes between the sites: every option has runs and every run of
  it has its count (a measured 0 is measured; an unknown is never 0). The frozen contrast takes, for an instance, the mean over the seeds that have a value and pairs the arms by region, so a unit
  measured in one option and not in another would enter it with different instances in each arm; this variant leaves such units out, so H2's bytes contrast rests on the VM runs.
- `env-vm` / `env-hpc`: only the units whose runs ALL ran in that one environment (a unit with runs in both is `mixed`, with an `unknown` run `unknown`; neither qualifies). `environment_units.json` says how many units qualify.
- Each variant directory: `tables/` (the whole analysis on the kept units; every table's FIRST LINE is `# snapshot final=<true|false> t=<t>`: read a CSV with `pd.read_csv(path, skiprows=1)`), `inputs/` (the filtered
  infra account, labels and coverage it took), `units.csv`, `units_by_model.csv` (units, units_left, units_kept, units_kept_with_a_run_without_value, and units by environment, per model), `dropped_runs.csv`,
  `own_only.json`. The other CSVs of `layout/` (`layout_read.csv`, `bypass.csv`, `units*.csv`, `dropped_runs.csv`) have NO snapshot line: read them with a plain `pd.read_csv`.
  A variant with no unit left has an empty `tables/` and `skipped` in `own_only.json`.
- `own-only/beside/<table>.csv` (the primary's and the variant's effect, interval, Holm p, smallest-effect verdict and regions side by side, with `direction_changed` and `threshold_crossed`, for every table with an
  effect per `layout` and `contrast`) and `environments/beside/<table>.csv` (the primary's, the VM's and the HPC's side by side): their first line is the snapshot line too.
"""


class LayoutReadError(RuntimeError):
    """A refusal or a failure; the message never holds a value of the data."""


# ---- the exclusion list ------------------------------------------------------------------------------------------------------------------
def _utc_s(iso: str) -> str:
    import datetime as dt
    return dt.datetime.fromisoformat(iso.strip().replace("Z", "+00:00")).astimezone(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def load_exclusions(path: Path | None) -> dict[tuple[str, str], list[tuple[str, str]]]:
    """{(provider, slot): [(from, to)]}: the windows in which a foreign actor shared a slot user (science, #34 5 Nov 02:50Z; `frozen/h3-exclusions.tsv` of a seal, in the format
    `snapshot/h3exclusions.py` reads: provider, slot, from, to, reason, tab separated, `#` comments, all five fields). Bounds are kept as `YYYY-MM-DD HH:MM:SS` UTC strings: an audit line's
    own stamp compares with them as text (`to` is inclusive to the end of its second). A missing file is no window; a malformed line is an error, never skipped."""
    out: dict[tuple[str, str], list[tuple[str, str]]] = {}
    if path is None or not Path(path).is_file():
        return out
    for n, ln in enumerate(Path(path).read_text().splitlines(), 1):
        if not ln.strip() or ln.lstrip().startswith("#"):
            continue
        f = ln.split("\t")
        if len(f) != 5 or not all(x.strip() for x in f):
            raise LayoutReadError(f"{path}:{n}: five tab-separated fields expected (provider, slot, from, to, reason)")
        try:
            lo, hi = _utc_s(f[2]), _utc_s(f[3])
        except ValueError as e:
            raise LayoutReadError(f"{path}:{n}: not an ISO time: {e}") from None
        if hi < lo:
            raise LayoutReadError(f"{path}:{n}: the window ends before it starts")
        out.setdefault((f[0].strip(), f[1].strip()), []).append((lo, hi))
    return out


# ---- the host kernels' hung-task lines (M stalls) ------------------------------------------------------------------------------------------
_K_ISO = re.compile(r"^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})(?:\.\d+)?(Z|[+-]\d{2}:?\d{2})?(?:\s|$)")
_K_SYSLOG = re.compile(r"^([A-Z][a-z]{2})\s+(\d{1,2})\s+(\d{2}:\d{2}:\d{2})(?:\s|$)")
_MONTHS = {m: i for i, m in enumerate(("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"), 1)}
HUNG = "blocked for more than"


def kernel_log_name(provider: str, host: str | None) -> str:
    """The file of a host's kernel log in `frozen/kernel-hung/`: `<provider store>__<host>.log`, host as the audit record names it (site_g's store: `.23`, `.8`), `-` for none."""
    return f"{provider}__{host or '-'}.log"


def _k_epoch(line: str, year: int) -> float | None:
    """The time of a kernel-journal line: `journalctl -o short-iso` (offset or none = UTC) or a classic syslog stamp (UTC, `year`); None when it has neither."""
    import calendar
    import datetime as dt
    m = _K_ISO.match(line)
    if m:
        d = dt.datetime.fromisoformat(f"{m[1]}T{m[2]}")
        off = 0
        if m[3] and m[3] != "Z":
            sign = -1 if m[3][0] == "-" else 1
            hh, mm = int(m[3][1:3]), int(m[3][-2:])
            off = sign * (hh * 3600 + mm * 60)
        return calendar.timegm(d.timetuple()) - off
    m = _K_SYSLOG.match(line)
    if m and m[1] in _MONTHS:
        h_, mi, se = m[3].split(":")
        return calendar.timegm((year, _MONTHS[m[1]], int(m[2]), int(h_), int(mi), int(se)))
    return None


def load_kernel_logs(directory: Path | None, year: int) -> dict[str, dict]:
    """{file name: {epochs: sorted times of its `blocked for more than` lines, bad: how many of them have no readable stamp, since: the journal's first stamp or None}}. A file that is
    absent is not in the dict: the host's kernel is `unknown` (the driver writes the file only when the copy succeeded; an empty file is zero lines, a value)."""
    out: dict[str, dict] = {}
    if directory is None or not Path(directory).is_dir():
        return out
    for p in sorted(Path(directory).glob("*.log")):
        epochs, bad = [], 0
        for ln in p.read_text(errors="replace").splitlines():
            if HUNG in ln:
                t = _k_epoch(ln, year)
                if t is None:
                    bad += 1
                else:
                    epochs.append(t)
        since = None
        sp = p.with_name(p.name + ".since")
        if sp.is_file() and sp.read_text().strip():
            since = _k_epoch(sp.read_text().strip().splitlines()[0], year)
        out[p.name] = {"epochs": sorted(epochs), "bad": bad, "since": since}
    return out


# ---- both layouts' manifests -------------------------------------------------------------------------------------------------------------
class LayoutMap:
    """A file's layout, from both layouts' manifests: `s1z/<name>` is S1, `s2z/<name>` is S2. A directory, the space root or a name in neither is None."""

    def __init__(self, s1_names, s2_names, s1_dir: str = "s1z", s2_dir: str = "s2z"):
        s1_names, s2_names = list(s1_names), list(s2_names)
        self.files = {f"{s1_dir}/{n}": "S1" for n in s1_names} | {f"{s2_dir}/{n}": "S2" for n in s2_names}
        if len(self.files) != len(s1_names) + len(s2_names):
            raise LayoutReadError("a name is in both manifests, or twice in one")

    @classmethod
    def from_manifests(cls, s1: Path, s2: Path) -> "LayoutMap":
        def names(p):
            return [line.split()[-1] for line in Path(p).read_text().splitlines() if line.strip()]
        return cls(names(s1), names(s2))

    @classmethod
    def default(cls) -> "LayoutMap":
        from icsa.instruments import fullindex
        return cls.from_manifests(*fullindex.MANIFESTS)

    def of_rel(self, rel: str | None) -> str | None:
        return None if not rel else self.files.get(rel.strip("/"))

    def rel_of_path(self, path: str | None) -> str | None:
        """A logged path (`/<space id>/s1z/sst_19820105.nc`, a mount path): the logs prefix a space id or name, so the longest tail on a '/' boundary that is a file;
        that file's path in the space, or None."""
        if not path or path in ("null", "undefined"):
            return None
        parts = path.strip("/").split("/")
        for i in range(len(parts)):
            cand = "/".join(parts[i:])
            if cand in self.files:
                return cand
        return None

    def of_path(self, path: str | None) -> str | None:
        rel = self.rel_of_path(path)
        return None if rel is None else self.files[rel]


# ---- one source's evidence ---------------------------------------------------------------------------------------------------------------
@dataclass
class Ev:
    """What one source shows of a run. `own`/`other`: bytes (gate, perf) or open/read events (audit) on files of the run's own and the sibling layout;
    `unmapped`: the same unit on something no manifest holds; `reason`: why the source cannot stand alone (None: it can), its counts then being partial.
    `files`: file (path in the space) -> requests (gate: every allowed content request, whatever its status or method) or open/read events (audit); `n_events`:
    their total, mapped or not. The bypass count compares the two."""
    source: str
    own: int = 0
    other: int = 0
    unmapped: int = 0
    reason: str | None = None
    files: dict | None = None
    n_events: int = 0
    files_unmapped: int = 0
    n_excluded: int = 0                  # audit lines left out because they fall in an exclusion window of the run's slot
    max_gap_s: float | None = None       # M stalls: the longest gap between two read events (perf: FsLogic reads; audit: remote_read), None when not measured
    n_reads: int = 0                     # the read events it was measured over
    gap_reason: str | None = None        # why the gap could not be measured though the source stands
    max_dur_s: float | None = None       # perf only: the longest single FsLogic read call (its `Duration [us]`), None when the log has no such column

    def __post_init__(self):
        if self.files is None:
            self.files = {}

    @property
    def has_bytes(self) -> bool:
        return self.source in ("gate", "perf") and self.reason is None


def _side(layout: str | None, own_layout: str) -> str | None:
    return None if layout is None else ("own" if layout == own_layout else "other")


def _bump(ev: Ev, side: str | None, n: int) -> None:
    if side is None:
        ev.unmapped += n
    else:
        setattr(ev, side, getattr(ev, side) + n)


def gate_evidence(run_dir: Path, ids: dict[str, str] | None, lm: LayoutMap, own_layout: str) -> Ev:
    ev = Ev("gate")
    p = Path(run_dir) / "gate_requests.jsonl"
    if not p.is_file():
        ev.reason = "no_log"
        return ev
    try:
        rec = json.loads((Path(run_dir) / "run_record.json").read_text())
    except (OSError, ValueError):
        ev.reason = "no_run_record"
        return ev
    if ((rec.get("sandbox") or {}).get("gate_transfers") or {}).get("unavailable"):
        ev.reason = "log_lost"               # the gate died, restarted or could not write: lost, never read as complete
        return ev
    if ids is None:
        ev.reason = "no_ids"
        return ev
    bad = 0
    for line in p.read_text().splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except ValueError:
            bad += 1
            continue
        if not isinstance(r, dict) or r.get("tag") != "content" or r.get("decision") != "allow":
            continue
        path = str(r.get("path") or "")
        m = _REAL_CONTENT.search(path)
        rel = ids.get(m.group(1)) if m else (path[len("/data/"):] if path.startswith("/data/") else None)
        layout = lm.of_rel(rel)
        ev.n_events += 1                     # an allowed content request of any method or status: it may have reached the provider
        if layout is None:
            ev.files_unmapped += 1
        else:
            ev.files[rel.strip("/")] = ev.files.get(rel.strip("/"), 0) + 1
        if r.get("status") not in (200, 206) or str(r.get("method") or "GET").upper() != "GET":
            continue
        sent = int(r.get("bytes") or 0)
        if sent > 0:
            _bump(ev, _side(layout, own_layout), sent)
    if bad:
        ev.reason = "bad_lines"
    return ev


def _tod_gap(prev: float, tod: float) -> float:
    """The gap between two times of day: a drop of more than 12 h is the midnight rollover; a smaller step back is a clock step, not a gap (as `icsa.faults.records.perf`)."""
    d = tod - prev
    if d < -12 * 3600:
        d += 86400
    return d if d > 0 else 0.0


def perf_evidence(run_dir: Path, lm: LayoutMap, own_layout: str) -> Ev:
    """oneclient's performance log: the `FsLogic` `read` rows, as `icsa.instruments.crosscheck.perf_reads` takes them (`ReadCache` rows are prefetch and never count). One
    `csv.reader` pass with the columns found by name: the logs of an M run are tens of MB each and a snapshot has many. Also the longest gap between two of those reads (the
    `Time` column is a time of day; each file is one oneclient session: gaps are not taken across files)."""
    ev = Ev("perf")
    files = sorted((Path(run_dir) / "oneclient_perf").glob("read_write_perf-*.csv"))
    if not files:
        ev.reason = "no_perf_csv"
        return ev
    bad = 0
    memo: dict[str, str | None] = {}
    for f in files:
        with open(f, newline="") as fh:
            rd = csv.reader(fh)
            head = [str(h).strip().lower() for h in next(rd, [])]
            try:
                ic, io_, isz, ifile = (head.index(k) for k in ("class", "operation", "size", "file"))
            except ValueError:
                bad += 1
                continue
            it = head.index("time") if "time" in head else None
            idur = head.index("duration [us]") if "duration [us]" in head else None
            if it is None:
                ev.gap_reason = "no_time_column"
            width = max(ic, io_, isz, ifile, it or 0, idur or 0) + 1
            prev = None
            for r in rd:
                if len(r) < width:
                    bad += 1
                    continue
                if r[ic] != "FsLogic" or r[io_] != "read":
                    continue
                if idur is not None:
                    try:
                        dur = float(r[idur]) / 1e6
                    except ValueError:
                        dur = None
                    if dur is not None and (ev.max_dur_s is None or dur > ev.max_dur_s):
                        ev.max_dur_s = dur
                if it is not None:
                    try:
                        h_, m_, s_ = r[it].split(":")
                        tod = int(h_) * 3600 + int(m_) * 60 + float(s_)
                    except ValueError:
                        ev.gap_reason = "bad_time"
                    else:
                        ev.n_reads += 1
                        if prev is not None:
                            g = _tod_gap(prev, tod)
                            if ev.max_gap_s is None or g > ev.max_gap_s:
                                ev.max_gap_s = g
                        prev = tod
                try:
                    size = int(r[isz])
                except ValueError:
                    bad += 1
                    continue
                if size > 0:
                    path = r[ifile]
                    side = memo.get(path, memo)
                    if side is memo:
                        side = memo[path] = _side(lm.of_path(path), own_layout)
                    _bump(ev, side, size)
    if bad:
        ev.reason = "bad_rows"
    return ev


def _iter_lines(fh, size: int = 1 << 22):
    """The lines of a text file as `str.splitlines` splits them (a line may hold a character file iteration does not break at: U+2028, a vertical tab, a lone CR), read in chunks of `size`
    characters: the largest audit file of a seal is 15 MB packed and 840 MB of text, and a worker must not hold that. The last, possibly unfinished, line of a chunk is carried to the next.
    Lines keep their terminators; `scan_audit` strips what it needs."""
    carry = ""
    while True:
        chunk = fh.read(size)
        if not chunk:
            break
        parts = (carry + chunk).splitlines(keepends=True)
        carry = parts.pop() if parts else ""
        yield from parts
    if carry:
        yield carry


def scan_audit(lines, ev: Ev, lm: LayoutMap, own_layout: str, windows: list[tuple[str, str]] | None = None, times: bool = False) -> tuple[int, int]:
    """One pass over the audit lines: (lines the format matches, lines it does not), and into `ev` the opens and reads by layout and by file. The same line format and
    request classification as the frozen parser (`icsa.faults.records.audit`: `_LINE`, `classify_request`), without building an event or a timestamp per line: a run
    can have hundreds of thousands of lines, and a snapshot has thousands of runs. A test holds the two equal. `windows`: exclusion windows of the run's slot; a line whose own
    stamp is in one still counts as a line (the seal counted it) and is not evidence. `times`: also the longest gap between two `remote_read` lines (`ev.max_gap_s`,
    `ev.n_reads`), M's stall field."""
    import calendar
    import time as _time
    from icsa.faults.records.audit import _LINE, classify_request
    from icsa.faults.records.base import Kind
    n = bad = 0
    memo: dict[str, tuple[str | None, str | None]] = {}
    day_epoch: dict[str, int] = {}
    prev_t = None
    for line in lines:
        if not line.strip():
            continue
        m = _LINE.match(line.rstrip())
        if m is None:
            bad += 1
            continue
        n += 1
        if windows:
            ts = f"{m['date']} {m['time']}"
            if any(lo <= ts <= hi + ".999999" for lo, hi in windows):
                ev.n_excluded += 1
                continue
        kind = classify_request(m["req"])
        if times and kind is Kind.READ:
            d = m["date"]
            base = day_epoch.get(d)
            if base is None:
                base = day_epoch[d] = calendar.timegm(_time.strptime(d, "%Y-%m-%d"))
            h_, m_, s_ = m["time"].split(":")
            t = base + int(h_) * 3600 + int(m_) * 60 + float(s_)
            ev.n_reads += 1
            if prev_t is not None and (ev.max_gap_s is None or t - prev_t > ev.max_gap_s):
                ev.max_gap_s = max(t - prev_t, 0.0)
            prev_t = t
        if kind in (Kind.OPEN, Kind.READ):
            p = m["path"]
            hit = memo.get(p, memo)
            if hit is memo:
                rel = None if p in ("null", "undefined", "") else p
                relpath = lm.rel_of_path(rel)
                hit = memo[p] = (_side(None if relpath is None else lm.files[relpath], own_layout), relpath)
            side, relpath = hit
            _bump(ev, side, 1)
            ev.n_events += 1
            if relpath is not None:
                ev.files[relpath] = ev.files.get(relpath, 0) + 1
    return n, bad


def audit_evidence(lines_path: Path, record: dict | None, attempt_dir: str, lm: LayoutMap, own_layout: str, windows: list[tuple[str, str]] | None = None,
                   times: bool = False) -> Ev:
    """The run's audit lines, only when the sealed audit record stands behind them: it is the analysed attempt's, it is `observed` or `read_nothing`
    (not `not_observed`: its lines may be another run's or missing some), and the lines read now are the lines it counted (the live store can move after
    the seal). Lines of a record that does not stand are never counted, not even as partial evidence."""
    ev = Ev("audit")
    if not isinstance(record, dict):
        ev.reason = "no_audit_record"
        return ev
    v = record.get("verdict") or {}
    if record.get("attempt_dir") != attempt_dir:
        ev.reason = "audit_attempt_mismatch"
        return ev
    if v.get("class") not in ("observed", "read_nothing"):
        was = (record.get("exclusion") or {}).get("was") or {}
        if not (v.get("reason") == "foreign_lines" and windows and was.get("class") in ("observed", "read_nothing")):
            ev.reason = f"audit_not_observed:{v.get('reason') or 'unspecified'}"
            return ev
        # marked `foreign_lines` by the exclusion list and otherwise observed: it stands with the lines of the window left out
    if not Path(lines_path).is_file():
        ev.reason = "audit_lines_missing"
        return ev
    with gzip.open(lines_path, "rt", encoding="utf-8", errors="strict") as fh:
        n, bad = scan_audit(_iter_lines(fh), ev, lm, own_layout, windows, times)       # splitlines, as the frozen parser and extract's spill do: a line is what they count
    n_sealed = (record.get("lines") or {}).get("n")
    why = "audit_bad_lines" if bad else ("audit_changed_since_seal" if n_sealed is None or n != int(n_sealed) else None)
    if why:
        ev.reason = why
        ev.own = ev.other = ev.unmapped = ev.n_events = ev.n_excluded = ev.n_reads = 0
        ev.max_gap_s = None
        ev.files = {}
    return ev


# ---- the union ---------------------------------------------------------------------------------------------------------------------------
def combine(evs: list[Ev]) -> dict:
    """The run's `layout_read` over its sources. Events seen are real even when their source cannot stand (a lost gate log still shows what it holds),
    so a sibling read and an own read in any of them make `both`; otherwise a value needs one source that stands and no read it could not place."""
    usable = [e for e in evs if e.reason is None]
    own_seen, other_seen = any(e.own > 0 for e in evs), any(e.other > 0 for e in evs)
    reasons = [f"{e.source}:{e.reason}" for e in evs if e.reason is not None]
    unplaced = [e for e in usable if e.unmapped > 0]
    reasons += [f"{e.source}:unmapped" for e in unplaced]
    if own_seen and other_seen:
        value = BOTH
    elif not usable or unplaced:
        value = EMPTY
    elif other_seen:
        value = OTHER
    elif own_seen:
        value = OWN
    else:
        value = NONE
    return {"value": value, "reasons": reasons, "other_seen": other_seen,
            "source": "+".join(sorted(e.source for e in evs if e.reason is None or e.own or e.other))}


_WINDOW_MARGIN_S = 60.0              # beyond the audit's own attribution tolerance (`window.eps_s`): a window this far from a lease cannot hold one of its lines


def relevant_windows(windows: list[tuple[str, str]] | None, arec: dict | None) -> list[tuple[str, str]] | None:
    """The exclusion windows of the run's slot that can touch the run: those that overlap its lease widened by the attribution tolerance and a margin. A window further away holds none of
    the lease's lines, so leaving it out changes no evidence, and it must not change the run's cache key either (an exclusion for a slot would otherwise make every run that ever used
    that slot read again). A record with no lease keeps every window."""
    import calendar
    import time as _time
    if not windows:
        return None
    w = (arec or {}).get("window") if isinstance(arec, dict) else None
    if not isinstance(w, dict) or w.get("lease_start") is None or w.get("lease_end") is None:
        return windows
    m = float(w.get("eps_s") or 0.0) + _WINDOW_MARGIN_S
    lo, hi = float(w["lease_start"]) - m, float(w["lease_end"]) + m
    ep = lambda x: calendar.timegm(_time.strptime(x, "%Y-%m-%d %H:%M:%S"))        # noqa: E731
    return [(a, b) for a, b in windows if ep(b) + 1.0 >= lo and ep(a) <= hi] or None


_STATUS: dict = {"cache": "off"}


def collect(*, run_key: str, option: str, layout: str, provider: str, run_dir: Path, platform_record: dict | None,
            ids_by_provider: dict[str, dict[str, str]], lm: LayoutMap, audit_root: Path, exclusions: dict | None = None, cache=None) -> dict:
    """The run's sources, each read once: gate (T, T-unpaginated, D), perf (M, M+), audit (every option). With a `cache` (snapshot.layoutcache.EvidenceCache) a run whose sources, audit
    record, exclusion windows and the code that reads them are what they were when its evidence was stored is not read again."""
    attempt = Path(run_dir).name
    if option not in (*REST_OPTIONS, *MOUNT_OPTIONS):
        raise LayoutReadError(f"option {option!r}: no source is defined for it")
    arec = (platform_record or {}).get("audit")
    slot = (((arec or {}).get("window") or {}).get("slot")) if isinstance(arec, dict) else None
    windows = relevant_windows((exclusions or {}).get((provider, str(slot))) if slot is not None else None, arec)
    key = None
    if cache is not None:
        key = cache.key(option=option, layout=layout, provider=provider, run_key=run_key, run_dir=Path(run_dir), arec=arec, windows=windows)
        hit = cache.get(key, provider, run_key, attempt)
        if hit is not None:
            _STATUS["cache"] = "hit"
            return {**hit, "attempt": attempt, "arec": arec}
    if option in REST_OPTIONS:
        gate, perf = gate_evidence(run_dir, ids_by_provider.get(provider), lm, layout), None
    else:
        gate, perf = None, perf_evidence(run_dir, lm, layout)
    aud = audit_evidence(Path(audit_root) / provider / "runs" / run_key / attempt / "lines.log.gz", arec, attempt, lm, layout, windows, times=option == "M")
    out = {"gate": gate, "perf": perf, "audit": aud}
    if cache is not None:
        cache.put(key, provider, run_key, attempt, out)
        _STATUS["cache"] = "miss"
    return {**out, "attempt": attempt, "arec": arec}


def _base_row(columns, run_key, block, run, option, layout, provider, instance, model, seed, environment) -> dict:
    row = dict.fromkeys(columns, "")
    row.update(run_key=run_key, layout=layout, block=block, run=run, option=option, provider=provider or "", instance=instance, model=model, seed=seed,
               environment=environment)
    return row


def layout_row(base: dict, ev: dict) -> dict:
    """The row of layout_read.csv. The MAIN field is the same definition for every option (science, #34): gate bytes for T, T-unpaginated and D, and the audit lines
    for all of them, M and M+ included. M's performance-log bytes are beside it, in their own columns, and `layout_read_with_perf` is the union with them."""
    row = base
    main = [e for e in (ev["gate"], ev["audit"]) if e is not None]
    c = combine(main)
    row.update(layout_read=c["value"], source=c["source"], reason=";".join(c["reasons"]), other_seen=int(c["other_seen"]), attempt_dir=ev["attempt"])
    gate, perf, aud = ev["gate"], ev["perf"], ev["audit"]
    if gate is not None and gate.reason is None:
        row.update(bytes_own=gate.own, bytes_other=gate.other)
    if aud.reason is None:
        row.update(n_audit_own=aud.own, n_audit_other=aud.other, audit_layout_read=combine([aud])["value"], audit_lines_excluded=aud.n_excluded)
    if perf is not None:
        cw = combine(main + [perf])
        row.update(layout_read_with_perf=cw["value"], source_with_perf=cw["source"], reason_with_perf=";".join(cw["reasons"]), other_seen_with_perf=int(cw["other_seen"]))
        if perf.reason is None:
            row.update(bytes_own_perf=perf.own, bytes_other_perf=perf.other, perf_layout_read=combine([perf])["value"])
    else:
        row.update(layout_read_with_perf=c["value"], source_with_perf=c["source"], reason_with_perf=row["reason"], other_seen_with_perf=int(c["other_seen"]))
    return row


def bypass_row(base: dict, ev: dict | None, early: str | None = None) -> dict:
    """Provider audit lines of the run's slot user against the gate's: the files the slot user opened or read at the provider that the gate never served.

    A REST run (T, T-unpaginated, D) reaches the provider only through the gate, which logs every content request it lets through; so every file the audit log shows the
    slot user opening or reading is a file the gate log shows a content request for. A file the audit shows and the gate does not is a read that did not go through the gate:
    a BYPASS. `bypass_events` are the audit's opens and reads on such files; an open or read of a path no manifest holds (`audit_unmapped_events`) is unexplained too.
    Compared only when both logs stand (`status` says why not otherwise); a gate request of any method or status counts as served, so a request the provider failed on cannot
    look like a bypass. Reported, never a filter on anything."""
    row = base
    if early:
        row.update(status=early, reason=early)
        return row
    gate, aud = ev["gate"], ev["audit"]
    if gate is None:
        row.update(status="not_applicable", reason="no_gate_for_this_option")
        return row
    if gate.reason is not None:
        row.update(status="no_gate", reason=f"gate:{gate.reason}")
        return row
    if aud.reason is not None:
        row.update(status="no_audit", reason=f"audit:{aud.reason}")
        return row
    row.update(n_gate_requests=gate.n_events, n_gate_files=len(gate.files), n_audit_open_read=aud.n_events, n_audit_files=len(aud.files), gate_unmapped_requests=gate.files_unmapped, audit_lines_excluded=aud.n_excluded)
    if gate.files_unmapped:
        row.update(status="uncertain", reason="gate_request_for_a_file_no_manifest_holds")
        return row
    extra = sorted(set(aud.files) - set(gate.files))
    row.update(status="compared", bypass_files=len(extra), bypass_events=sum(aud.files[f] for f in extra), audit_unmapped_events=aud.unmapped,
               bypass_file_list=";".join(extra[:5]))
    row["nonzero"] = int(row["bypass_events"] > 0 or aud.unmapped > 0)
    return row


def stall_row(base: dict, ev: dict, kernel: dict, arec: dict | None) -> dict:
    """M's stall fields (science, #34 05:06Z): `max_read_gap_s`, the longest single gap between two read events, from the oneclient performance log (`perf`: FsLogic reads) when it
    stands and holds two reads, else from the run's audit lines (`audit`: remote_read lines, with the exclusion windows left out); `hung_task_lines`, the kernel's `blocked for more
    than` lines on the run's host inside its lease window. A value that cannot be had is empty with its reason, never 0: no source (`max_read_gap_source` is `none`), no log of the
    host, a journal that starts after the lease, a line with no readable stamp."""
    row = base
    perf, aud = ev["perf"], ev["audit"]
    if perf is not None and perf.reason is None and perf.gap_reason is None and perf.n_reads >= 2:
        row.update(max_read_gap_s=round(perf.max_gap_s, 3), max_read_gap_source="perf", n_read_events=perf.n_reads)
    elif aud.reason is None and aud.n_reads >= 2:
        row.update(max_read_gap_s=round(aud.max_gap_s, 3), max_read_gap_source="audit", n_read_events=aud.n_reads)
    else:
        why = lambda e, tag: f"{tag}:{e.reason or e.gap_reason or 'fewer_than_two_reads'}"       # noqa: E731
        row.update(max_read_gap_source="none", gap_reason=";".join(([why(perf, "perf")] if perf is not None else []) + [why(aud, "audit")]))
    if perf is not None and perf.reason is None and perf.max_dur_s is not None:
        row.update(max_read_duration_s=round(perf.max_dur_s, 3))
    win = (arec or {}).get("window") if isinstance(arec, dict) else None
    host = (arec or {}).get("host") if isinstance(arec, dict) else None
    if not isinstance(win, dict) or win.get("lease_start") is None or win.get("lease_end") is None or host is None:
        row.update(hung_reason="no_lease_window")
        row["stall_evidence"] = stall_evidence(row)
        return row
    t0, t1 = float(win["lease_start"]), float(win["lease_end"])
    row.update(host=host, lease_start=t0, lease_end=t1)
    k = kernel.get(kernel_log_name(base["provider"], host))
    if k is None:
        row.update(hung_reason="no_kernel_log")
    elif k["bad"]:
        row.update(hung_reason="kernel_log_stamp_unreadable")
    elif k["since"] is not None and t0 < k["since"]:
        row.update(hung_reason="journal_starts_after_the_lease")
    else:
        import bisect
        row.update(hung_task_lines=bisect.bisect_right(k["epochs"], t1) - bisect.bisect_left(k["epochs"], t0))
    row["stall_evidence"] = stall_evidence(row)
    return row


def stall_evidence(row: dict) -> str:
    """For a run with a gap of 5 minutes or more between reads: what shows that the gap was a stall and not the model's thinking (science, #34 07:02Z). `open_read`: a single read call of the run was
    open for 5 minutes or more at the FUSE level (the perf log's `Duration [us]`; a read, so a hang in a lookup or an open is not seen here); `hung_task`: the host's kernel logged a hung task in the
    run's lease window; `both`; `none`: both are known and neither shows it (the model thinking, a computation, or a hang the logs do not carry); `unknown`: nothing shows it and one of the two
    could not be had. Empty for a run with no gap of 5 minutes or more (or no gap measured)."""
    if row["max_read_gap_s"] == "" or float(row["max_read_gap_s"]) < STALL_GAP_S:
        return ""
    op = None if row["max_read_duration_s"] == "" else float(row["max_read_duration_s"]) >= OPEN_READ_S
    hg = None if row["hung_task_lines"] == "" else int(row["hung_task_lines"]) > 0
    if op and hg:
        return "both"
    if op:
        return "open_read"
    if hg:
        return "hung_task"
    return "none" if op is False and hg is False else "unknown"


def run_row(*, run_key: str, block: str, run: str, option: str, layout: str, provider: str | None, run_dir: Path | None, platform_record: dict | None,
            ids_by_provider: dict[str, dict[str, str]], lm: LayoutMap, audit_root: Path, instance: str = "", model: str = "", seed: str = "",
            environment: str = "", exclusions: dict | None = None, backend: str | None = None, slot: str | None = None, bytes_between_sites: int | None = None) -> dict:
    """One row of layout_read.csv. A run with no owner, no attempt directory or no source that stands is empty with its reasons."""
    return run_pair(run_key=run_key, block=block, run=run, option=option, layout=layout, provider=provider, run_dir=run_dir, platform_record=platform_record,
                    ids_by_provider=ids_by_provider, lm=lm, audit_root=audit_root, instance=instance, model=model, seed=seed, environment=environment, exclusions=exclusions, backend=backend, slot=slot, bytes_between_sites=bytes_between_sites)[0]


def run_pair(*, run_key: str, block: str, run: str, option: str, layout: str, provider: str | None, run_dir: Path | None, platform_record: dict | None,
             ids_by_provider: dict[str, dict[str, str]], lm: LayoutMap, audit_root: Path, instance: str = "", model: str = "", seed: str = "",
             environment: str = "", exclusions: dict | None = None, backend: str | None = None, slot: str | None = None, bytes_between_sites: int | None = None) -> tuple[dict, dict]:
    """(the row of layout_read.csv, the row of bypass.csv) of a run: its sources are read once."""
    return run_triple(run_key=run_key, block=block, run=run, option=option, layout=layout, provider=provider, run_dir=run_dir, platform_record=platform_record,
                      ids_by_provider=ids_by_provider, lm=lm, audit_root=audit_root, instance=instance, model=model, seed=seed, environment=environment,
                      exclusions=exclusions, backend=backend, slot=slot, bytes_between_sites=bytes_between_sites)[:2]


def run_triple(*, run_key: str, block: str, run: str, option: str, layout: str, provider: str | None, run_dir: Path | None, platform_record: dict | None,
               ids_by_provider: dict[str, dict[str, str]], lm: LayoutMap, audit_root: Path, instance: str = "", model: str = "", seed: str = "",
               environment: str = "", exclusions: dict | None = None, backend: str | None = None, slot: str | None = None, bytes_between_sites: int | None = None, kernel: dict | None = None,
               cache=None) -> tuple[dict, dict, dict | None]:
    """(the row of layout_read.csv, the row of bypass.csv, the row of m_stalls.csv: None for every option but M) of a run: its sources are read once."""
    args = (run_key, block, run, option, layout, provider, instance, model, seed, environment)
    row, brow = _base_row(COLUMNS, *args), _base_row(BYPASS_COLUMNS, *args)
    srow = _base_row(STALL_COLUMNS, *args) if option == "M" else None
    row["layout_read"] = row["layout_read_with_perf"] = EMPTY
    row["backend"], row["slot"] = backend or "", slot or ""                  # the winning attempt's run record, as the scored row carries them
    row["bytes_between_sites"] = _int_or_empty(bytes_between_sites)         # the scored row's: None (HPC: not measured) stays empty, never 0
    early = "no_owner" if provider is None else ("no_attempt_dir" if run_dir is None or not Path(run_dir).is_dir() else None)
    if option in REST_OPTIONS:
        row["gate_transfers_status"] = early or ""
    if early:
        row["reason"] = row["reason_with_perf"] = early
        if srow is not None:
            srow.update(max_read_gap_source="none", gap_reason=early, hung_reason=early)
        return row, bypass_row(brow, None, early), srow
    if option in REST_OPTIONS:
        gb, gs = gate_transfer_bytes(run_dir)
        row["bytes_to_sandbox"], row["gate_transfers_status"] = _int_or_empty(gb), gs
    ev = collect(run_key=run_key, option=option, layout=layout, provider=provider, run_dir=run_dir, platform_record=platform_record,
                 ids_by_provider=ids_by_provider, lm=lm, audit_root=audit_root, exclusions=exclusions, cache=cache)
    return layout_row(row, ev), bypass_row(brow, ev), (stall_row(srow, ev, kernel or {}, ev["arec"]) if srow is not None else None)


# ---- bytes at the gate and between the sites -------------------------------------------------------------------------------------------------
GATE_COLUMNS = ("run_key", "block", "run", "instance", "model", "seed", "option", "layout", "provider", "environment", "bytes_to_sandbox", "gate_transfers_status", "bytes_between_sites")
RELATION_COLUMNS = ("option", "layout", "vm_runs", "both_known", "between_sites_unknown", "to_sandbox_unknown", "sum_between_sites", "sum_to_sandbox", "ratio_of_sums", "ratio_median",
                    "ratio_min", "ratio_max", "equal_runs", "pearson_r")


def gate_transfer_bytes(run_dir: Path) -> tuple[int | None, str]:
    """`sandbox.gate_transfers.bytes_to_sandbox` of the run record: the content bytes the gate sent to the sandbox. Not read from the cache: a few KB per run. None, with the reason, when the
    record has none (`no_run_record`, `no_gate_transfers`, `unavailable`: the gate died, restarted or could not write, `not_recorded`); never 0 for an unknown."""
    try:
        rec = json.loads((Path(run_dir) / "run_record.json").read_text())
    except (OSError, ValueError):
        return None, "no_run_record"
    gt = (rec.get("sandbox") or {}).get("gate_transfers")
    if not isinstance(gt, dict):
        return None, "no_gate_transfers"
    if gt.get("unavailable"):
        return None, "unavailable"
    b = gt.get("bytes_to_sandbox")
    if isinstance(b, bool) or not isinstance(b, int):
        return None, "not_recorded"
    return b, "ok"


def _int_or_empty(v) -> int | str:
    return "" if v is None or v == "" else int(v)


def bytes_relation(rows: list[dict]) -> list[dict]:
    """On the VM runs of a gated option (T, T-unpaginated, D) where BOTH counts exist, how the bytes between the sites (the sidecar's counter, the study's H2 measure) and the bytes the gate sent to the
    sandbox relate, per option and layout. HPC runs have no bytes between sites and are not in it: the two columns are never mixed, and a run missing either count is counted apart, never as 0."""
    import statistics
    out = []
    for opt in REST_OPTIONS:
        for lay in ("S1", "S2"):
            g = [r for r in rows if r["option"] == opt and r["layout"] == lay and r["environment"] == "vm"]
            if not g:
                continue
            both = [(int(r["bytes_between_sites"]), int(r["bytes_to_sandbox"])) for r in g if r["bytes_between_sites"] != "" and r["bytes_to_sandbox"] != ""]
            ratios = [a / b for a, b in both if b > 0]
            r_ = ""
            if len(both) >= 3 and len({a for a, _ in both}) > 1 and len({b for _, b in both}) > 1:
                r_ = round(statistics.correlation([a for a, _ in both], [b for _, b in both]), 6)
            sa, sb = sum(a for a, _ in both), sum(b for _, b in both)
            out.append({"option": opt, "layout": lay, "vm_runs": len(g), "both_known": len(both),
                        "between_sites_unknown": sum(r["bytes_between_sites"] == "" for r in g), "to_sandbox_unknown": sum(r["bytes_to_sandbox"] == "" for r in g),
                        "sum_between_sites": sa if both else "", "sum_to_sandbox": sb if both else "", "ratio_of_sums": round(sa / sb, 6) if both and sb > 0 else "",
                        "ratio_median": round(statistics.median(ratios), 6) if ratios else "", "ratio_min": round(min(ratios), 6) if ratios else "",
                        "ratio_max": round(max(ratios), 6) if ratios else "", "equal_runs": sum(a == b for a, b in both), "pearson_r": r_})
    return out


# ---- backend shares ----------------------------------------------------------------------------------------------------------------------
def load_site_ba_slots(path: Path | None, override: list[str] | None = None) -> tuple[str, ...]:
    """The site_ba slots: `override` (the command line), else the lines of `path` (`frozen/site_ba-slots.txt`: one slot per line, `#` comments), else the default."""
    if override:
        return tuple(override)
    if path is not None and Path(path).is_file():
        return tuple(x.strip() for x in Path(path).read_text().splitlines() if x.strip() and not x.lstrip().startswith("#"))
    return SITE_BA_SLOTS


def backend_of(backend: str | None, slot: str | None, site_ba: tuple[str, ...]) -> str:
    """Where a run's MODEL ran, from its winning attempt's run record: `anthropic`, `site_b`, `site_ba` (an HPC slot in the site_ba list), `site_a` (any other HPC slot), or
    `unrecorded`. Not the environment the run's dispatcher ran in."""
    if backend in ("anthropic", "site_b"):
        return backend
    if backend == "hpc":
        return "site_ba" if slot in site_ba else "site_a"
    return "unrecorded"


def backend_shares(rows: list[dict], primary: tuple[str, ...], site_ba: tuple[str, ...]) -> list[dict]:
    """Per option x model across the cut: the runs by backend and by environment (VM or HPC: where the run's dispatcher ran) and each one's share of the (block group, option, model) cell.
    The block group is `primary` for the analysis's primary blocks (main and pagination: one analysis) and the block's own name for any other. Layouts are merged. Scored runs only."""
    cnt: Counter = Counter()
    for r in rows:
        grp = "primary" if r["block"] in primary else r["block"]
        cnt[(grp, r["option"], r["model"], backend_of(r["backend"] or None, r["slot"] or None, site_ba), r["environment"] or "unknown")] += 1
    cell: Counter = Counter()
    for (grp, opt, model, _, _), n in cnt.items():
        cell[(grp, opt, model)] += n
    return [{"block_group": g, "option": o, "model": m, "backend": b, "environment": e, "runs": n, "share": round(n / cell[(g, o, m)], 6)}
            for (g, o, m, b, e), n in sorted(cnt.items())]


# ---- the sealed inputs --------------------------------------------------------------------------------------------------------------------
def _jsonl(p: Path):
    with open(p) as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)


def _sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def base_dir(seal: Path) -> Path:
    """`out-coded` when it exists (the label the analysis and the H3 stage use), else `out`."""
    seal = Path(seal)
    return seal / ("out-coded" if (seal / "out-coded" / "pipeline" / "scored_rows.jsonl").is_file() else "out")


def run_string(r: dict) -> str:
    return f"{r['instance_id']}__{r['option']}__{r['layout']}__{r['model']}__s{r['seed']}"


def provider_ids(seal: Path, data_root: Path, index_roots: dict[str, str] | None, lm: LayoutMap) -> dict[str, dict[str, str]]:
    """`provider_ids_from` the seal's own `bmerge.json`."""
    return provider_ids_from(Path(seal) / "bmerge.json", data_root, index_roots, lm)


def provider_ids_from(bmerge_config: Path, data_root: Path, index_roots: dict[str, str] | None, lm: LayoutMap) -> dict[str, dict[str, str]]:
    """{provider: {file id: path}} from each owner's own index: site_g's is the data root's, a B provider's is the `index_root` of `bmerge.json`. Refused when an index
    lacks a file of a manifest, or a B provider's ids equal site_g's (it resolved to site_g: its runs would be mapped with site_g's ids)."""
    cfg = json.loads(Path(bmerge_config).read_text())["providers"]
    roots = {"site_g": str(data_root)} | {p: c["index_root"] for p, c in cfg.items() if c.get("index_root")} | dict(index_roots or {})
    out: dict[str, dict[str, str]] = {}
    for p, r in sorted(roots.items()):
        f = Path(r) / "layout" / "ids.json"
        if not f.is_file():
            raise LayoutReadError(f"no ids.json for provider {p}: {f}")
        out[p] = json.loads(f.read_text())
        missing = set(lm.files) - set(out[p].values())
        if missing:
            raise LayoutReadError(f"provider {p}'s ids lack {len(missing)} files of the manifests")
    site_g = out.get("site_g")
    for p, ids in out.items():
        if site_g is not None and p != "site_g" and set(ids) == set(site_g):
            raise LayoutReadError(f"provider {p}'s ids equal site_g's: its runs would be mapped with site_g's ids")
    return out


_WORK: dict = {}


def _init_work(ids, lm, audit_root, exclusions=None, kernel=None, cache=None) -> None:
    _WORK.update(ids=ids, lm=lm, audit_root=audit_root, exclusions=exclusions, kernel=kernel, cache=cache)


def _work(kw: dict) -> tuple[dict, dict, dict | None, str]:
    """One run's rows in a worker process: the provider ids, the layout map, the audit root and the cache are the worker's own (set once), not pickled per run. The last item is whether
    the run's evidence came from the cache (`hit`), was read and stored (`miss`) or no cache is in use (`off`)."""
    _STATUS["cache"] = "off"
    out = run_triple(ids_by_provider=_WORK["ids"], lm=_WORK["lm"], audit_root=_WORK["audit_root"], exclusions=_WORK["exclusions"], kernel=_WORK["kernel"], cache=_WORK["cache"], **kw)
    return (*out, _STATUS["cache"])


def _fill_one(kw: dict) -> str:
    """Reads (or finds) one attempt's evidence into the cache; `hit` or `miss`."""
    _STATUS["cache"] = "off"
    collect(ids_by_provider=_WORK["ids"], lm=_WORK["lm"], audit_root=_WORK["audit_root"], exclusions=_WORK["exclusions"], cache=_WORK["cache"], **kw)
    return _STATUS["cache"]


def provider_environments(table: Path | None = DEFAULT_PROVIDER_TABLE) -> dict[str, str]:
    """{provider: `vm` | `hpc`} from lane-snap's provider table (`lib-providers.sh`): a line `<provider> <host> [vm2|site_a]`; a `site_a` third column is HPC (site_a), every other listed
    provider is the run VMs. site_g (main's own store) is the run VMs and is not listed. No table is an empty map."""
    out: dict[str, str] = {}
    if table is not None and Path(table).is_file():
        for line in Path(table).read_text().splitlines():
            f = line.split()
            if f and not f[0].startswith("#"):
                out[f[0]] = "hpc" if len(f) > 2 and f[2] == "site_a" else "vm"
    return out


def environment_of(provider: str | None, envmap: dict[str, str]) -> str:
    """`vm`, `hpc`, or `unknown` for a provider the table does not name (and that is not site_g or an `icsa-site_a*` store): it is never taken for the VMs, so the unit it ran is
    counted and does not qualify for a within-environment table. No provider is empty."""
    if provider is None:
        return ""
    if provider in envmap:
        return envmap[provider]
    if provider.startswith("icsa-site_a"):
        return "hpc"
    return "vm" if provider == "site_g" else "unknown"


def build_all(seal: Path, *, lm: LayoutMap | None = None, data_root: Path = DEFAULT_DATA_ROOT, audit_root: Path = DEFAULT_AUDIT_ROOT,
               index_roots: dict[str, str] | None = None, envmap: dict[str, str] | None = None, jobs: int = 1, exclusions_path: Path | None = None, kernel_dir: Path | None = None, site_ba_slots: list[str] | None = None, cache_dir: Path | None = None) -> dict:
    """{rows, bypass, stalls, shares, meta}: the rows of layout_read.csv, bypass.csv, m_stalls.csv (M runs only) and backend_shares.csv for every scored run of the seal (the analysis's own rows: `out-coded`
    if it exists), and a meta record of the inputs. The host kernels' hung-task lines are read from `<seal>/frozen/kernel-hung/` unless `kernel_dir` says otherwise."""
    seal = Path(seal)
    lm = lm or LayoutMap.default()
    envmap = provider_environments() if envmap is None else envmap
    base = base_dir(seal)
    scored_p, infra_p = base / "pipeline" / "scored_rows.jsonl", base / "pipeline" / "infra.json"
    plat_p, prov_p = seal / "h3" / "platform_rows.jsonl", seal / "M" / "providers.json"
    for p in (scored_p, infra_p, plat_p, prov_p, seal / "bmerge.json"):
        if not p.is_file():
            raise LayoutReadError(f"{p} is missing: this stage needs the analysis, the merge and the H3 join of the seal")
    ids = provider_ids(seal, data_root, index_roots, lm)
    exc_p = Path(exclusions_path) if exclusions_path is not None else seal / "frozen" / "h3-exclusions.tsv"
    excl = load_exclusions(exc_p)
    kdir = Path(kernel_dir) if kernel_dir is not None else seal / "frozen" / "kernel-hung"
    try:
        year = int(json.loads((base / "SNAPSHOT.json").read_text())["t"][:4])
    except (OSError, ValueError, KeyError, TypeError):
        year = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).year
    kernel = load_kernel_logs(kdir, year)
    owner = json.loads(prov_p.read_text())["providers"]
    attempts = {(a["block"], a["key"]): a for a in json.loads(infra_p.read_text())["analysed_attempts"]}
    plat = {(d["block"], d["run"]): d["platform_record"] for d in _jsonl(plat_p)}
    items = []
    for r in _jsonl(scored_p):
        run = run_string(r["run"])
        block = r["block"]
        key = f"{block}__{run}"
        a = attempts.get((block, run))
        prov = owner.get(key)
        items.append(dict(run_key=key, block=block, run=run, option=str(r["run"]["option"]), layout=str(r["run"]["layout"]), provider=prov,
                          run_dir=Path(a["run_dir"]) if a else None, platform_record=plat.get((block, run)), instance=str(r["run"]["instance_id"]),
                          model=str(r["run"]["model"]), seed=str(r["run"]["seed"]), environment=environment_of(prov, envmap),
                          backend=r.get("backend"), slot=r.get("slot"), bytes_between_sites=r.get("bytes_between_sites")))
    cache = None
    if cache_dir is not None:
        from .layoutcache import EvidenceCache
        os.umask(0o077)
        Path(cache_dir).mkdir(mode=0o700, parents=True, exist_ok=True)
        cache = EvidenceCache(Path(cache_dir), lm, ids, audit_root)
    if jobs > 1 and len(items) > 1:       # the runs are independent and almost all I/O and parsing: a few processes, in order
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(jobs, initializer=_init_work, initargs=(ids, lm, audit_root, excl, kernel, cache)) as ex:
            pairs = list(ex.map(_work, items, chunksize=4))
    else:
        _init_work(ids, lm, audit_root, excl, kernel, cache)
        pairs = [_work(kw) for kw in items]
    rows, bypass, stalls = [p[0] for p in pairs], [p[1] for p in pairs], [p[2] for p in pairs if p[2] is not None]
    cache_status = Counter(p[3] for p in pairs)
    if len({x["run_key"] for x in rows}) != len(rows):
        raise LayoutReadError("a run is scored twice")
    meta = {"schema": SCHEMA, "base": base.name, "rows": len(rows), "audit_root": str(audit_root), "provider_environments": dict(sorted(envmap.items())),
            "inputs_sha256": {"scored_rows": _sha(scored_p), "infra": _sha(infra_p), "platform_rows": _sha(plat_p), "providers": _sha(prov_p),
                              **{f"ids:{p}": hashlib.sha256(json.dumps(v, sort_keys=True).encode()).hexdigest() for p, v in sorted(ids.items())}},
            "manifest_files": len(lm.files), "kernel_logs": {"dir": str(kdir) if kdir.is_dir() else None, "files": len(kernel)},
            "cache": {"dir": str(cache_dir) if cache_dir is not None else None, "hits": cache_status.get("hit", 0), "misses": cache_status.get("miss", 0)}, "exclusions": {"file": str(exc_p) if exc_p.is_file() else None, "windows": sum(len(v) for v in excl.values()),
                                                                "sha256": _sha(exc_p) if exc_p.is_file() else None}}
    site_ba = load_site_ba_slots(seal / "frozen" / "site_ba-slots.txt", site_ba_slots)
    from icsa.analysis import config as cfgmod
    primary = tuple(cfgmod.load()["blocks"]["primary"])
    meta["site_ba_slots"] = list(site_ba)
    return {"rows": rows, "bypass": bypass, "stalls": stalls, "shares": backend_shares(rows, primary, site_ba), "meta": meta}


def build_rows(seal: Path, **kw) -> tuple[list[dict], list[dict], dict]:
    """`build_all`'s rows of layout_read.csv and bypass.csv, and the meta record (m_stalls.csv's rows are `build_all(...)["stalls"]`)."""
    r = build_all(seal, **kw)
    return r["rows"], r["bypass"], r["meta"]


def write_atomic(path: Path, data: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(data)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def layout_dir(seal: Path) -> Path:
    d = Path(seal) / "layout"
    d.mkdir(mode=0o700, exist_ok=True)
    return d


def _csv(columns, rows, key="run_key", ignore: bool = False) -> str:
    import io
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=columns, lineterminator="\n", extrasaction="ignore" if ignore else "raise")
    w.writeheader()
    w.writerows(sorted(rows, key=lambda x: x[key]))
    return buf.getvalue()


def write_read(seal: Path, rows: list[dict], meta: dict, bypass: list[dict] | None = None, stalls: list[dict] | None = None, shares: list[dict] | None = None) -> dict:
    """layout_read.csv, bypass.csv (when given), their counts and the inputs' record, into <seal>/layout/. Returns what the terminal may show: totals, and whether a bypass
    happened (never which option or how many), and for M the totals science asked for (M runs, with a gap of 5 minutes or more, with a hung-task line)."""
    d = layout_dir(seal)
    out, bp = d / "layout_read.csv", d / "bypass.csv"
    sp, shp, gbp, brp = d / "m_stalls.csv", d / "backend_shares.csv", d / "gate_bytes.csv", d / "bytes_relation.csv"
    for p in [out, gbp, brp] + ([bp] if bypass is not None else []) + ([sp] if stalls is not None else []) + ([shp] if shares is not None else []):
        if p.exists():
            raise LayoutReadError(f"{p} exists: never overwritten (move it aside)")
    write_atomic(out, _csv(COLUMNS, rows))
    gated = [r for r in rows if r["option"] in REST_OPTIONS]
    write_atomic(gbp, _csv(GATE_COLUMNS, gated, ignore=True))                                             # per run, on both environments: the gate's bytes to the sandbox, beside the sidecar's bytes between sites
    import io as _io
    buf2 = _io.StringIO()
    w2 = csv.DictWriter(buf2, fieldnames=RELATION_COLUMNS, lineterminator="\n")
    w2.writeheader()
    w2.writerows(bytes_relation(rows))
    write_atomic(brp, buf2.getvalue())
    if not (d / "DEFINITIONS.md").exists():
        write_atomic(d / "DEFINITIONS.md", DEFINITIONS_MD)
    counts = {"by_layout_read": dict(Counter(r["layout_read"] or "empty" for r in rows)),
              "by_reason": dict(Counter(r["reason"] or "none" for r in rows)),
              "by_reason_item": dict(Counter(x for r in rows for x in r["reason"].split(";") if x)),
              "by_layout_read_with_perf": dict(Counter(r["layout_read_with_perf"] or "empty" for r in rows)),
              "other_seen_without_value": sum(1 for r in rows if r["other_seen"] == 1 and not r["layout_read"])}
    write_atomic(d / "counts_by_reason.json", json.dumps(counts, indent=1, sort_keys=True))
    write_atomic(d / "layout_read.meta.json", json.dumps(meta, indent=1, sort_keys=True))
    shown = {"rows": len(rows)}
    if (meta.get("cache") or {}).get("dir"):
        shown.update(cache_hits=meta["cache"]["hits"], cache_misses=meta["cache"]["misses"])
    if bypass is not None:
        write_atomic(bp, _csv(BYPASS_COLUMNS, bypass))
        compared = [r for r in bypass if r["status"] == "compared"]
        nonzero = [r for r in compared if r["nonzero"] == 1]
        write_atomic(d / "bypass_summary.json", json.dumps({"rows": len(bypass), "by_status": dict(Counter(r["status"] for r in bypass)), "compared": len(compared),
                                                            "nonzero_runs": len(nonzero), "it_happened": bool(nonzero)}, indent=1, sort_keys=True))
        shown.update(bypass_compared=len(compared), it_happened="yes" if nonzero else "no")
    if shares is not None:
        import io
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=SHARE_COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(shares)
        write_atomic(shp, buf.getvalue())
        shown.update(backend_shares_rows=len(shares))
    if stalls is not None:
        write_atomic(sp, _csv(STALL_COLUMNS, stalls))
        known_gap = [r for r in stalls if r["max_read_gap_s"] != ""]
        known_hung = [r for r in stalls if r["hung_task_lines"] != ""]
        t = {"m_runs": len(stalls), "gap_known": len(known_gap), "gap_unknown": len(stalls) - len(known_gap),
             "gap_ge_300s": sum(float(r["max_read_gap_s"]) >= STALL_GAP_S for r in known_gap), "hung_known": len(known_hung), "hung_unknown": len(stalls) - len(known_hung),
             "hung_task_runs": sum(int(r["hung_task_lines"]) > 0 for r in known_hung),
             "gap_ge_300s_with_stall_evidence": sum(r["stall_evidence"] in ("open_read", "hung_task", "both") for r in stalls),
             "gap_ge_300s_evidence_unknown": sum(r["stall_evidence"] == "unknown" for r in stalls),
             "by_stall_evidence": dict(Counter(r["stall_evidence"] or "no_gap_of_5_min" for r in stalls)),
             "by_gap_source": dict(Counter(r["max_read_gap_source"] for r in stalls)), "by_hung_reason": dict(Counter(r["hung_reason"] or "none" for r in stalls))}
        write_atomic(d / "m_stalls_summary.json", json.dumps(t, indent=1, sort_keys=True))
        shown.update(m_runs=t["m_runs"], m_gap_ge_5min=t["gap_ge_300s"], m_hung_task=t["hung_task_runs"], m_gap_unknown=t["gap_unknown"], m_hung_unknown=t["hung_unknown"],
                    m_gap_ge_5min_stalled=t["gap_ge_300s_with_stall_evidence"], m_gap_ge_5min_evidence_unknown=t["gap_ge_300s_evidence_unknown"])
    return shown


def load_rows(seal: Path) -> list[dict]:
    p = Path(seal) / "layout" / "layout_read.csv"
    if not p.is_file():
        raise LayoutReadError(f"{p} is missing: run `read` first")
    with open(p, newline="") as fh:
        return list(csv.DictReader(fh))


def drop_reason(row: dict, field: str = "layout_read") -> str | None:
    """Why the H3 reading and the own-layout-only tables leave a run out: it read the sibling (certainly, or by the value). `field`: `layout_read`, the main one, or
    `layout_read_with_perf`."""
    v = row[field]
    if v in H3_REASONS:
        return H3_REASONS[v]
    seen = row.get("other_seen" if field == "layout_read" else "other_seen_with_perf")
    if not v and str(seen) == "1":
        return H3_SIBLING_SEEN
    return None


# ---- the H3 reading beside the primary ---------------------------------------------------------------------------------------------------
def rewrite_platform(src: Path, dst: Path, drops: dict[tuple[str, str], str]) -> tuple[int, int]:
    """Copies the platform rows with both records of every dropped run rewritten to `not_observed:<reason>` (the measure counts `not_observed:<reason>` by
    itself); returns (rows rewritten, rows copied). The record keeps its other fields and the verdict it had under `layout_read_original_verdict`."""
    n_rewritten = n = 0
    out = []
    for d in _jsonl(src):
        n += 1
        why = drops.get((d["block"], d["run"]))
        if why is not None:
            for name in ("audit", "switched_on"):
                rec = d["platform_record"].get(name)
                if isinstance(rec, dict):
                    rec["layout_read_original_verdict"] = rec.get("verdict")
                    rec["verdict"] = {"class": "not_observed", "reason": why, "in_primary": False, "testable": False, "flags": [],
                                      "calibration_rule_class": "not_observed"}
            n_rewritten += 1
        out.append(json.dumps(d, sort_keys=True))
    write_atomic(dst, "".join(x + "\n" for x in out))
    return n_rewritten, n


def h3_side(seal: Path, *, tree: Path, pin: Path = DEFAULT_PIN, scored: Path | None = None, python: str = sys.executable, field: str = "layout_read") -> dict:
    """The H3 measure on a copy of the platform rows in which every run that read the sibling is `not_observed` (not testable), counted by reason. The PINNED
    measure runs unchanged (same tree, pin and `--scored` file as the primary); the primary's output is not touched."""
    seal, tree = Path(seal), Path(tree)
    rows = load_rows(seal)
    src = seal / "h3" / "platform_rows.jsonl"
    if not src.is_file():
        raise LayoutReadError(f"{src} is missing")
    if scored is None:
        info = seal / "h3" / "measure" / "label_source.json"
        name = json.loads(info.read_text())["scored_rows_file"] if info.is_file() else None
        scored = seal / "h3" / name if name and (seal / "h3" / name).is_file() else base_dir(seal) / "pipeline" / "scored_rows.jsonl"
    out = layout_dir(seal) / "h3-own"
    if out.exists():
        raise LayoutReadError(f"{out} exists: never overwritten (move it aside)")
    out.mkdir(mode=0o700)
    drops = {(r["block"], r["run"]): w for r in rows if (w := drop_reason(r, field))}
    plat_keys = {(d["block"], d["run"]) for d in _jsonl(src)}
    expected = len(set(drops) & plat_keys)
    rewritten, copied = rewrite_platform(src, out / "platform_rows.jsonl", drops)
    if rewritten != expected:
        raise LayoutReadError("the platform rows rewritten are not the runs layout_read.csv names that have a platform row: the keys of the two do not match")
    env = dict(os.environ, PYTHONPATH=str(tree), PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run([python, "-m", "icsa.faults.mainaudit", "measure", "--pin", str(pin), "--scored", str(scored), "--platform", str(out / "platform_rows.jsonl"),
                        "--out", str(out / "measure")], cwd=tree, env=env, capture_output=True, text=True)
    write_atomic(out / "measure.out", r.stdout)
    write_atomic(out / "measure.err", r.stderr)
    info = {"rewritten_platform_rows": rewritten, "platform_rows": copied, "dropped_runs": len(drops), "dropped_without_platform_row": len(drops) - expected,
            "measure_rc": r.returncode, "scored_rows": str(scored), "pin": str(pin), "tree": str(tree), "field": field}
    write_atomic(out / "h3_own.json", json.dumps(info, indent=1, sort_keys=True))
    return info


# ---- the command --------------------------------------------------------------------------------------------------------------------------
OWN_ARGS = ("variants", "config", "h3_table", "overhead", "fidelity_rows", "parallel")


def own_argv(ns) -> list[str]:
    """The arguments `snapshot.layoutown` takes, as given; `--field` is shared with the H3 step and passed on when it is not the default."""
    return [x for k in OWN_ARGS if getattr(ns, k) for x in ("--" + k.replace("_", "-"), getattr(ns, k))] + (["--field", ns.field] if ns.field != "layout_read" else [])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m snapshot.layoutread", description=__doc__.split("\n\n")[0])
    ap.add_argument("step", choices=["read", "h3", "own", "all"])
    ap.add_argument("seal", type=Path)
    ap.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT, help="site_g's index is <data root>/layout")
    ap.add_argument("--audit-root", type=Path, default=DEFAULT_AUDIT_ROOT, help="the audit stores, one directory per provider")
    ap.add_argument("--index-root", action="append", default=[], metavar="PROVIDER=DIR", help="a provider's index root, over bmerge.json's")
    ap.add_argument("--tree", type=Path, help="the code tree the H3 stage runs from (default: the tree this process runs from)")
    ap.add_argument("--pin", type=Path, default=DEFAULT_PIN)
    ap.add_argument("--scored", type=Path, help="h3: the scored rows the primary measure took (default: from h3/measure/label_source.json)")
    ap.add_argument("--site_ba-slots", help="read: comma list of the site_ba model slots (default: frozen/site_ba-slots.txt, else gemma-107)")
    ap.add_argument("--cache", type=Path, help="read: the per-run evidence cache (snapshot.layoutcache): a run found in it is not read again, one not found is read and stored")
    ap.add_argument("--kernel-dir", type=Path, help="read: the host kernels' hung-task logs (default <seal>/frozen/kernel-hung)")
    ap.add_argument("--jobs", type=int, default=1, help="read: worker processes (the runs are independent)")
    ap.add_argument("--providers-table", type=Path, default=DEFAULT_PROVIDER_TABLE, help="read: lane-snap's provider table; a `site_a` third column is HPC, any other listed provider and site_g the run VMs, an unlisted provider unknown")
    ap.add_argument("--field", choices=["layout_read", "layout_read_with_perf"], default="layout_read", help="h3: which value decides (the main one by default)")
    for name in OWN_ARGS:       # `own` only: handed to snapshot.layoutown as it takes them
        ap.add_argument("--" + name.replace("_", "-"), help=argparse.SUPPRESS)
    ns = ap.parse_args(argv)
    extra = own_argv(ns)
    try:
        seal = ns.seal.resolve()
        if not (seal / "SNAPSHOT.json").is_file() and not (seal / "out").is_dir():
            raise LayoutReadError(f"{seal} is not a seal")
        if ns.step in ("read", "all"):
            built = build_all(seal, data_root=ns.data_root, audit_root=ns.audit_root, index_roots=dict(x.split("=", 1) for x in ns.index_root),
                              envmap=provider_environments(ns.providers_table), jobs=ns.jobs, kernel_dir=ns.kernel_dir, cache_dir=ns.cache,
                              site_ba_slots=[x for x in (ns.site_ba_slots or "").split(",") if x])
            shown = write_read(seal, built["rows"], built["meta"], built["bypass"], built["stalls"], built["shares"])
            print("layoutread read " + " ".join(f"{k}={v}" for k, v in shown.items()))
        if ns.step in ("h3", "all"):
            import icsa
            tree = ns.tree or Path(icsa.__file__).resolve().parents[1]
            info = h3_side(seal, tree=tree, pin=ns.pin, scored=ns.scored, field=ns.field)
            print(f"layoutread h3 platform_rows={info['platform_rows']} measure_rc={info['measure_rc']}")      # how many runs were left out is a result: it stays in h3_own.json
            if info["measure_rc"] != 0:
                return 1
        if ns.step in ("own", "all"):
            from . import layoutown
            info = layoutown.own_only(seal, extra)
            print(f"layoutread own variants={len(info['variants'])} beside_tables={info['beside_tables']}" + (f" bytes_units_qualifying={info['bytes_units_qualifying']}" if "bytes-measured" in info["variants"] else ""))       # the runs and units left out are results: they stay in the sealed files
    except LayoutReadError as e:
        print(f"layoutread refused: {e}", file=sys.stderr)
        return 2
    except Exception as e:      # noqa: BLE001 -- the detail never goes to the terminal: it could hold a value of the seal
        print(f"layoutread FAILED {type(e).__name__}", file=sys.stderr)
        try:
            write_atomic(layout_dir(ns.seal.resolve()) / f"error.{ns.step}.txt", repr(e))
        except Exception:   # noqa: BLE001
            pass
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
