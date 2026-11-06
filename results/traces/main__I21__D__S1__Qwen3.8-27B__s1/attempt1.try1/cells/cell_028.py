import numpy as np, datetime
z = np.load('/work/region.npz'); s = np.load('/work/doy_stats.npz')
tgt = z['tgt_sst']                    # (92,60,60) float64
st = s['sm_thresh']                   # (366,3600)
tgt_doy = s['target_doy']             # (92,)
lat, lon = z['lat'], z['lon']
NC = 60*60
st2 = st.reshape(366, 60, 60)
tgt3 = tgt.reshape(92, NC)

sea = np.all(np.isfinite(tgt), axis=0)          # per flattened cell
nsea = int(sea.sum())
print("sea cells:", nsea)

# hot: (92, 3600) ; land compares NaN>=thr -> False, fine
thr_t = st[tgt_doy - 1, :]                      # (92, 3600)
hot = tgt3 >= thr_t
hot &= sea[None, :]
print("hot fraction over all cells/days:", hot.mean())
print("hot days per day (range):", hot.sum(axis=1).min(), hot.sum(axis=1).max())

def mhw_events_1d(hot):
    n = len(hot)
    pad = np.concatenate(([False], hot, [False]))
    d = np.diff(pad.astype(np.int8))
    starts = np.where(d == 1)[0]
    ends = np.where(d == -1)[0] - 1
    kept = [(int(a), int(b)) for a, b in zip(starts, ends) if b - a + 1 >= 5]
    evs = []
    for a, b in kept:
        if evs and a - evs[-1][1] - 1 <= 2:
            evs[-1] = (evs[-1][0], b)
        else:
            evs.append((a, b))
    out = np.zeros(n, bool)
    for a, b in evs:
        out[a:b+1] = True
    return out, evs

def brute_mhw_1d(hot):
    # independent: mark days in merged hot runs via expansion
    n = len(hot)
    in_mhw = np.zeros(n, bool)
    # a day t is in an MHW if it belongs to a kept run or to a <=2 gap between kept runs
    i = 0
    evs = []
    while i < n:
        if hot[i]:
            j = i
            while j+1 < n and hot[j+1]:
                j += 1
            if j - i + 1 >= 5:
                evs.append([i, j])
            i = j + 1
        else:
            i += 1
    merged = []
    for a, b in evs:
        if merged and a - merged[-1][1] - 1 <= 2:
            merged[-1][1] = b
        else:
            merged.append([a, b])
    out = np.zeros(n, bool)
    for a, b in merged:
        out[a:b+1] = True
    return out, merged

mhw = np.zeros((92, NC), bool)
ev_count = 0
mismatch = 0
for c in range(NC):
    if not sea[c]:
        continue
    m, evs = mhw_events_1d(hot[:, c])
    m2, evs2 = brute_mhw_1d(hot[:, c])
    if not np.array_equal(m, m2):
        mismatch += 1
    mhw[:, c] = m
    ev_count += len(evs)
print("cells with any MHW:", int(mhw.any(axis=0).sum()), "total per-cell MHWs:", ev_count, "mismatches vs brute:", mismatch)

active = mhw.any(axis=1)
print("active days:", int(active.sum()), "of 92")
# regional events
reg = []
i = 0
while i < 92:
    if active[i]:
        j = i
        while j+1 < 92 and active[j+1]:
            j += 1
        reg.append((i, j))
        i = j + 1
    else:
        i += 1
dates = [datetime.date.fromisoformat(x) for x in z['tgt_dates']]
for a, b in reg:
    print("regional event:", dates[a], "->", dates[b], "len", b-a+1)
np.savez('/work/mhw.npz', mhw=mhw, active=active, sea=sea,
         reg=np.array(reg) if reg else np.zeros((0,2), int))
print("saved")
