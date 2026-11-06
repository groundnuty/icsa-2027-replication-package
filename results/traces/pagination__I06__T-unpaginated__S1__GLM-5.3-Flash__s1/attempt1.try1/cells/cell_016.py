import numpy as np, datetime as dt, pickle, json

thr = np.load('/tmp/thr.npy')      # entry j = day j+1
clim = np.load('/tmp/clim.npy')
targ_sst = np.load('/tmp/targ_sst.npy')
with open('/tmp/meta.pkl','rb') as f: meta = pickle.load(f)
targ_dates = [dt.date.fromisoformat(s) for s in meta['targ_dates']]

def doy366(d):
    if d.month==2 and d.day==29: return 60
    if d.month<=2: return (d-dt.date(d.year,1,1)).days+1
    return 61+(d-dt.date(d.year,3,1)).days

targ_doy = np.array([doy366(d) for d in targ_dates])
print("target doys:", targ_doy[0], "...", targ_doy[-1], "n:", len(targ_doy))
assert targ_doy[0]==153 and targ_doy[-1]==244

sea = np.isfinite(targ_sst.astype(np.float64)).all(axis=0)
n_land = int((~sea).sum())
base_sst = np.load('/tmp/base_sst.npy')
land_base = ~np.isfinite(base_sst.astype(np.float64)).all(axis=0)
print("land in target:", n_land, " nonfinite-all-baseline-window cells:", int(land_base.sum()),
      " same mask:", np.array_equal(sea, ~land_base))

sst64 = targ_sst.astype(np.float64)
thr_day = thr[targ_doy - 1]                 # (92,60,60)
clim_day = clim[targ_doy - 1]
hot = sst64 >= thr_day                      # NaN >= x -> False
print("hot days total (cell-days):", int(hot.sum()), " of sea cell-days:", int(sea.sum())*92)
print("hot on land cells:", int(hot[:, ~sea].sum()))

# margin check for numerical robustness of >= comparisons
margins = np.where(np.isfinite(sst64) & np.isfinite(thr_day), sst64 - thr_day, np.nan)
fin = np.abs(margins[np.isfinite(margins)])
print("min |sst - thr| over all comparisons (K):", fin.min())

# per-cell MHW: runs >=5, join gaps of 1-2 days
def runs_bool(mask1d):
    idx = np.flatnonzero(mask1d)
    if idx.size == 0: return []
    splits = np.flatnonzero(np.diff(idx) > 1)
    out = []
    start = 0
    for s in splits:
        out.append((idx[start], idx[s])); start = s+1
    out.append((idx[start], idx[-1]))
    return out

targ_str = [d.isoformat() for d in targ_dates]
mhw_mask = np.zeros(sst64.shape, dtype=np.uint8)
n_candidates = 0; n_merged = 0; cand_lens = []; merged_lens = []
for i in range(60):
    for j in range(60):
        if not sea[i,j]:
            continue
        cand = [r for r in runs_bool(hot[:, i, j]) if r[1]-r[0]+1 >= 5]
        n_candidates += len(cand)
        cand_lens += [r[1]-r[0]+1 for r in cand]
        merged = []
        for s,e in cand:
            if merged and s - merged[-1][1] - 1 in (1,2):
                merged[-1] = (merged[-1][0], e)
            else:
                merged.append((s,e))
        n_merged += len(merged)
        merged_lens += [e-s+1 for s,e in merged]
        for s,e in merged:
            mhw_mask[s:e+1, i, j] = 1

print("candidate runs (>=5):", n_candidates, " merged per-cell MHWs:", n_merged)
print("candidate len min/med/max:", min(cand_lens), int(np.median(cand_lens)), max(cand_lens))
print("merged len min/med/max:", min(merged_lens), int(np.median(merged_lens)), max(merged_lens))
print("per-cell MHW cell-days:", int(mhw_mask.sum()))

# regional events
active = mhw_mask.any(axis=(1,2))            # any sea cell in MHW
print("active days:", int(active.sum()), "of", len(active))
ev = runs_bool(active)
events = [(targ_str[s], targ_str[e]) for s,e in ev]
print("regional events:")
for s,e in events:
    sd = dt.date.fromisoformat(s); ed = dt.date.fromisoformat(e)
    print("  ", s, "->", e, f"({(ed-sd).days+1} days)")

np.save('/tmp/mhw_mask.npy', mhw_mask)
np.save('/tmp/active.npy', active)
np.save('/tmp/hot.npy', hot)
with open('/tmp/events.pkl','wb') as f:
    pickle.dump(events, f)
print("saved mask, active, events")
