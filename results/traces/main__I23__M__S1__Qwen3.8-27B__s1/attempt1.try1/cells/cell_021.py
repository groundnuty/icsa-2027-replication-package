import numpy as np, json, datetime as dt
OUT="/tmp/mhw"
tgt = np.load(f"{OUT}/tgt.npy").reshape(92, 3600)
thr_s = np.load(f"{OUT}/thr_s.npy")
sea = np.load(f"{OUT}/sea.npy")
D_tgt = np.load(f"{OUT}/D_tgt.npy")
dates = json.load(open(f"{OUT}/dates.json"))
tgt_dates = [dt.date.fromisoformat(s) for s in dates["tgt_dates"]]

hot = (tgt >= thr_s[D_tgt]) & sea[None,:]

def runs_of(h):
    pad = np.concatenate([[False], np.asarray(h), [False]])
    d = np.diff(pad.astype(np.int8))
    s = np.flatnonzero(d == 1); e = np.flatnonzero(d == -1) - 1
    return list(zip(s.tolist(), e.tolist()))

# Alt interpretation: join ALL hot runs separated by <=2 non-hot days first, then require total length >=5
def cell_events_alt(h):
    runs = runs_of(h)
    merged = []
    for s,e in runs:
        if merged and s - merged[-1][1] - 1 <= 2:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s,e))
    return [(s,e) for s,e in merged if e - s + 1 >= 5]

def cell_events_main(h):
    runs = [ (s,e) for s,e in runs_of(h) if e-s+1 >= 5 ]
    merged = []
    for s,e in runs:
        if merged and s - merged[-1][1] - 1 <= 2:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s,e))
    return merged

sea_idx = np.flatnonzero(sea)
n_main = n_alt = 0
for c in sea_idx:
    n_main += len(cell_events_main(hot[:,c]))
    n_alt += len(cell_events_alt(hot[:,c]))
print("main interpretation MHWs:", n_main, "| alt (join-then-duration) MHWs:", n_alt)

# also check: what if duration counted after joining but join gap only between original runs of any length
# (same as alt). And check what happens with no smoothing of threshold (diagnostic only)
print("diagnostics done")
