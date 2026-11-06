"""Two side tables beside the primary fault-injection fidelity read (lane-snap6, 6 Nov; science #34 04:02Z, ruling (a)). Failing soft, last in order.
   python3 -I fidelity_extra.py --latest <h3_table.csv of the score pulled into the seal> --original <h3_table.csv of the 5 Nov 08:22Z score> --out-dir DIR --t ISO [--final true|false] [--latest-tag TAG --original-tag TAG]
 1. fidelity_invalid_original.csv : per tested cell, the ORIGINAL score's allocation counts (planned / invalid / lost / pending / withheld, faulted and control) and its status, with the invalid reasons reduced to class counts; the same rows
    for the pulled score when it is a different one (column `score`).
 2. fidelity_worstcase_bounds.csv : from the PULLED score's frozen counts, per tested cell: recall and precision recomputed counting every still-invalid faulted run as a MISS (denominator n_faulted + n_invalid_faulted: conservative, since some of those
    may be unobservable by design) and every invalid control as a FALSE FLAG (precision = detected / (detected + faulted-run false flags + control false alarms + invalid controls)); Wilson 95% intervals; the verdict at the H3 threshold 0.9.
Counts and rates of the fault-calibration cells only (no study outcome). The first line of each CSV is a comment line (skiprows=1), like the other side tables."""
import argparse, json, math, re, sys
import pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("--latest", required=True); ap.add_argument("--original", required=True); ap.add_argument("--out-dir", required=True)
ap.add_argument("--t", required=True); ap.add_argument("--final", default="false"); ap.add_argument("--latest-tag", default="latest"); ap.add_argument("--original-tag", default="20261105T082219Z")
a = ap.parse_args()
TH = 0.9

def load(p):
    t = pd.read_csv(p)
    if str(t.columns[0]).startswith("#"):
        t = pd.read_csv(p, skiprows=1)
    return t[(t["tested"].astype(str) == "True") & (t["subset"] == "observable")].copy()

def wilson(k, n, z=1.959964):
    if n <= 0:
        return (float("nan"), float("nan"))
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)

def classes(s):
    """invalid_reasons is a JSON object {reason: count}. Classes (science #34 06:13Z): zero_read_by_design = 'not_observed' (the listing_truncation S1 runs: the plan has zero read operations, nothing for the fault to act on);
    attribution_overlap = 'run window overlaps [...] (same principal)'; left_no_record = a neighbour attempt left no record and may share the slot (older score); other = anything else. Counts only."""
    out = {"zero_read_by_design": 0, "attribution_overlap": 0, "left_no_record": 0, "other": 0}
    try:
        d = json.loads(s) if isinstance(s, str) and s.strip() else {}
    except ValueError:
        return {**out, "other": -1}
    for k, n in d.items():
        cls = ("zero_read_by_design" if k == "not_observed" else "attribution_overlap" if k.startswith("run window overlaps") else "left_no_record" if "left no record" in k else "other")
        out[cls] += int(n)
    return out


def alloc_rows(t, tag):
    rows = []
    for _, r in t.iterrows():
        cl = classes(r.get("invalid_reasons"))
        rows.append({"score": tag, "option": r["option"], "layout": r["layout"], "record": r["record"], "condition": r["condition"], "status": r["status"],
                     **{c: int(r[c]) for c in t.columns if re.match(r"n_(planned|invalid|lost|pending|withheld)_(faulted|control)$", c)},
                     "invalid_zero_read_by_design": cl["zero_read_by_design"], "invalid_attribution_overlap": cl["attribution_overlap"], "invalid_left_no_record": cl["left_no_record"], "invalid_other": cl["other"],
                     "invalid_reasons_listed": str(r.get("invalid_reasons"))})
    return rows

orig, lat = load(a.original), load(a.latest)
NOTE = "listing_truncation in S1 plans zero read ops; the fault has nothing to act on, so the record observes nothing; the observability table was fixed before calibration and is not changed. Attribution-overlap runs (the run window overlaps another run of the same principal) stay invalid, are listed with their reason, and enter the worst-case bound"
head = f"# snapshot t={a.t} final={a.final} fault-calibration side table (lane-snap6); not part of the registered analysis; original score {a.original_tag}, pulled score {a.latest_tag}. Note on the invalid (not_observed) runs: {NOTE}."
import os
os.makedirs(a.out_dir, exist_ok=True)
rows1 = alloc_rows(orig, a.original_tag) + (alloc_rows(lat, a.latest_tag) if a.latest_tag != a.original_tag else [])
t1 = pd.DataFrame(rows1)
bounds = []
for _, r in lat.iterrows():
    nf, nc, ni_f = int(r["n_faulted"]), int(r["n_control"]), int(r.get("n_invalid_faulted", 0))
    # the frozen table carries rates, not the detected counts: tp = recall x n_faulted and fa = false_alarm x n_control (small integers, exact), checked against the stated precision
    tp = int(round(r["recall"] * nf)) if nf and not math.isnan(r["recall"]) else 0
    fa = int(round(r["false_alarm"] * nc)) if nc and not math.isnan(r["false_alarm"]) else 0
    ff, ni_c = int(r.get("n_false_flag_faulted", 0)), int(r.get("n_invalid_control", 0))
    derived_ok = True
    if (tp + ff + fa) and not math.isnan(r["precision"]):
        derived_ok = abs(tp / (tp + ff + fa) - r["precision"]) < 1e-9
    den_r = nf + ni_f; den_p = tp + ff + fa + ni_c
    rec = tp / den_r if den_r else float("nan"); prec = tp / den_p if den_p else float("nan")
    rl, rh = wilson(tp, den_r); pl, ph = wilson(tp, den_p)
    ok = bool(rec >= TH and prec >= TH)
    cl = classes(r.get("invalid_reasons"))
    bounds.append({"option": r["option"], "layout": r["layout"], "record": r["record"], "condition": r["condition"], "pulled_status": r["status"],
                   "invalid_zero_read_by_design": cl["zero_read_by_design"], "invalid_attribution_overlap": cl["attribution_overlap"], "invalid_left_no_record": cl["left_no_record"], "invalid_other": cl["other"],
                   "n_detected_derived": tp, "derivation_matches_precision": derived_ok, "n_faulted_scored": nf, "n_invalid_faulted": ni_f, "n_false_flag_faulted": ff, "n_false_alarm_derived": fa, "n_invalid_control": ni_c,
                   "recall_reported": r.get("recall"), "precision_reported": r.get("precision"),
                   "recall_worstcase": rec, "recall_worstcase_lo": rl, "recall_worstcase_hi": rh, "precision_worstcase": prec, "precision_worstcase_lo": pl, "precision_worstcase_hi": ph,
                   "worstcase_verdict": ("pass" if ok else "fail") if (nf + ni_f) else "not_testable", "changes_reading": bool(ni_f or ni_c)})
t2 = pd.DataFrame(bounds)
for name, t in (("fidelity_invalid_original", t1), ("fidelity_worstcase_bounds", t2)):
    p = os.path.join(a.out_dir, name + ".csv")
    with open(p, "w") as fh:
        fh.write(head + "\n")
        t.to_csv(fh, index=False)
    os.chmod(p, 0o600)
print(f"fidelity_extra: invalid_original rows={len(t1)} (cells with invalid: {int((t1.filter(regex='^n_invalid').sum(axis=1) > 0).sum())}), worstcase rows={len(t2)}, cells whose reading changes={int(t2['changes_reading'].sum())}")
