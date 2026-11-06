import numpy as np, json, datetime as dt, pickle

hot = np.load("/work/hot.npy")
sea = np.load("/work/sea.npy")
with open("/work/dates_ext_tgt.pkl","rb") as fh: dd = pickle.load(fh)
tgt_dates = dd["tgt_dates"]
assert hot.shape[0] == tgt_dates.size == 92

def runs_of(mask):
    m = np.asarray(mask, dtype=bool)
    if m.size == 0: return []
    d = np.diff(m.astype(np.int8))
    starts = list(np.where(d == 1)[0] + 1)
    ends = list(np.where(d == -1)[0])
    if m[0]: starts = [0] + starts
    if m[-1]: ends = ends + [m.size - 1]
    return list(zip(starts, ends))

def detect_mhw(hot1d, min_run=5, join_gap=2):
    runs = [(s, e) for (s, e) in runs_of(hot1d) if e - s + 1 >= min_run]
    if not runs: return []
    merged = [[int(runs[0][0]), int(runs[0][1])]]
    for s, e in runs[1:]:
        gap = s - merged[-1][1] - 1
        if 1 <= gap <= join_gap:
            merged[-1][1] = int(e)
        else:
            merged.append([int(s), int(e)])
    return [tuple(x) for x in merged]

nt, ny, nx = hot.shape
mhw = np.zeros((nt, ny, nx), dtype=np.uint8)
percell_events = {}
total_events = 0
for i in range(ny):
    for j in range(nx):
        if not sea[i, j]:
            continue
        evs = detect_mhw(hot[:, i, j])
        if evs:
            percell_events[(i, j)] = evs
            total_events += len(evs)
            for s, e in evs:
                mhw[s:e+1, i, j] = 1

print("per-cell MHWs total:", total_events, "cells with >=1 MHW:", len(percell_events))
lens = np.array([e - s + 1 for evs in percell_events.values() for s, e in evs])
print("per-cell MHW length: min", lens.min(), "max", lens.max(), "mean", round(float(lens.mean()), 2))
print("length histogram:", {int(k): int(v) for k, v in zip(*np.unique(lens, return_counts=True))})

active = mhw.max(axis=(1, 2)).astype(bool)
print("active days:", int(active.sum()), "of", nt)
print("per-day active-cell counts (first 30):", mhw.sum(axis=(1,2))[:30])
print("zero-active days:", int((~active).sum()))

reg = []
d = 0
while d < nt:
    if active[d]:
        e = d
        while e + 1 < nt and active[e + 1]:
            e += 1
        reg.append((d, e))
        d = e + 1
    else:
        d += 1
print("regional events:", len(reg))
for s, e in reg:
    print("  onset", str(tgt_dates[s])[:10], "end", str(tgt_dates[e])[:10], "length", e - s + 1, "days")

np.save("/work/mhw.npy", mhw)
with open("/work/events.pkl","wb") as fh:
    pickle.dump({"percell": percell_events, "regional": reg}, fh)
print("saved mhw + events")
