#!/usr/bin/env python3
"""The 4 h test for M+'s rest (30(h)), after the barrier, with each step's source stated (science #34 12:33Z): a step MEASURED in the barrier is used as measured, a step not
measured is scaled by bytes and says so. Offline; reads $OUT/mplus_log.jsonl and the run records. Writes nothing but prints (and, with --write, the chosen resume plan).

  PYTHONPATH=<frozen tree> python mplus_project.py --out $OUT [--limit-h 4] [--write FILE]

The frozen `plan_window` always scales the layout provisioning by bytes from the REQUIRED scope's provisioning (`project_window`), even when the barrier measured a layout
provisioning; this keeps the frozen step_times and project_window and replaces only that one figure by the measured mean of the layout provisioning where there is one.
Per layout it lists: evict, M cold wall, required provisioning, M+ required wall, layout provisioning (measured | scaled by bytes), M+ layout wall (measured | taken from M+ required).
Exit 0 all 30 runs fit, 1 reduced to 3 of 5 per layout, 2 a step has no figure at all (nothing to project from)."""
import argparse, json, sys
from pathlib import Path
from icsa.scripted import mplus as M
from icsa.scripted.summarize import load_runs
from icsa.records import Layout

INST = ["I35", "I37", "I48", "I01", "I06"]
LB = {"S1": 4254680853, "S2": 3785412176}          # fed.MAIN_S1_BYTES, MAIN_S2_BYTES (#3): the layouts' bytes


def project(log, runs, seed=20271201, limit_s=4 * 3600, instances=INST):
    steps = M.step_times(log, runs)
    done = M.done_steps(runs)
    out, lines, total_all, total_red = {}, [], 0.0, 0.0
    for layout in ("S1", "S2"):
        st = steps[layout]
        miss = [k for k in ("evict_s", "provision_required_s", "placed_bytes_required", "cold_site_f_wall_s", "mplus_required_wall_s") if not st.get(k)]
        if miss:
            lines.append(f"{layout}: NO FIGURE for {miss}: cannot project"); out[layout] = None; continue
        pl = [e["seconds"] for e in log if e.get("event") == "provision" and e.get("layout") == layout and e.get("scope") == "layout" and e.get("confirmed_placed") is True]
        ml = [r["wall_s"] for r in runs if r.get("ok") and r.get("layout") == layout and (r.get("extra") or {}).get("variant") == "mplus" and r["extra"].get("scope") == "layout"]
        e, p, c, m = st["evict_s"], st["provision_required_s"], st["cold_site_f_wall_s"], st["mplus_required_wall_s"]
        p_layout = sum(pl) / len(pl) if pl else p * LB[layout] / st["placed_bytes_required"]
        m_layout = sum(ml) / len(ml) if ml else m
        lines.append(f"{layout}: evict {e:.0f}s (measured, n={st['samples']['evict']}); M cold wall {c:.0f}s (measured, n={st['samples']['cold_site_f']}); required provisioning {p:.0f}s "
                     f"(measured, n={st['samples']['provision']}, {st['placed_bytes_required']:.3g} B); M+ required wall {m:.0f}s (measured, n={st['samples']['mplus_required']}); "
                     f"layout provisioning {p_layout:.0f}s ({'measured, n=%d' % len(pl) if pl else 'SCALED by bytes: %.3g/%.3g of the required scope' % (LB[layout], st['placed_bytes_required'])}); "
                     f"M+ layout wall {m_layout:.0f}s ({'measured, n=%d' % len(ml) if ml else 'taken from M+ required: NOT measured'})")
        order = M.select_instances(instances, seed, Layout(layout), None)
        for key, ids, acc in (("all", order, "all"), ("reduced", order[:M.REDUCED_N], "red")):
            s = 0.0
            for iid in ids:
                if (iid, layout, "cold-site_f") not in done: s += e + c
                if (iid, layout, "mplus-required") not in done: s += e + p + m
            left = [iid for iid in ids if (iid, layout, "mplus-layout") not in done]
            if left: s += e + p_layout + len(left) * m_layout
            out.setdefault(key, {})[layout] = s
    ok = all(out.get(l) is not False for l in ("S1", "S2")) and "all" in out and all(v is not None for v in (out.get("S1"), out.get("S2")))
    return steps, lines, out, done


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0]); ap.add_argument("--out", required=True, type=Path); ap.add_argument("--limit-h", type=float, default=4.0)
    ap.add_argument("--write", type=Path); a = ap.parse_args(argv)
    log = [json.loads(x) for x in (a.out / "mplus_log.jsonl").read_text().splitlines()]
    runs = load_runs(a.out)
    steps, lines, out, done = project(log, runs, limit_s=a.limit_h * 3600)
    print("\n".join(lines))
    if out.get("S1") is None or out.get("S2") is None or "all" not in out:
        print("NO PROJECTION: a layout lacks a figure above"); return 2
    allh = sum(out["all"].values()); redh = sum(out["reduced"].values()); keep = allh <= a.limit_h * 3600
    print(f"remaining, drain excluded: all 5 instances per layout {allh/3600:.2f} h (S1 {out['all']['S1']/3600:.2f} + S2 {out['all']['S2']/3600:.2f}); first 3 {redh/3600:.2f} h; limit {a.limit_h:g} h -> "
          + ("ALL 30 runs (mplus-resume-all.json)" if keep else "REDUCED to 3 of 5 per layout (mplus-resume-reduced.json)"))
    print("steps done:", len(done))
    if a.write:
        src = Path(__file__).resolve().parent / ("mplus-resume-all.json" if keep else "mplus-resume-reduced.json")
        a.write.write_text(src.read_text()); print("wrote", a.write)
    return 0 if keep else 1


if __name__ == "__main__":
    sys.exit(main())
