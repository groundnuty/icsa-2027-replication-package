import numpy as np, datetime

tgt = np.load('/work/tgt.npy')          # (92, 3600)
thr = np.load('/work/thr.npy')          # (366, 3600)
sea = np.load('/work/sea_mask.npy')     # (3600,)
ncells = tgt.shape[1]
nt = tgt.shape[0]

tgt_dates = []
d = datetime.date(2016,6,1)
while d <= datetime.date(2016,8,31):
    tgt_dates.append(d); d += datetime.timedelta(days=1)
doy = np.array([dt.timetuple().tm_yday for dt in tgt_dates])
assert (doy == np.arange(153, 245)).all(), doy[:5]
print("doy range:", doy[0], doy[-1])

thr_t = thr[doy-1]                      # (92, 3600)
hot = np.zeros((nt, ncells), dtype=bool)
hot[:, sea] = (tgt[:, sea] >= thr_t[:, sea])
print("hot days total (sea cells):", int(hot.sum()), " mean per day:", hot.sum(axis=1).mean())

def cell_mhw_runs(h):
    idx = np.where(h)[0]
    runs = []
    if len(idx):
        split = np.where(np.diff(idx) > 1)[0] + 1
        for s in np.split(idx, split):
            if len(s) >= 5:
                runs.append([s[0], s[-1]])
    joined = []
    for r in runs:
        if joined and r[0] - joined[-1][1] - 1 <= 2:
            joined[-1][1] = r[1]
        else:
            joined.append(list(r))
    return [tuple(x) for x in joined]

def brute(h):
    idx = np.where(h)[0]
    segs = []
    if len(idx):
        for i in range(len(idx)):
            if i+1 < len(idx) and idx[i+1] - idx[i] > 1:
                segs.append(idx[:i+1])
        segs.append(idx[i:])
    big = [seg for seg in segs if len(seg) >= 5]
    out = []
    for seg in big:
        if out and seg[0] - out[-1] - 1 <= 2:
            out = out[:-1] + [out[-1][0], seg[-1]]
        else:
            out.append([seg[0], seg[-1]])
    return [tuple(o) for o in out]

mask = np.zeros((nt, ncells), dtype=np.uint8)
n_mhw_cells = 0
for c in range(ncells):
    if not sea[c]:
        continue
    r1 = cell_mhw_runs(hot[:, c])
    if r1: n_mhw_cells += 1
    for (s, e) in r1:
        mask[s:e+1, c] = 1
print("cells with >=1 per-cell MHW:", n_mhw_cells)

rng = np.random.default_rng(7)
ok = True
for _ in range(8):
    c = int(rng.integers(0, ncells))
    if cell_mhw_runs(hot[:, c]) != brute(hot[:, c]):
        ok = False; print("MISMATCH", c)
print("cross-check ok:", ok)

active = mask.any(axis=1)
print("active days:", int(active.sum()), "of", nt)
print("active per day (first 92):", [int(x) for x in active])
ev = []
i = 0
while i < nt:
    if active[i]:
        j = i
        while j+1 < nt and active[j+1]:
            j += 1
        ev.append((tgt_dates[i], tgt_dates[j]))
        i = j+1
    else:
        i += 1
print("events:")
for (a, b) in ev:
    print("  ", a, "->", b, f"({(b-a).days+1} days)")

np.save('/work/mask.npy', mask)
with open('/work/events.txt', 'w') as f:
    for a, b in ev:
        f.write(f"{a} {b}\n")
