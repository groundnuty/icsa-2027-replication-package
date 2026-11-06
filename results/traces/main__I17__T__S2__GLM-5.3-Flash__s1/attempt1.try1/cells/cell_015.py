import numpy as np, datetime as dt, json, warnings

me = '/work/me/'
target = np.load(me+'target.npy')   # (92,60,60) float32, target period
base   = np.load(me+'base.npy')     # (4028,60,60) float32, 1991-12-27..2003-01-05
tt = np.load(me+'times_target.npy') # datetime64[s]
tb = np.load(me+'times_base.npy')

t64 = target.astype(np.float64)
b64 = base.astype(np.float64)
print("base days:", b64.shape, "first/last:", str(tb[0])[:10], str(tb[-1])[:10])

def doy366(d):  # month/day -> 1..366 (Feb29=60), via reference leap year 2000
    return dt.date(2000, d.month, d.day).timetuple().tm_yday

# seeds: integer day offsets from 1991-12-27 for each baseline date 1992-01-01..2002-12-31
epoch = dt.date(1991,12,27)
seeds = {d: [] for d in range(1,367)}
cur = dt.date(1992,1,1)
while cur <= dt.date(2002,12,31):
    seeds[doy366(cur)].append((cur-epoch).days)
    cur += dt.timedelta(days=1)
print("seed counts: d1=%d d59=%d d60=%d d61=%d d365=%d d366=%d" %
      (len(seeds[1]), len(seeds[59]), len(seeds[60]), len(seeds[61]), len(seeds[365]), len(seeds[366])))

Nb = b64.shape[0]
thr  = np.full((366,60,60), np.nan)
clim = np.full((366,60,60), np.nan)
used = np.zeros(Nb, bool)
warnings.filterwarnings('ignore')
for d in range(1,367):
    if d == 60:
        continue
    m = np.zeros(Nb, bool)
    for s in seeds[d]:
        m[max(0,s-5):min(Nb,s+6)] = True
    used |= m
    vals = b64[m]                                  # (pool_days, 3600)
    thr[d-1]  = np.nanquantile(vals, 0.9, axis=0, method='hazen')
    clim[d-1] = np.nanmean(vals, axis=0)

# day 60 = mean of days 59 and 61
thr[59]  = 0.5*(thr[58]  + thr[60])
clim[59] = 0.5*(clim[58] + clim[60])

def smooth31(x):  # centred 31-day circular moving mean along axis 0 (len 366)
    xp = np.concatenate([x[-15:], x, x[:15]], axis=0)
    cs = np.cumsum(xp, axis=0)
    cs = np.concatenate([np.zeros((1,)+x.shape[1:], dtype=np.float64), cs], axis=0)
    return (cs[31:] - cs[:-31]) / 31.0

thr_s  = smooth31(thr)
clim_s = smooth31(clim)
print("thr_s  range over all cells/doys: %.3f .. %.3f" % (np.nanmin(thr_s), np.nanmax(thr_s)))
print("clim_s range over all cells/doys: %.3f .. %.3f" % (np.nanmin(clim_s), np.nanmax(clim_s)))

sea = np.isfinite(target).all(axis=0)   # finite SST on every target day
print("sea cells: %d / %d" % (sea.sum(), sea.size))

used_idx = np.where(used)[0]
first_used = epoch + dt.timedelta(days=int(used_idx.min()))
last_used  = epoch + dt.timedelta(days=int(used_idx.max()))
print("baseline days used by pools: %s .. %s (%d days)" % (first_used, last_used, used.sum()))

tdates = [dt.date.fromisoformat(str(x.astype('datetime64[D]'))) for x in tt]
tdoys = np.array([doy366(d) for d in tdates], dtype=int)
print("target days:", len(tdates), str(tdates[0]), "..", str(tdates[-1]),
      " doy", tdoys.min(), "..", tdoys.max())

hot = t64 >= thr_s[tdoys-1]             # (92,60,60)
print("hot days total (all cells):", int(hot.sum()))

# runs of consecutive hot days per cell
padded = np.zeros((94,60,60), dtype=bool); padded[1:-1] = hot
dd = np.diff(padded.astype(np.int8), axis=0)
st = np.argwhere(dd == 1)    # run starts at hot index i
en = np.argwhere(dd == -1)   # run ends (exclusive) at hot index i
st_s = st[np.lexsort((st[:,0], st[:,2], st[:,1]))]
en_s = en[np.lexsort((en[:,0], en[:,2], en[:,1]))]
assert (st_s[:,1:] == en_s[:,1:]).all(), "start/end pairing failed"
lengths = en_s[:,0] - st_s[:,0]
print("all runs:", len(st_s), " runs >=5d:", int((lengths>=5).sum()))

iv = [(int(a[1]), int(a[2]), int(a[0]), int(b[0]))
      for a, b in zip(st_s[lengths>=5], en_s[lengths>=5])]
iv.sort(key=lambda r: (r[0], r[1], r[2]))

# join MHWs separated by 1-2 non-hot days, per cell
merged = []
curc = None; cur = None
for (y, x, s, e) in iv:
    if (y, x) != curc:
        if cur is not None: merged.append(cur)
        curc = (y, x); cur = [y, x, s, e]
    elif s - cur[3] <= 2:
        cur[3] = max(cur[3], e)
    else:
        merged.append(cur); cur = [y, x, s, e]
if cur is not None: merged.append(cur)
durs = [e-s for (_,_,s,e) in merged]
print("per-cell MHWs after join:", len(merged), " duration min/max:", min(durs), max(durs))

mhw = np.zeros((92,60,60), dtype=np.uint8)
for (y, x, s, e) in merged:
    mhw[s:e, y, x] = 1
mhw[:, ~sea] = 0

active = (mhw.astype(bool) & sea).any(axis=(1,2))
print("active days:", int(active.sum()), "/ 92")

ap = np.concatenate([[False], active, [False]])
dad = np.diff(ap.astype(np.int8))
events = [(tdates[int(a)], tdates[int(b)-1]) for a, b in zip(np.where(dad==1)[0], np.where(dad==-1)[0])]
for on, edd in events:
    print("regional event:", on, "->", edd, " (%d days)" % ((edd-on).days+1))

np.save(me+'thr_s.npy', thr_s); np.save(me+'clim_s.npy', clim_s)
np.save(me+'mhw.npy', mhw); np.save(me+'active.npy', active)
np.save(me+'tdoys.npy', tdoys)
json.dump({"events": [[str(a), str(b)] for a, b in events],
           "baseline_used": [str(first_used), str(last_used)],
           "sea_cells": int(sea.sum())}, open(me+'summary.json','w'))
print("analysis done")
