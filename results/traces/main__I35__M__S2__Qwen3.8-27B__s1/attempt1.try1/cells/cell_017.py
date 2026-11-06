import numpy as np, json
from collections import Counter

mhw = np.load("/tmp/mhw.npy").astype(bool)
tdates = np.datetime64("2009-06-01") + np.arange(92)
nt, nsea = mhw.shape

active = mhw.any(axis=1)
print("active days:", int(active.sum()), "of", nt)

dura = np.diff(np.concatenate([[0], active.astype(int), [0]]))
ev_s = np.where(dura == 1)[0]
ev_e = np.where(dura == -1)[0] - 1
events = [(int(s), int(e)) for s, e in zip(ev_s, ev_e)]
print("regional events:")
for s, e in events:
    print("  ", str(tdates[s]), "->", str(tdates[e]), " len", e - s + 1)

# per-cell duration stats recompute quickly for report
hpad = np.zeros((nsea, nt + 2), dtype=bool); hpad[:, 1:-1] = mhw.T
d = np.diff(hpad.astype(np.int8), axis=1)
cnt = Counter()
cells_with = 0
for c in range(nsea):
    starts = np.where(d[c] == 1)[0]; ends = np.where(d[c] == -1)[0]
    runs = [e - s + 1 for s, e in zip(starts, ends)]
    if runs:
        cells_with += 1
        cnt.update(runs)
print("cells with MHW:", cells_with, " total:", sum(cnt.values()), " max dur:", max(cnt))

json.dump([{"onset": str(tdates[s]), "end": str(tdates[e])} for s, e in events], open("/tmp/events.json", "w"))
print("OK")
