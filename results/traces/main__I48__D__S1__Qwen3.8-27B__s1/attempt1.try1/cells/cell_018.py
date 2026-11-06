import numpy as np, datetime

tgt = np.load('/work/tgt.npy'); thr = np.load('/work/thr.npy'); sea = np.load('/work/sea_mask.npy')
ncells = tgt.shape[1]; nt = tgt.shape[0]
tgt_dates = []
d = datetime.date(2016,6,1)
while d <= datetime.date(2016,8,31):
    tgt_dates.append(d); d += datetime.timedelta(days=1)
doy = np.array([dt.timetuple().tm_yday for dt in tgt_dates])
assert (doy == np.arange(153, 245)).all()

hot = np.zeros((nt, ncells), dtype=bool)
hot[:, sea] = (tgt[:, sea] >= thr[doy-1][:, sea])

def cell_mhw_runs(h):
    idx = np.where(h)[0]
    runs = []
    if len(idx):
        split = np.where(np.diff(idx) > 1)[0] + 1
        for s in np.split(idx, split):
            if len(s) >= 5:
                runs.append([int(s[0]), int(s[-1])])
    joined = []
    for r in runs:
        if joined and r[0] - joined[-1][1] - 1 <= 2:
            joined[-1][1] = r[1]
        else:
            joined.append(list(r))
    return [tuple(x) for x in joined]

def brute(h):
    # fully independent, loop-based
    segs, s = [], None
    for i in range(len(h)):
        if h[i]:
            if s is None: s = i
            e = i
        else:
            if s is not None:
                segs.append((s, e)); s = None
    if s is not None: segs.append((s, e))
    big = [sg for sg in segs if sg[1] - sg[0] + 1 >= 5]
    out = []
    for (a, b) in big:
        if out and a - out[-1][1] - 1 <= 2:
            out[-1] = (out[-1][0], b)
        else:
            out.append((a, b))
    return out

mask = np.zeros((nt, ncells), dtype=np.uint8)
n_mhw_cells = 0
for c in range(ncells):
    if not sea[c]: continue
    r1 = cell_mhw_runs(hot[:, c])
    if r1: n_mhw_cells += 1
    for (s, e) in r1:
        mask[s:e+1, c] = 1
print("cells with >=1 per-cell MHW:", n_mhw_cells)

rng = np.random.default_rng(7)
mismatch = 0
for c in range(ncells):
    if cell_mhw_runs(hot[:, c]) != brute(hot[:, c]):
        mismatch += 1; print("MISMATCH", c)
print("mismatches over ALL 3600 cells:", mismatch)

active = mask.any(axis=1)
print("active days:", int(active.sum()), "of", nt)
print("active days list (date:1):", [tgt_dates[i].strftime('%m-%d') for i in range(nt) if active[i]])
ev = []
i = 0
while i < nt:
    if active[i]:
        j = i
        while j+1 < nt and active[j+1]: j += 1
        ev.append((tgt_dates[i], tgt_dates[j])); i = j+1
    else: i += 1
print("events:")
for a, b in ev: print("  ", a, "->", b, f"({(b-a).days+1} days)")

np.save('/work/mask.npy', mask)
with open('/work/events.txt', 'w') as f:
    for a, b in ev: f.write(f"{a} {b}\n")
