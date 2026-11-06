import numpy as np, datetime
z = np.load('/work/region.npz'); s = np.load('/work/doy_stats.npz')
tgt = z['tgt_sst']; st = s['sm_thresh']; tgt_doy = s['target_doy']
NC = 3600
st2 = st.reshape(366, NC)
tgt3 = tgt.reshape(92, NC)

sea = np.isfinite(tgt3).all(axis=0)
print("sea cells:", int(sea.sum()))
thr_t = st2[tgt_doy - 1, :]
hot = (tgt3 >= thr_t) & sea[None, :]
print("hot fraction:", round(float(hot.mean()),4), "hot cells/day min/max:", int(hot.sum(axis=1).min()), int(hot.sum(axis=1).max()))

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
    n = len(hot); i = 0; evs = []
    while i < n:
        if hot[i]:
            j = i
            while j+1 < n and hot[j+1]: j += 1
            if j - i + 1 >= 5: evs.append([i, j])
            i = j + 1
        else:
            i += 1
    merged = []
    for a, b in evs:
        if merged and a - merged[-1][1] - 1 <= 2: merged[-1][1] = b
        else: merged.append([a, b])
    out = np.zeros(n, bool)
    for a, b in merged: out[a:b+1] = True
    return out, merged

mhw = np.zeros((92, NC), bool)
ev_count = 0; mismatch = 0; cells_with = 0
for c in range(NC):
    if not sea[c]: continue
    m, evs = mhw_events_1d(hot[:, c])
    m2, _ = brute_mhw_1d(hot[:, c])
    if not np.array_equal(m, m2): mismatch += 1
    mhw[:, c] = m
    ev_count += len(evs)
    cells_with += 1 if m.any() else 0
print("cells with MHW:", cells_with, "per-cell MHWs:", ev_count, "mismatches:", mismatch)

active = mhw.any(axis=1)
print("active days:", int(active.sum()), "/92")
reg = []
i = 0
while i < 92:
    if active[i]:
        j = i
        while j+1 < 92 and active[j+1]: j += 1
        reg.append((i, j)); i = j + 1
    else:
        i += 1
dates = [datetime.date.fromisoformat(x) for x in z['tgt_dates']]
for a, b in reg:
    print("regional event:", dates[a], "->", dates[b], "len", b-a+1)
np.savez('/work/mhw.npz', mhw=mhw, active=active, sea=sea,
         reg=np.array(reg) if reg else np.zeros((0,2), int))
print("saved")
