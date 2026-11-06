import numpy as np, datetime as dt

z = np.load("/work/cache_sst.npz"); tgt32 = z["tgt"]; tgt_ord = z["tgt_ord"]
z2 = np.load("/work/cache_thr2.npz"); thr, clim = z2["thr"], z2["clim"]
tgt64 = tgt32.astype(np.float64)
tgt_doy = np.array([dt.date.fromordinal(int(o)).timetuple().tm_yday for o in tgt_ord], dtype=np.int32)
sea = np.all(np.isfinite(tgt64), axis=0)
dates = [dt.date.fromordinal(int(o)) for o in tgt_ord]
print("target days:", len(dates), dates[0], "..", dates[-1], "| sea cells:", int(sea.sum()))

# hot days (>= threshold), sea cells only
with np.errstate(invalid="ignore"):
    hot = (tgt64 >= thr[tgt_doy-1]) & sea[None, :, :]
print("hot cell-days: %d of %d (%.1f%%)" % (hot.sum(), hot[:, sea].size, 100*hot[:, sea].mean()))

# per-cell MHW: runs >=5 consecutive hot days, then join gaps of 1-2 non-hot days
def cell_segments(hot):
    n = len(hot); segs = []; i = 0
    while i < n:
        if hot[i]:
            j = i
            while j < n and hot[j]: j += 1
            if j - i >= 5: segs.append((i, j-1))
            i = j
        else:
            i += 1
    if not segs: return []
    joined = [list(segs[0])]
    for s, e in segs[1:]:
        if s - joined[-1][1] - 1 <= 2:
            joined[-1][1] = e
        else:
            joined.append([s, e])
    return joined

mhw = np.zeros(hot.shape, dtype=np.uint8)
n_seg0 = n_seg1 = 0
lens0, lens1 = [], []
for i in range(60):
    for j in range(60):
        if not sea[i, j]: continue
        h = hot[:, i, j]
        if not h.any(): continue
        segs = []
        k = 0; n = 92
        while k < n:
            if h[k]:
                m = k
                while m < n and h[m]: m += 1
                if m - k >= 5: segs.append([k, m-1])
                k = m
            else:
                k += 1
        n_seg0 += len(segs)
        lens0 += [e-s+1 for s, e in segs]
        if not segs: continue
        joined = [list(segs[0])]
        for s, e in segs[1:]:
            if s - joined[-1][1] - 1 <= 2: joined[-1][1] = e
            else: joined.append([s, e])
        n_seg1 += len(joined)
        lens1 += [e-s+1 for s, e in joined]
        for s, e in joined: mhw[s:e+1, i, j] = 1

print("raw runs >=5d: %d (len %d..%d d) | after gap-join: %d (len %d..%d d)" %
      (n_seg0, min(lens0), max(lens0), n_seg1, min(lens1), max(lens1)))
print("mhw cell-days: %d | land cells all zero: %s" % (int(mhw.sum()), bool(not mhw[:, ~sea].any())))

# regional events: active day = any sea cell in MHW; maximal runs of consecutive active days
active = mhw.any(axis=2).any(axis=1) & np.ones(len(dates), dtype=bool)
active = mhw.reshape(len(dates), -1).any(axis=1)
print("active days: %d of %d" % (int(active.sum()), len(dates)))
events = []
k = 0
while k < len(dates):
    if active[k]:
        m = k
        while m < len(dates) and active[m]: m += 1
        events.append((dates[k], dates[m-1]))
        k = m
    else:
        k += 1
print("regional events: %d" % len(events))
for s, e in events:
    print("  onset %s  end %s  (%d days)" % (s.isoformat(), e.isoformat(), (e-s).days+1))
np.savez_compressed("/work/cache_mhw.npz", mhw=mhw, active=active)
print("saved /work/cache_mhw.npz")
