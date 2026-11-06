"""PRIMARY.json at the seal root (lane-snap6, 6 Nov; science #34 03:30Z, option B by Route D): which table sets are the PRIMARY ones. The K-augmented sets (out-kaug/, out-coded-kaug/) when they were computed and are complete, else the frozen
out/ and out-coded/ (and it says so). Also the exact table note, the correction file's sha256 and the counts by option, in the seal only, and NOTE-K-AUG.txt in each K-augmented directory.
   python3 -I primary_json.py <seal dir>"""
import hashlib, json, os, sqlite3, sys
seal = os.path.abspath(sys.argv[1])
# science's K-aug note (#34 09:36Z, verbatim from handoff/kaug-note-science-0936Z.md): the count of runs comes from the correction file's count_applies_no_earlier_done_copy; the I48 sentence only when the unscorable fallback is in force (frozen/correction-unscorable-*.json), its count from that file
NOTE_A = ("**K-aug:** the frozen tables, with these runs counted as time-capped by count only, without measures. **{n} runs** whose earliest analysable attempt ran past the 8.17 h cap and was marked an infrastructure failure by the dispatcher, as its record couldn't be read; "
          "under the registered definition a cap is never an infrastructure failure. They were selected by that rule before the final's tables were read, and their later attempts are held aside as duplicates.")
NOTE_I48 = " **{m} run{pl}** that ended by its time cap, whose partial output couldn't be scored within the analysis's memory limit."
NOTE_Z = " The tables in `out/` and `out-coded/` leave them out, and a sensitivity counts their retries instead."
NOTE_SENS = {"out-retries": "computed on the frozen basis WITHOUT the capped correction (the retries count in place of the capped attempts) and without K-aug: compare with `out/` and `out-coded/`, not with the primary `out-kaug/`",
             "out-lab504": "computed on the frozen basis, with the capped correction and without K-aug, the flagged Lab-504 runs left out: compare with `out/` and `out-coded/`, not with the primary `out-kaug/`",
             "out-050": "computed on the frozen basis, with the capped correction and without K-aug, at the default 00:50Z cut: compare with `out/` and `out-coded/`, not with the primary `out-kaug/`"}
def complete(d):
    return os.path.isfile(os.path.join(seal, d, "tables", "manifest.json")) and os.path.isfile(os.path.join(seal, d, "SNAPSHOT.json"))
def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.isfile(p) else None
kaug, kaug_c = complete("out-kaug"), complete("out-coded-kaug")
plain, plain_c = complete("out"), complete("out-coded")
capped_by_opt, n_capped = {}, 0
try:
    c = sqlite3.connect(f"file:{seal}/out/work/cut/state.sqlite?mode=ro", uri=True)
    r = c.execute("select value from meta where key='capped_correction_runs'").fetchone()
    keys = json.loads(r[0]) if r else []
    n_capped = len(keys)
    for k in keys:
        o = k.split("__")[2]
        capped_by_opt[o] = capped_by_opt.get(o, 0) + 1
except Exception:       # noqa: BLE001
    pass
held = None
try:
    held = json.load(open(os.path.join(seal, "out", "work", "cut", "cut.json"))).get("capped_held_aside")
except Exception:       # noqa: BLE001
    pass
import glob
_cf = sorted(glob.glob(os.path.join(seal, "frozen", "correction-capped-*.json")))      # the correction file whatever its row count (7, 8, ...): the one the driver copied into frozen/
csha = sha(_cf[-1]) if _cf else None
n_rule, n_unsc = None, 0
try:
    n_rule = json.load(open(_cf[-1])).get("count_applies_no_earlier_done_copy")
except Exception:       # noqa: BLE001
    pass
_uf = sorted(glob.glob(os.path.join(seal, "frozen", "correction-unscorable-*.json")))
try:
    n_unsc = sum(len(json.load(open(f)).get("attempts", [])) for f in _uf)
except Exception:       # noqa: BLE001
    n_unsc = 0
usha = sha(_uf[-1]) if _uf else None
if n_rule is None:      # no correction file: the old definition cannot be stated: say so rather than guess
    NOTE = "the correction file was not found in frozen/: the K-augmented note cannot be rendered"
else:
    NOTE = NOTE_A.format(n=n_rule) + (NOTE_I48.format(m=n_unsc, pl="" if n_unsc == 1 else "s") if n_unsc else "") + NOTE_Z

prim = "out-kaug" if kaug else ("out" if plain else None)
prim_c = "out-coded-kaug" if kaug_c else ("out-coded" if plain_c else None)
doc = {"format": "icsa-snapshot-primary-v1",
       "primary_tables": prim, "primary_coded_tables": prim_c,
       "frozen_beside": {"tables": "out" if plain else None, "coded_tables": "out-coded" if plain_c else None},
       "k_augmented": {"computed": bool(kaug), "coded_computed": bool(kaug_c), "capped_runs_applied": n_capped, "capped_runs_by_option": capped_by_opt, "held_aside_earlier_done_copy": held,
                       "correction_file_sha256": csha, "unscorable_memory_runs": n_unsc, "unscorable_file_sha256": usha, "runs_applying_by_rule": n_rule, "table_note": NOTE if kaug or kaug_c else None},
       "sensitivities": {d: {"complete_in_this_seal": complete(d), "dir_in_sens_seal": (os.path.basename(seal) + "-sens/" + d) if os.path.isdir(os.path.join(seal + "-sens", d)) else None,
                             "complete_in_sens_seal": os.path.isfile(os.path.join(seal + "-sens", d, "tables", "manifest.json")),      # the heavy sensitivities of the final run by resume into <seal>-sens (science 6 Nov): their state at the time of THIS write
                             "note": NOTE_SENS[d]} for d in ("out-retries", "out-lab504", "out-050")},
       "side_tables": {"fidelity-extra": os.path.isdir(os.path.join(seal, "fidelity-extra"))},
       "why": ("science #34 03:30Z (option B by Route D): out-kaug/ is the primary, out/ is the frozen analysis beside it" if kaug else
               "the K-augmented tables were NOT computed in this run (switch off, correction not applied, or a failure): the frozen out/ is the only table set")}
p = os.path.join(seal, "PRIMARY.json")
open(p, "w").write(json.dumps(doc, indent=1, sort_keys=True)); os.chmod(p, 0o600)
for d, on in (("out-kaug", kaug), ("out-coded-kaug", kaug_c)):
    if on:
        t = os.path.join(seal, d, "NOTE-K-AUG.txt")
        open(t, "w").write(f"{NOTE}\ncorrection file sha256: {csha}\nunscorable (memory) file sha256: {usha}\ncapped runs applied by option (counts): {json.dumps(capped_by_opt, sort_keys=True)}\nheld aside (an earlier done copy exists): {held}\n"); os.chmod(t, 0o600)
print(f"PRIMARY.json: primary tables {prim}, coded {prim_c}; frozen beside: out {plain}, out-coded {plain_c}; capped applied {n_capped} {capped_by_opt}")
