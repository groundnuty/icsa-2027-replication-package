import numpy as np
mask = np.load('/work/mask.npy')
tgt = np.load('/work/tgt.npy'); thr = np.load('/work/thr.npy'); sea = np.load('/work/sea_mask.npy')
nt, ncells = mask.shape
doy = np.arange(153, 245)
hot = np.zeros((nt, ncells), dtype=bool)
hot[:, sea] = tgt[:, sea] >= thr[doy-1][:, sea]

def segs_of(h):
    """maximal consecutive True segments as list of (start,end) local idx"""
    segs = []
    i = 0
    L = len(h)
    while i < L:
        if h[i]:
            j = i
            while j+1 < L and h[j+1]: j += 1
            segs.append((i, j))
            i = j+1
        else:
            i += 1
    return segs

bad = 0
for c in range(ncells):
    col = mask[:, c]
    idx = np.where(col)[0]
    if not len(idx): continue
    for sp in np.split(idx, np.where(np.diff(idx) > 1)[0] + 1):
        s, e = int(sp[0]), int(sp[-1])
        if not sea[c]: bad += 1; print("land in mask", c, s, e); break
        h = hot[s:e+1, c]
        if not h[0] or not h[-1]: bad += 1; print("ends not hot", c, s, e); break
        sg = segs_of(h)
        if max(b-a+1 for a, b in sg) < 5: bad += 1; print("no >=5 run", c, s, e); break
        for i in range(len(sg)-1):
            if sg[i+1][0] - sg[i][1] - 1 > 2: bad += 1; print("gap>2", c, s, e); break
        # boundary invariants
        if s > 0 and hot[s-1, c]: bad += 1; print("prev day hot", c, s, e); break
        if e < nt-1 and hot[e+1, c]: bad += 1; print("next day hot", c, s, e); break
print("structural violations:", bad)

# final consistency: mask == independently recomputed spans (fixed seg function)
def cell_mhw_runs(h):
    sg = segs_of(h)
    big = [(a, b) for (a, b) in sg if b - a + 1 >= 5]
    out = []
    for (a, b) in big:
        if out and a - out[-1][1] - 1 <= 2:
            out[-1] = (out[-1][0], b)
        else:
            out.append((a, b))
    return out

bad2 = 0
for c in range(ncells):
    expect = np.zeros(nt, dtype=np.uint8)
    for (s, e) in cell_mhw_runs(hot[:, c]):
        expect[s:e+1] = 1
    if not np.array_equal(mask[:, c], expect):
        bad2 += 1
print("cells where mask != recomputation:", bad2)

# region active days + events (recomputed)
active = mask.any(axis=1)
import datetime
tgt_dates = []
d = datetime.date(2016,6,1)
while d <= datetime.date(2016,8,31):
    tgt_dates.append(d); d += datetime.timedelta(days=1)
ev = []
i = 0
while i < nt:
    if active[i]:
        j = i
        while j+1 < nt and active[j+1]: j += 1
        ev.append((tgt_dates[i], tgt_dates[j])); i = j+1
    else: i += 1
print("events:", [(str(a), str(b)) for a, b in ev])
print("active count:", int(active.sum()))
