import numpy as np, pickle, json, os
from datetime import date, timedelta

# ---------------- independent brute-force verification ----------------
block = np.load("/tmp/sst_block.npy")
alldays = open("/tmp/alldays.txt").read().split("\n")
nb = 4028
sea_cells = np.load("/tmp/sea_cells.npy")
thr = np.load("/tmp/thr_smooth.npy")
clim = np.load("/tmp/clim_smooth.npy")
pools = pickle.load(open("/tmp/pools.pkl","rb"))
target_days = alldays[nb:]; nt = len(target_days)
cum_before = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
def doy_of(s):
    m, d = int(s[5:7]), int(s[8:10]); return cum_before[m-1] + d

base = block[:nb].astype(np.float64)

# pick sample sea cells and sample doys in target range + edges
rng = np.random.default_rng(42)
flat_sea = np.flatnonzero(sea_cells.ravel())
sample_cells = rng.choice(flat_sea, 12, replace=False)
sample_doys = [46, 60, 138, 153, 160, 200, 220, 244, 274, 1, 366]

def hazen_list(vals, p=0.9):
    v = np.sort(np.asarray(vals, dtype=np.float64))
    k = len(v)
    if k == 0: return np.nan
    h = k * p + 0.5
    j = int(np.floor(h)); g = h - j
    j0 = min(max(j, 1), k); jp = min(max(j+1, 1), k)
    return v[j0-1] + g * (v[jp-1] - v[j0-1])

max_dt = 0.0; max_dc = 0.0
for c in sample_cells:
    r, l = divmod(int(c), 60)
    for d in sample_doys:
        if d == 60: continue
        vals = base[pools[d], r, l]
        vals = vals[np.isfinite(vals)]
        t_raw = hazen_list(vals)
        cl_raw = vals.mean() if len(vals) else np.nan
        # smoothed = mean of raw over d-15..d+15 (day 60 substituted)
        def raw_at(dd):
            if dd == 60:
                v59 = base[pools[59], r, l]; v59 = v59[np.isfinite(v59)]
                v61 = base[pools[61], r, l]; v61 = v61[np.isfinite(v61)]
                return (hazen_list(v59) + hazen_list(v61)) / 2, (v59.mean() + v61.mean()) / 2
            v = base[pools[dd], r, l]; v = v[np.isfinite(v)]
            return hazen_list(v), (v.mean() if len(v) else np.nan)
        acc_t = 0.0; acc_c = 0.0
        for off in range(-15, 16):
            rt, rc = raw_at((d + off - 1) % 366 + 1)
            acc_t += rt; acc_c += rc
        max_dt = max(max_dt, abs(acc_t/31.0 - thr[d-1, r, l]))
        max_dc = max(max_dc, abs(acc_c/31.0 - clim[d-1, r, l]))
print("brute-force vs pipeline: max |dthr| =", max_dt, " max |dclim| =", max_dc)

# independent per-cell MHW check (straight loop) on all cells, only over target window
sst = block[nb:].astype(np.float64)
tdoy = np.array([doy_of(s) for s in target_days])
hot = sst >= thr[tdoy - 1]
hot[:, ~sea_cells] = False
mhw_ref = np.zeros((nt, 60, 60), dtype=bool)
n_events_cell = 0
for r in range(60):
    for l in range(60):
        if not sea_cells[r, l]: continue
        days = [t for t in range(nt) if hot[t, r, l]]
        # group consecutive
        groups = []
        for t in days:
            if groups and t == groups[-1][-1] + 1: groups[-1].append(t)
            else: groups.append([t])
        # join groups separated by 1-2 non-hot days
        merged = []
        for g in groups:
            if merged and g[0] - merged[-1][-1] - 1 <= 2: merged[-1].extend(g)
            else: merged.append(list(g))
        for g in merged:
            if len(g) >= 5:
                n_events_cell += 1
                for t in g: mhw_ref[t, r, l] = True
mhw = np.load("/tmp/mhw_mask.npy")
print("per-cell mhw identical:", np.array_equal(mhw, mhw_ref), "| per-cell events:", n_events_cell)

# independent regional event check
active = mhw_ref.reshape(nt, -1).any(axis=1)
ev = []
t = 0
while t < nt:
    if active[t]:
        e = t
        while e + 1 < nt and active[e+1]: e += 1
        ev.append((target_days[t], target_days[e])); t = e + 1
    else: t += 1
print("events:", ev)
print("saved events file:", open("/tmp/events.txt").read().strip())
