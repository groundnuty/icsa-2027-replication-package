"""The inspection queue (rubric §1): sets R, C, N and K-test mixed in one seeded order.

Population rows (JSONL, one per run): run_key, run_dir, instance_id, option, layout, model, seed,
label (the instrument's: complete / omitting / unknown), phase (pilot / calibration / main /
pagination / ktest), optionally decoded_not_delivered (#9's flag, True / False / None), and for K-test rows
the answer fixed by construction: truth (complete / omitting), truth_note (one line), and
truth_parts (the groups a correct extraction names as missing, e.g. [["baseline", 1995]]).

- R: every pilot, calibration, main or pagination run labelled `unknown`.
- C: every pilot and calibration run labelled `complete` or `omitting`; on main, either a seeded
  random sample of up to `c_main_per_cell` complete- and as many omitting-labelled runs per
  option x layout, or (the main block's coding plan, `c_rates`) every decided run whose seeded hash of its
  run key falls below its cell's rate, so membership does not depend on which runs have finished (the strata N and n
  are recorded either way), plus every main run whose
  `decoded_not_delivered` is True (it should never happen; each goes to inspection), marked forced.
  The pagination cell (block `pagination`, T-unpaginated: a primary block beside main) follows main's rule: the
  rubric (§1) says "main runs" and "per option x layout" and does not name the cell, and its option is its own stratum.
- K: every ktest row.
- N: every PILOT run with no label (`unlabelled` true: `population.py`), whether it ended by the time cap or not (science, #76,
  22:28Z: all of the pilot's planned runs are inspected). The coders answer it like any packet, in the same seeded order and with the same
  text form, and the answer is never scored against a label: no part of the gate, no resolved share, no kappa, no coverage record
  reads it. A pilot run with nothing to build (never started, no run directory, no code cell) is in set N all the same, and is refused
  into the key's `refused` with its reason like any packet that cannot be built, so every planned pilot run is in exactly one of R, C
  and N. Another phase's unlabelled run stays in no set (science's ruling speaks of the pilot's runs only), listed in the key under
  `unlabelled`; `report.py` counts it with the population.
  A time-capped run (`time_capped` true, "K" in report-spec: the runs ended by the time cap, which has nothing to do with set K) has
  no label at all (None), not `unknown`.

The queue file (what the coders' runner reads) holds only the opaque ids in one seeded random
order: the order is a shuffle of the sorted ids, so it depends on the seed and the ids alone.
The key file (set, run, label, truth, cue scan per packet) is written OUTSIDE the packet
directory and never goes to a coder. A run whose packet cannot be built is listed in the key
under `refused` with the reason, never silently dropped.
"""
from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

from . import packet, prompt, rubric

FORMAT_QUEUE = "icsa-inspection-queue-v1"
FORMAT_KEY = "icsa-inspection-key-v1"
PHASES = ("pilot", "calibration", "main", "pagination", "ktest")
MAIN_PHASES = ("main", "pagination")      # the phases whose decided runs are sampled for C (strata per option x layout x label)
LABELS = ("complete", "omitting", "unknown")


def id_secret(seed) -> str:
    return hashlib.sha256(f"icsa-inspection-packet-id|{seed}".encode()).hexdigest()


def c_hash(seed, run_key) -> float:
    """A run's place in [0, 1) for set C of the main block: a seeded hash of its run key alone, so that whether it joins C never depends on which
    other runs exist or have finished (science, #34, 4 Nov 18:53Z)."""
    return (int.from_bytes(hashlib.sha256(f"{seed}|C|{run_key}".encode()).digest()[:8], "big") >> 11) / 2**53       # 53 bits: exactly a float, strictly below 1


def assign_sets(rows: list[dict], *, seed, c_main_per_cell: int = 15, c_rates: dict | None = None) -> tuple[dict[str, dict], list[dict]]:
    """run_key -> {'set', 'forced'} for every selected run, and the C-main strata table.

    `c_rates` None: the earlier rule, a seeded random sample of up to `c_main_per_cell` per option x layout x label from the population as it is now.
    `c_rates` {(option, layout): rate}: the order-stable rule. A decided main run joins C when `c_hash(seed, run_key) < rate` of its cell, whatever else is
    in the population; a cell with decided runs and no rate is refused. The strata then also carry `rate` and `expected` (rate x N), beside the realised n."""
    seen = set()
    for r in rows:
        if r["run_key"] in seen:
            raise ValueError(f"run {r['run_key']} appears twice")
        seen.add(r["run_key"])
        if r.get("phase") not in PHASES:
            raise ValueError(f"run {r['run_key']}: phase {r.get('phase')!r} is not one of {PHASES}")
        if r["phase"] != "ktest" and r.get("label") not in LABELS and not (r.get("unlabelled") and r.get("label") is None):
            raise ValueError(f"run {r['run_key']}: label {r.get('label')!r} is not one of {LABELS}")
        if r["phase"] == "ktest" and r.get("truth") not in ("complete", "omitting"):
            raise ValueError(f"K-test case {r['run_key']}: truth must be complete or omitting")
        if r.get("decoded_not_delivered") not in (True, False, None):
            raise ValueError(f"run {r['run_key']}: decoded_not_delivered must be true, false or null")
        if r.get("unlabelled") not in (True, False, None):
            raise ValueError(f"run {r['run_key']}: unlabelled must be true, false or null")
        if r.get("time_capped") not in (True, False, None):
            raise ValueError(f"run {r['run_key']}: time_capped must be true, false or null")
        if r.get("time_capped") and (not r.get("unlabelled") or r.get("label") is not None):
            raise ValueError(f"run {r['run_key']}: a time-capped run is unlabelled and has no label (not even unknown)")
    out: dict[str, dict] = {}
    for r in rows:
        if r.get("unlabelled"):          # no final label: nothing for the coders to resolve or check, so never R or C
            if r["phase"] == "pilot":
                out[r["run_key"]] = {"set": "N", "forced": False}      # but a pilot run is read all the same, and its answer is never scored
            continue
        if r["phase"] == "ktest":
            out[r["run_key"]] = {"set": "K", "forced": False}
        elif r["label"] == "unknown":
            out[r["run_key"]] = {"set": "R", "forced": False}
        elif r["phase"] in ("pilot", "calibration"):
            out[r["run_key"]] = {"set": "C", "forced": False}
    strata = []
    main = [r for r in rows if r["phase"] in MAIN_PHASES and r["label"] in ("complete", "omitting")]
    for o, l, lab in sorted({(str(r["option"]), str(r["layout"]), r["label"]) for r in main}):
        members = sorted((r for r in main if (str(r["option"]), str(r["layout"]), r["label"]) == (o, l, lab)),
                         key=lambda r: str(r["run_key"]))
        extra = {}
        if c_rates is None:
            n = min(c_main_per_cell, len(members))
            pick = random.Random(f"{seed}|C|{o}|{l}|{lab}").sample(members, n)
        else:
            if (o, l) not in c_rates:
                raise ValueError(f"no C rate for cell {o} x {l}: a cell with decided runs cannot be left out of the sample")
            rate = c_rates[(o, l)]
            pick = [r for r in members if c_hash(seed, r["run_key"]) < rate]
            n, extra = len(pick), {"rate": rate, "expected": rate * len(members)}
        for r in pick:
            out[r["run_key"]] = {"set": "C", "forced": False, "c_stratum": [o, l, lab]}
        strata.append({"option": o, "layout": l, "label": lab, "N": len(members), "n": n,
                       "weight": len(members) / n if n else None, **extra})
    for r in main:
        if r.get("decoded_not_delivered") is True and r["run_key"] not in out:
            out[r["run_key"]] = {"set": "C", "forced": True}
    return out, strata


def order(ids, seed) -> list[str]:
    ids = sorted(ids)
    random.Random(f"{seed}|order").shuffle(ids)
    return ids


def build(rows: list[dict], *, seed, packets_dir, key_path, identifiers_for, c_main_per_cell: int = 15,
          rubric_path=None) -> dict:
    """Build every packet, the queue file (in packets_dir) and the key file (outside it)."""
    packets_dir, key_path = Path(packets_dir).resolve(), Path(key_path).resolve()
    if packets_dir == key_path.parent or packets_dir in key_path.parents:
        raise ValueError("the key file must be outside the packet directory")
    packets_dir.mkdir(parents=True, exist_ok=True)
    if any(packets_dir.iterdir()):
        raise FileExistsError(f"{packets_dir} is not empty")
    sets, strata = assign_sets(rows, seed=seed, c_main_per_cell=c_main_per_cell)
    unlabelled = [{"run_key": r["run_key"], "phase": r["phase"], "option": r.get("option"), "layout": r.get("layout"),
                   "model": r.get("model"), "reason": r.get("unlabelled_reason"), "time_capped": bool(r.get("time_capped")),
                   "set": sets.get(r["run_key"], {}).get("set")} for r in rows if r.get("unlabelled")]
    secret = id_secret(seed)
    by_key = {r["run_key"]: r for r in rows}
    entries, refused = {}, []
    for rk in sorted(sets):
        r, s = by_key[rk], sets[rk]
        pid = packet.packet_id(secret, rk)
        if pid in entries:
            raise ValueError(f"packet id collision {pid}")
        meta = {"run_key": rk, **s, "phase": r["phase"], "instance_id": r.get("instance_id"),
                "option": r.get("option"), "layout": r.get("layout"), "model": r.get("model"),
                "seed": r.get("seed"), "label": r.get("label"),
                "decoded_not_delivered": r.get("decoded_not_delivered")}
        if s["set"] == "N":
            meta.update(time_capped=bool(r.get("time_capped")), unlabelled_reason=r.get("unlabelled_reason"))
        if s["set"] == "K":
            meta.update(truth=r["truth"], truth_note=r.get("truth_note", ""), truth_parts=r.get("truth_parts", []),
                        pattern=r.get("pattern"), k_group=r.get("k_group", "core"), stated_narrowing=bool(r.get("stated_narrowing", False)))
        try:
            if not r.get("run_dir"):
                raise packet.PacketError("no run directory is recorded for the run (it never started, or its attempt left none)")
            pk = packet.build(r["run_dir"], identifiers_for(r), strict=s["set"] == "K")
            if s["set"] == "N" and not pk["cells"]:
                raise packet.PacketError(f"{r['run_dir']}: no code cell ran, so there is nothing for a coder to read")
        except packet.PacketError as e:
            refused.append({**meta, "reason": str(e)[:500]})
            continue
        (packets_dir / f"{pid}.txt").write_text(pk["text"])
        (packets_dir / f"{pid}.lines.json").write_text(json.dumps({str(k): v for k, v in pk["lines"].items()}))
        entries[pid] = {**meta, "packet_sha256": pk["sha256"], "cells": pk["cells"], "cues": pk["cues"],
                        "tokens": pk["tokens"]}
    rub = rubric.info(rubric_path)
    queue = {"format": FORMAT_QUEUE, "prompt_sha256": prompt.prompt_sha256(), "rubric_sha256": rub["sha256"],
             "order": order(entries, seed)}
    (packets_dir / "queue.json").write_text(json.dumps(queue, indent=1))
    key = {"format": FORMAT_KEY, "seed": seed, "id_secret": secret, "rubric": rub,
           "prompt_sha256": queue["prompt_sha256"], "c_main_per_cell": c_main_per_cell, "c_main_strata": strata,
           "packets": entries, "refused": refused,
           "unlabelled": sorted(unlabelled, key=lambda u: u["run_key"])}
    key_path.write_text(json.dumps(key, indent=1, sort_keys=True, default=str))
    return key


def known_endpoints() -> list[str]:
    """The platform's host names as the harness configures them (Onezone, Oneprovider): always sanitised."""
    try:
        from icsa.harness import real_sandbox as R
    except Exception:  # noqa: BLE001 -- without the harness there is no configured host to hide
        return []
    return [h for h in (getattr(R, "ONEZONE_HOST", None), getattr(R, "PROVIDER_HOST", None)) if h]


def identifiers(row: dict, *, instance_ids=(), model_names=(), extra_dirs=(), endpoints=()) -> dict[str, str]:
    """The identifiers to sanitise in one run's packet: its run key and run directory, its instance
    id and every other scenario name, every model name (keys, reported names, API ids), and every
    known endpoint host name (Onezone, Oneprovider, gate, and the local simulation's), which becomes
    the one token ENDPOINT. URLs, IP addresses and localhost are replaced by packet.sanitise_endpoints."""
    out: dict[str, str] = {}
    for v in (*known_endpoints(), *endpoints):
        if v:
            out[str(v)] = "ENDPOINT"
    for v in instance_ids:
        out[str(v)] = "SCENARIO"
    if row.get("instance_id"):
        out[str(row["instance_id"])] = "SCENARIO"
    for v in (*model_names, row.get("model") or ""):
        if v:
            out[str(v)] = "MODEL"
    for v in (row.get("run_dir"), *extra_dirs):
        if v:
            out[str(Path(v).resolve())] = "DIR"
    out[str(row["run_key"])] = "RUN"
    if row.get("key"):        # a campaign row's run_key is the store key; the record's own key (population.py) is a run identifier too
        out[str(row["key"])] = "RUN"
    return out


def read_population(path) -> list[dict]:
    return [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]
