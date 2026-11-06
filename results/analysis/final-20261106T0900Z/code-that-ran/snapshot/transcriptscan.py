"""A sealed scan of the full transcripts of every S1 run, five booleans per run (science, #34 22:29Z, for the final).

    python -m snapshot.transcriptscan fill  --merged-root M --cache DIR [--jobs N] [--stop-by ISO] [--pause-file F] [--limit N]    # ahead of time, under nice/ionice/memcap
    python -m snapshot.transcriptscan stage <seal> --cache DIR [--budget-s N] [--seed S]                                          # at the freeze: joins the cache to the cut

The five booleans of a run (an attempt's `transcript.json` and `code_cells.json`; the S1 runs of every option):
  b1  the run called the dataset-metadata tool (`get_file_metadata`) on the S1 root (`.../s1z`) and got back its file count (`json.files.count`, a whole number) in the tool's result;
  b2  its TEXT (the assistant's messages and its reasoning) says the listing is capped, truncated or incomplete (the 1,000-entry cap);
  b3  its text relates the listing to the metadata's count, or to the number of days;
  b4  its CODE builds file names from dates rather than taking them from the listing;
  b5  its code compares a count of files with an expected count.
Regex only; every pattern is written to the output (`transcript_scan_patterns.csv`: boolean, name, where it is applied, the expression). "Text" is what the model wrote (message content, `reasoning`,
`_reasoning`, `reasoning_content`, never a tool result: a tool's own wording is not the run's); "code" is the `code` of every `python` call in the transcript and every cell of `code_cells.json`; a
boolean is true if ANY of its patterns matches ANY piece. Matching is by sentence (text) or by line and cell (code), case-insensitive.

Output (sealed, `<seal>/layout/side/`, stamped like the snapshot's tables): `transcript_scan_runs.csv` (a row per scanned run: its booleans, the pattern names that fired, the recovered flag),
`transcript_scan_counts.csv` (per option x layout, and per option x layout x model, each split by `recovered_from_truncated_listing`: yes / no / unknown), `transcript_scan_quotes.csv` (10 seeded
runs per option, among the runs with at least one boolean true, with the matching sentence or line of each true boolean, at most 200 characters), `transcript_scan_patterns.csv` and
`transcript_scan.json` (the account). Failing soft: an exception leaves `transcript_scan.FAILED.txt` with its class only, and the step ends 0.

The cache is a private (mode 700) directory of one file per run and attempt, keyed by the run key, the attempt directory, the two source files' (size, mtime) and the version of the patterns and
code; an entry is used only on an exact match. It holds the booleans AND the matching sentences (quotes), so it is as sealed as the seal; nothing in it is ever printed. Terminal output of this
module: counts of rows, runs, seconds and the patterns' NAMES, never a value, a quote or a split."""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import argparse         # noqa: E402
import csv              # noqa: E402
import datetime as dt   # noqa: E402
import hashlib          # noqa: E402
import json             # noqa: E402
import os               # noqa: E402
import random           # noqa: E402
import re               # noqa: E402
import tempfile         # noqa: E402
import time             # noqa: E402
from collections import Counter  # noqa: E402
from pathlib import Path    # noqa: E402

from . import layoutread as L   # noqa: E402

FORMAT = "transcript-scan/1"
BOOLEANS = ("b1_metadata_count", "b2_listing_capped", "b3_listing_vs_count_or_days", "b4_names_from_dates", "b5_count_vs_expected")
QUOTE_MAX = 200
PER_OPTION = 10
META_TOOL = "get_file_metadata"
LISTING = r"(?:listing|list(?:ed|s|ing)?|entries|children|directory|dir\b|\bls\b|files? returned|returned|results)"
SENT_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")


def _rx(s: str) -> "re.Pattern[str]":
    return re.compile(s, re.I)


# name -> (boolean, where, expression). TEXT patterns are matched per sentence; CODE patterns per line, with `cell` ones needing a second expression in the same cell (all|any of them as noted).
TEXT = {
    "p2_capped_word": (BOOLEANS[1], "text/sentence", rf"\A(?=.*\b(?:capped|truncated|truncation|truncates|incomplete|clipped|cut off)\b)(?=.*{LISTING})"),
    "p2_1000_cap": (BOOLEANS[1], "text/sentence", r"\b(?:first|only|max(?:imum)?|up to|at most|limit(?:ed)?(?: to| of)?|cap(?:ped)?(?: at| of| to)?)\s+(?:of\s+)?1[,_ ]?000\b|"
                                                  r"\b1[,_ ]?000[- ](?:entry|entries|item|items|file|files|result|results|child|children)\b|\b1[,_ ]?000\s+(?:entries|items|results|children|names)\b"),
    "p3_listing_and_metadata_count": (BOOLEANS[2], "text/sentence", rf"\A(?=.*{LISTING})(?=.*(?:\bmetadata\b|files\.count|files/count|\bfile count\b|\bfiles count\b|\b15[,_ ]?340\b))"),
    "p3_listing_and_days": (BOOLEANS[2], "text/sentence", rf"\A(?=.*{LISTING})(?=.*(?:\bnumber of days\b|\bdays? (?:count|in|between|of|since)\b|\b\d[\d,]*\s+days\b|\bdaily files\b|\bhow many days\b|\bexpected (?:number|count|days|files)\b))"),
}
DATES = r"(?:date|datetime|timedelta|strftime|strptime|%Y|fromordinal|toordinal|isoformat|\bday\b|\bdays\b)"
CODE = {
    "p4_fstring_sst": (BOOLEANS[3], "code/line+cell", r"\bf[\"']sst_\{", DATES),
    "p4_percent_sst": (BOOLEANS[3], "code/line", r"sst_%Y|sst_%[dmjy]", None),
    "p4_strftime_sst": (BOOLEANS[3], "code/line", r"strftime\(\s*[\"'][^\"']*sst_", None),
    "p4_concat_sst": (BOOLEANS[3], "code/line+cell", r"[\"']sst_[\"']\s*\+|\+\s*[\"']\.nc[\"']|sst_[^\"'\n]*[\"']\s*%\s*\(?\w|sst_\{[^}]*\}[^\n]*\.format|[\"']sst_\{[^}\n]*\}[^\n]*[\"']\s*\.format", DATES),
    "p5_len_compare": (BOOLEANS[4], "code/line", r"\blen\(\s*[^()\n]*(?:file|list|entr|child|name|path|item|\bls\b|day|sst|\.nc|listing)[^()\n]*\)\s*(?:==|!=|<=|>=|<|>)\s*[\w.\[\]'\"]+"),
    "p5_len_compare_reverse": (BOOLEANS[4], "code/line", r"[\w.\[\]'\"]+\s*(?:==|!=|<=|>=|<|>)\s*len\(\s*[^()\n]*(?:file|list|entr|child|name|path|item|\bls\b|day|sst|\.nc|listing)[^()\n]*\)"),
    "p5_assert_len": (BOOLEANS[4], "code/line", r"\bassert\s+len\("),
    "p5_expected_count": (BOOLEANS[4], "code/line+cell", r"\bexpected[_ ]?(?:count|files|n|number|total|days|len|size)\w*\b|\bn_expected\b|\bexpected\s*=", r"\blen\("),
}


CODE = {n: (v + (None,) if len(v) == 3 else v) for n, v in CODE.items()}                 # (boolean, where, expression, second expression needed in the same cell or None)


def pattern_rows() -> list[dict]:
    rows = [{"boolean": BOOLEANS[0], "pattern": "p1_metadata_tool_on_s1_root", "where": "tool call + its result",
             "expression": f"a call of `{META_TOOL}` whose `file_id_or_path` (trailing slashes removed) ends with `/s1z` or is `s1z`, whose tool result is JSON holding `json.files.count` as a whole number"}]
    rows += [{"boolean": b, "pattern": n, "where": w, "expression": e} for n, (b, w, e) in TEXT.items()]
    rows += [{"boolean": b, "pattern": n, "where": w, "expression": e + (f"   [and, in the same cell: {c}]" if c else "")} for n, (b, w, e, c) in CODE.items()]
    return rows


def version() -> str:
    """The version of the patterns and of the code that applies them: another one is another cache key."""
    import inspect
    src = json.dumps([pattern_rows(), FORMAT, BOOLEANS, QUOTE_MAX], sort_keys=True) + inspect.getsource(scan_transcript) + json.dumps(GATE, sort_keys=True) + json.dumps({k: v.pattern for k, v in FOCUS.items()}, sort_keys=True) + inspect.getsource(_sentences) + inspect.getsource(_clip) + inspect.getsource(_texts)
    return hashlib.sha256(src.encode()).hexdigest()[:16]


# Where in a sentence a quote is centred (the expressions of the conjunction patterns match zero-width at the start; the quote must show the words that made them fire).
FOCUS = {"p2_capped_word": _rx(r"\b(?:capped|truncated|truncation|truncates|incomplete|clipped|cut off)\b"),
         "p3_listing_and_metadata_count": _rx(r"\bmetadata\b|files\.count|files/count|\bfile count\b|\bfiles count\b|\b15[,_ ]?340\b"),
         "p3_listing_and_days": _rx(r"\bnumber of days\b|\bdays? (?:count|in|between|of|since)\b|\b\d[\d,]*\s+days\b|\bdaily files\b|\bhow many days\b|\bexpected (?:number|count|days|files)\b")}
_TEXT_RX = {n: (b, _rx(e)) for n, (b, w, e) in TEXT.items()}
_CODE_RX = {n: (b, _rx(e), _rx(c) if c else None) for n, (b, w, e, c) in CODE.items()}
# A cheap test run before each expression (speed only: a line or sentence with none of these substrings, lower-cased, cannot match its expression; a test pins that every pattern is covered).
GATE = {"p2_capped_word": ("cap", "trunc", "incomplete", "clipped", "cut off"), "p2_1000_cap": ("000",),
        "p3_listing_and_metadata_count": ("metadata", "files.count", "files/count", "file count", "files count", "340"),
        "p3_listing_and_days": ("day", "daily", "expected"),
        "p4_fstring_sst": ("sst_",), "p4_percent_sst": ("sst_",), "p4_strftime_sst": ("sst_",), "p4_concat_sst": ("sst_", ".nc"),
        "p5_len_compare": ("len(",), "p5_len_compare_reverse": ("len(",), "p5_assert_len": ("assert",), "p5_expected_count": ("expected",)}


# ---- reading one transcript -------------------------------------------------------------------------------------------------------------------
def _strings(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, list):
        for y in x:
            yield from _strings(y)
    elif isinstance(x, dict):
        for k in ("text", "content"):
            if k in x:
                yield from _strings(x[k])


def _texts(t: dict) -> list[str]:
    """What the model wrote: the assistant messages' content and reasoning fields, and the transcript's own `reasoning`. Never a tool result."""
    out = []
    for m in t.get("system_and_messages") or []:
        if isinstance(m, dict) and m.get("role") == "assistant":
            for k in ("content", "_reasoning", "reasoning_content", "reasoning"):
                if k in m:
                    out += [s for s in _strings(m[k]) if s.strip()]
    if "reasoning" in t:
        out += [s for s in _strings(t["reasoning"]) if s.strip()]
    return out


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in SENT_SPLIT.split(text) if s.strip()]


def _clip(s: str, start: int = 0) -> str:
    """The sentence or line at most QUOTE_MAX characters, the window starting a little before `start` (the matched word) so that the match is in it."""
    s = " ".join(s.split())
    if len(s) <= QUOTE_MAX:
        return s
    a = max(0, min(start - 60, len(s) - QUOTE_MAX))
    return s[a:a + QUOTE_MAX]


def _norm_path(p) -> str:
    return str(p or "").strip().rstrip("/")


def _is_s1_root(p) -> bool:
    n = _norm_path(p)
    return n == "s1z" or n.endswith("/s1z")


def _files_count(content):
    try:
        j = json.loads(content) if isinstance(content, str) else content
    except ValueError:
        return None
    if isinstance(j, dict) and isinstance(j.get("json"), str):
        try:
            j = {**j, "json": json.loads(j["json"])}
        except ValueError:
            return None
    try:
        n = j["json"]["files"]["count"]
    except (KeyError, TypeError):
        return None
    return n if isinstance(n, int) and not isinstance(n, bool) else None


def scan_transcript(transcript: dict, code_cells: list | None) -> dict:
    """{booleans: {name: bool}, patterns: [names that fired], quotes: {boolean: [pattern, quote]}, count_seen: int|None}. A transcript with no messages is scanned as empty (all False)."""
    msgs = [m for m in (transcript.get("system_and_messages") or []) if isinstance(m, dict)]
    calls = {}
    codes: list[str] = []
    for m in msgs:
        if m.get("role") != "assistant":
            continue
        for tc in m.get("tool_calls") or []:
            f = tc.get("function") or {}
            try:
                args = json.loads(f.get("arguments") or "{}")
            except (ValueError, TypeError):
                args = {}
            if not isinstance(args, dict):
                args = {}
            if f.get("name") == "python" and isinstance(args.get("code"), str):
                codes.append(args["code"])
            elif f.get("name") == META_TOOL:
                calls[tc.get("id")] = args
    for cell in code_cells or []:
        if isinstance(cell, dict) and isinstance(cell.get("code"), str):
            codes.append(cell["code"])
    b = dict.fromkeys(BOOLEANS, False)
    fired: list[str] = []
    quotes: dict[str, list[str]] = {}
    count_seen = None
    for m in msgs:                                                            # b1: the metadata tool on the S1 root and its result's file count
        if m.get("role") == "tool" and m.get("tool_call_id") in calls and _is_s1_root(calls[m["tool_call_id"]].get("file_id_or_path")):
            n = _files_count(m.get("content"))
            if n is not None:
                b[BOOLEANS[0]], count_seen = True, n
                if "p1_metadata_tool_on_s1_root" not in fired:
                    fired.append("p1_metadata_tool_on_s1_root")
                quotes.setdefault(BOOLEANS[0], ["p1_metadata_tool_on_s1_root", _clip(f"{META_TOOL}({_norm_path(calls[m['tool_call_id']].get('file_id_or_path'))}) -> json.files.count = {n}")])
    for text in _texts(transcript):                                           # b2, b3: sentence by sentence
        for s in _sentences(text):
            low = s.lower()
            for name, (bool_, rx) in _TEXT_RX.items():
                if not any(g in low for g in GATE[name]):
                    continue
                mt = rx.search(s)
                if mt:
                    b[bool_] = True
                    if name not in fired:
                        fired.append(name)
                    focus = FOCUS[name].search(s) if name in FOCUS else None
                    quotes.setdefault(bool_, [name, _clip(s, focus.start() if focus else mt.start())])
    for code in codes:                                                        # b4, b5: line by line, the cell for the second expression
        lines = code.splitlines()
        for name, (bool_, rx, need) in _CODE_RX.items():
            if need is not None and not need.search(code):
                continue
            gate = GATE[name]
            for ln in lines:
                low = ln.lower()
                if not any(g in low for g in gate):
                    continue
                mt = rx.search(ln)
                if mt:
                    b[bool_] = True
                    if name not in fired:
                        fired.append(name)
                    quotes.setdefault(bool_, [name, _clip(ln.strip(), mt.start())])
                    break
    return {"booleans": b, "patterns": sorted(fired), "quotes": quotes, "count_seen": count_seen}


def scan_run_dir(run_dir) -> dict:
    d = Path(run_dir)
    t = json.loads((d / "transcript.json").read_text())
    cells = None
    cp = d / "code_cells.json"
    if cp.is_file():
        try:
            cells = json.loads(cp.read_text())
        except ValueError:
            cells = None
    return scan_transcript(t if isinstance(t, dict) else {}, cells if isinstance(cells, list) else None)


# ---- the cache ------------------------------------------------------------------------------------------------------------------------------
def _stat(p: Path):
    try:
        st = os.stat(p)
    except OSError:
        return None
    return [st.st_size, st.st_mtime_ns]


class ScanCache:
    """One JSON file per run and attempt under `root/<block__run key>/<attempt>.json`, mode 600 in directories of mode 700; used only on an exact key (version, sources' size and mtime)."""

    def __init__(self, root: Path):
        self.root, self.version = Path(root), version()

    def _path(self, block: str, run_key: str, attempt: str) -> Path:
        return self.root / f"{block}__{run_key}" / f"{attempt}.json"

    def _key(self, run_dir: Path) -> dict:
        return {"version": self.version, "transcript": _stat(run_dir / "transcript.json"), "code_cells": _stat(run_dir / "code_cells.json")}

    def get(self, block: str, run_key: str, run_dir: Path) -> dict | None:
        try:
            d = json.loads(self._path(block, run_key, Path(run_dir).name).read_text())
        except (OSError, ValueError):
            return None
        if d.get("format") != FORMAT or d.get("key") != self._key(Path(run_dir)) or d["key"]["transcript"] is None:
            return None
        return d["result"]

    def put(self, block: str, run_key: str, run_dir: Path, result: dict) -> None:
        p = self._path(block, run_key, Path(run_dir).name)
        for d in (self.root, p.parent):
            d.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=p.parent, prefix=".tmp-")
        with os.fdopen(fd, "w") as fh:
            json.dump({"format": FORMAT, "key": self._key(Path(run_dir)), "block": block, "run_key": run_key, "attempt": Path(run_dir).name, "result": result}, fh)
        os.chmod(tmp, 0o600)
        os.replace(tmp, p)

    def lookup_or_scan(self, block: str, run_key: str, run_dir) -> tuple[dict | None, str]:
        """(result, 'hit' | 'miss' | 'unreadable'): a miss is scanned and stored; a run dir with no readable transcript is 'unreadable' (None)."""
        hit = self.get(block, run_key, Path(run_dir))
        if hit is not None:
            return hit, "hit"
        try:
            r = scan_run_dir(run_dir)
        except (OSError, ValueError):
            return None, "unreadable"
        self.put(block, run_key, Path(run_dir), r)
        return r, "miss"


# ---- ahead of time: fill ------------------------------------------------------------------------------------------------------------------
def fill(merged_root: Path, cache_dir: Path, *, stop_by: float | None = None, pause_file: Path | None = None, limit: int | None = None, jobs: int = 1,
         now=time.time, sleep=time.sleep) -> dict:
    """Scans every `done` S1 attempt of a merged store into the cache (a store's `state.sqlite` and its `runs.block`). Between runs it waits while `pause_file` exists and stops at `stop_by`
    (epoch seconds) or after `limit` runs. Counts only."""
    from .layoutcache import attempts_of
    cache = ScanCache(cache_dir)
    todo = [a for a in attempts_of(Path(merged_root)) if a["layout"] == "S1" and Path(a["run_dir"]).is_dir()]
    c = Counter()
    for a in todo:
        if limit is not None and c["hit"] + c["miss"] + c["unreadable"] >= limit:
            c["stopped_limit"] = 1
            break
        while pause_file is not None and Path(pause_file).exists():
            if stop_by is not None and now() >= stop_by:
                break
            sleep(30)
        if stop_by is not None and now() >= stop_by:
            c["stopped_time"] = 1
            break
        key = a["run_key"].split("__", 1)[1] if a["run_key"].startswith(a["block"] + "__") else a["run_key"]
        _, how = cache.lookup_or_scan(a["block"], key, a["run_dir"])
        c[how] += 1
    return {"s1_attempts": len(todo), **{k: c[k] for k in ("hit", "miss", "unreadable")}, "stopped": "time" if c["stopped_time"] else "limit" if c["stopped_limit"] else ""}


# ---- at the freeze: stage ---------------------------------------------------------------------------------------------------------------------
def _cut(seal: Path) -> tuple[Path, list[dict]]:
    """The cut's S1 scored runs: [{block, key, option, layout, model, run_dir}], and the pipeline directory they came from."""
    base = L.base_dir(seal)
    infra = json.loads((base / "pipeline" / "infra.json").read_text())["analysed_attempts"]
    dirs = {(a["block"], a["key"]): a["run_dir"] for a in infra}
    rows = []
    for ln in (base / "pipeline" / "scored_rows.jsonl").read_text().splitlines():
        r = json.loads(ln)
        if r["run"]["layout"] != "S1":
            continue
        key = f'{r["run"]["instance_id"]}__{r["run"]["option"]}__{r["run"]["layout"]}__{r["run"]["model"]}__s{r["run"]["seed"]}'
        rows.append({"block": r["block"], "key": key, "option": r["run"]["option"], "layout": "S1", "model": r["run"]["model"], "run_dir": dirs.get((r["block"], key))})
    return base, rows


def _recovered(base: Path) -> dict:
    p = base / "pipeline" / "cause_flags.csv"
    out: dict = {}
    if not p.is_file():
        return out
    with open(p, newline="") as fh:
        for r in csv.DictReader(fh):
            v = (r.get("recovered_from_truncated_listing") or "").strip().lower()
            out[(r["block"], r["run_key"])] = "yes" if v in ("true", "1", "yes") else "no" if v in ("false", "0", "no") else "unknown"
    return out


def stage(seal: Path, cache_dir: Path | None, *, budget_s: float = 900.0, seed: int = 20271105, snap: dict | None = None, now=time.time) -> dict:
    """Joins the cache to the cut and writes the tables. A run whose entry is missing is scanned now while the budget lasts, else counted as not scanned (never as false)."""
    from . import stamp
    d = L.layout_dir(seal) / "side"
    if (d / "transcript_scan_counts.csv").exists():
        raise L.LayoutReadError(f"{d / 'transcript_scan_counts.csv'} exists: never overwritten (move it aside)")
    base, runs = _cut(Path(seal))
    snap = snap or json.loads((base / "SNAPSHOT.json").read_text())
    rec = _recovered(base)
    tmpcache = None
    if cache_dir is None:
        tmpcache = tempfile.TemporaryDirectory()
        cache = ScanCache(Path(tmpcache.name))
    else:
        cache = ScanCache(cache_dir)
    t0 = now()
    acc: Counter = Counter()
    out = []
    for r in runs:
        res, how = None, "no_run_dir"
        if r["run_dir"]:
            hit = cache.get(r["block"], r["key"], Path(r["run_dir"]))
            if hit is not None:
                res, how = hit, "hit"
            elif now() - t0 <= budget_s:
                res, how = cache.lookup_or_scan(r["block"], r["key"], r["run_dir"])
            else:
                how = "not_scanned_budget"
        acc[how] += 1
        out.append({**r, "how": how, "res": res, "recovered": rec.get((r["block"], r["key"]), "unknown")})
    if tmpcache is not None:
        tmpcache.cleanup()
    scanned = [x for x in out if x["res"] is not None]
    d.mkdir(mode=0o700, parents=True, exist_ok=True)
    tmp = d / "transcript-scan-tables"
    tmp.mkdir(mode=0o700)
    # runs
    with open(tmp / "transcript_scan_runs.csv", "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["block", "run_key", "option", "layout", "model", "recovered_from_truncated_listing", "scanned", *BOOLEANS, "metadata_files_count", "patterns"])
        for x in sorted(out, key=lambda x: (x["block"], x["key"])):
            res = x["res"]
            w.writerow([x["block"], x["key"], x["option"], x["layout"], x["model"], x["recovered"], int(res is not None),
                        *[(int(res["booleans"][b]) if res else "") for b in BOOLEANS], (res["count_seen"] if res and res["count_seen"] is not None else ""), (";".join(res["patterns"]) if res else "")])
    # counts
    def tally(keyf, dims):
        g: dict = {}
        for x in out:
            c = g.setdefault(keyf(x), Counter())
            c["runs"] += 1
            if x["res"] is not None:
                c["scanned"] += 1
                for b in BOOLEANS:
                    c[b] += int(x["res"]["booleans"][b])
        rows = []
        for k, c in sorted(g.items()):
            rows.append({**dict(zip(dims, k)), "runs": c["runs"], "scanned": c["scanned"], "not_scanned": c["runs"] - c["scanned"], **{b: c[b] for b in BOOLEANS}})
        return rows
    cols = ["dimension", "option", "layout", "model", "recovered_from_truncated_listing", "runs", "scanned", "not_scanned", *BOOLEANS]
    rows = ([{"dimension": "option_layout", "model": "all", **r} for r in tally(lambda x: (x["option"], x["layout"], x["recovered"]), ["option", "layout", "recovered_from_truncated_listing"])]
            + [{"dimension": "option_layout_all_recovered", "model": "all", "recovered_from_truncated_listing": "all", **r}
               for r in tally(lambda x: (x["option"], x["layout"]), ["option", "layout"])]
            + [{"dimension": "option_layout_model", **r} for r in tally(lambda x: (x["option"], x["layout"], x["model"], x["recovered"]), ["option", "layout", "model", "recovered_from_truncated_listing"])])
    with open(tmp / "transcript_scan_counts.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    # quotes: PER_OPTION seeded runs among those with at least one boolean true
    qrows = []
    for opt in sorted({x["option"] for x in scanned}):
        pool = sorted((x for x in scanned if x["option"] == opt and any(x["res"]["booleans"].values())), key=lambda x: (x["block"], x["key"]))
        pick = random.Random(f"{seed}:{opt}").sample(pool, min(PER_OPTION, len(pool)))
        for x in sorted(pick, key=lambda x: (x["block"], x["key"])):
            for b in BOOLEANS:
                if x["res"]["booleans"][b] and b in x["res"]["quotes"]:
                    name, q = x["res"]["quotes"][b]
                    qrows.append({"option": opt, "block": x["block"], "run_key": x["key"], "model": x["model"], "recovered_from_truncated_listing": x["recovered"], "boolean": b, "pattern": name,
                                  "quote": q[:QUOTE_MAX]})
    with open(tmp / "transcript_scan_quotes.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["option", "block", "run_key", "model", "recovered_from_truncated_listing", "boolean", "pattern", "quote"], lineterminator="\n")
        w.writeheader()
        w.writerows(qrows)
    with open(tmp / "transcript_scan_patterns.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["boolean", "pattern", "where", "expression"], lineterminator="\n")
        w.writeheader()
        w.writerows(pattern_rows())
    account = {"format": FORMAT, "version": cache.version, "s1_runs_in_cut": len(runs), "scanned": len(scanned), "from_cache": acc["hit"], "scanned_now": acc["miss"], "unreadable": acc["unreadable"],
               "no_run_dir": acc["no_run_dir"], "not_scanned_budget": acc["not_scanned_budget"], "seed": seed, "per_option": PER_OPTION, "quote_max_chars": QUOTE_MAX, "seconds": round(now() - t0, 1),
               "booleans": list(BOOLEANS)}
    stamp.stamp_tables(tmp, stamp.header(bool(snap["final"]), snap["t"]))              # the tables first (it accepts nothing but tables here)
    (tmp / "transcript_scan.json").write_text(json.dumps(account, indent=1, sort_keys=True))
    for p in tmp.iterdir():
        p.replace(d / p.name)
    tmp.rmdir()
    return {"rows": len(out), "runs": len(runs), "scanned": len(scanned), "cached": acc["hit"], "computed": acc["miss"], "missing": len(runs) - len(scanned), "seconds": account["seconds"]}


def stage_soft(seal: Path, cache_dir: Path | None, **kw) -> dict:
    """`stage` that cannot fail the interim or the final: an exception leaves a note naming its class and the answer says it failed."""
    try:
        return stage(seal, cache_dir, **kw)
    except Exception as e:      # noqa: BLE001
        import traceback
        traceback.print_exc(file=sys.stderr)
        try:
            d = L.layout_dir(seal) / "side"
            d.mkdir(mode=0o700, parents=True, exist_ok=True)
            (d / "transcript_scan.FAILED.txt").write_text(f"the transcript scan was not made: {type(e).__name__}\n")
        except OSError:
            pass
        return {"failed": type(e).__name__}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m snapshot.transcriptscan", description=__doc__.split("\n\n")[0])
    ap.add_argument("step", choices=["fill", "stage", "patterns"])
    ap.add_argument("seal", nargs="?", type=Path)
    ap.add_argument("--merged-root", type=Path)
    ap.add_argument("--cache", type=Path)
    ap.add_argument("--stop-by", help="fill: ISO UTC time after which no run is started")
    ap.add_argument("--pause-file", type=Path, help="fill: wait while this file exists")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--budget-s", type=float, default=900.0, help="stage: seconds to scan runs missing from the cache")
    ap.add_argument("--seed", type=int, default=20271105)
    ns = ap.parse_args(argv)
    os.umask(0o077)
    if ns.step == "patterns":
        for r in pattern_rows():
            print(f"{r['boolean']} {r['pattern']}")
        return 0
    if ns.step == "fill":
        if not ns.merged_root or not ns.cache:
            ap.error("fill: --merged-root and --cache are required")
        stop = dt.datetime.fromisoformat(ns.stop_by.replace("Z", "+00:00")).timestamp() if ns.stop_by else None
        r = fill(ns.merged_root, ns.cache, stop_by=stop, pause_file=ns.pause_file, limit=ns.limit)
        print("transcriptscan fill " + " ".join(f"{k}={v}" for k, v in r.items() if v != ""))
        return 0
    if not ns.seal:
        ap.error("stage: the seal is required")
    r = stage_soft(ns.seal, ns.cache, budget_s=ns.budget_s, seed=ns.seed)
    print("transcriptscan stage " + (" ".join(f"{k}={v}" for k, v in r.items()) if "failed" not in r else "failed"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
