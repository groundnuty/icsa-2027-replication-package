import numpy as np, json
import xarray as xr
from datetime import date, timedelta

dat = np.load('/tmp/sst_data.npz')
master = dat['master']; target = dat['target']
chk = xr.open_dataset('output/mhw_mask.nc')
mask_out = chk['mhw'].values
lat_out, lon_out, t_out = chk['lat'].values, chk['lon'].values, chk['time'].values
chk.close()

def daterange(a,b):
    o=[]
    while a<=b: o.append(a); a+=timedelta(days=1)
    return o
base_dates = daterange(date(1991,12,27), date(2003,1,5))
tgt_dates  = daterange(date(2021,6,1), date(2021,8,31))
base_all   = daterange(date(1992,1,1), date(2002,12,31))
dmap = {x: i for i, x in enumerate(base_dates)}
mdays=[31,29,31,30,31,30,31,31,30,31,30,31]; cum=[0]
for m in mdays: cum.append(cum[-1]+m)
doyf = lambda m,dd: cum[m-1]+dd

def pool_dates_for(dd):
    s = set()
    for b in base_all:
        if doyf(b.month, b.day) == dd:
            for off in range(-5, 6):
                tt = b + timedelta(days=off)
                if date(1991,12,27) <= tt <= date(2003,1,5):
                    s.add(tt)
    return s

def hazen_p90(vals):
    v = sorted(vals); n = len(v)
    pos = min(max((n+1)*0.9 - 0.5, 0.0), n-1)
    lo = int(pos); site_g = pos-lo
    return v[lo] + (v[lo+1]-v[lo])*site_g if lo+1 < n else v[lo]

def indep_cell_mask(ri, ck):
    # threshold (smoothed) for every target day, independently
    thr_cache = {}
    def thrd(d):
        if d in thr_cache: return thr_cache[d]
        if d == 60:
            thr_cache[d] = 0.5*(thrd(59)+thrd(61)); return thr_cache[d]
        vals = [master[dmap[tt], ri, ck] for tt in pool_dates_for(d) if np.isfinite(master[dmap[tt], ri, ck])]
        thr_cache[d] = hazen_p90(vals)
        return thr_cache[d]
    hot = []
    for t in tgt_dates:
        dd = doyf(t.month, t.day)
        s = 0.0
        for k in range(-15, 16):
            d2 = dd + k
            while d2 > 366: d2 -= 366
            while d2 < 1: d2 += 366
            s += thrd(d2)
        thr_s = s/31.0
        hot.append(bool(target[:, ri, ck][0] >= thr_s))
    # MHW runs + merge
    runs = []
    i = 0
    while i < 92:
        if hot[i]:
            j = i
            while j+1 < 92 and hot[j+1]: j += 1
            runs.append([i, j]); i = j+1
        else:
            i += 1
    runs = [r for r in runs if r[1]-r[0]+1 >= 5]
    merged = []
    for s,e in runs:
        if merged and s - merged[-1][1] - 1 <= 2:
            merged[-1][1] = e
        else:
            merged.append([s,e])
    m = np.zeros(92, dtype=np.uint8)
    for s,e in merged: m[s:e+1] = 1
    return m, merged

sea_mask = np.isfinite(target).all(axis=0)
sea_cells = np.argwhere(sea_mask)
# verify all 3308 sea cells (independent impl) vs written mask
tot_mismatch = 0
worst = None
for (ri, ck) in sea_cells:
    m, merged = indep_cell_mask(ri, ck)
    d = int((m != mask_out[:, ri, ck]).sum())
    if d:
        tot_mismatch += d
        if worst is None: worst = (ri, ck, d)
print("independent full re-derivation: mismatched cell-days:", tot_mismatch, "of", 92*len(sea_cells), "first bad:", worst)

# land cells must be 0
land = ~sea_mask
print("land cells with any 1 in output:", int(mask_out[:, land].sum()), "(n land cells:", int(land.sum()), ")")

# event gap check: days 2021-06-17..19 (idx 16..18) must have zero active cells
idx16_18 = np.array([(t.date().isoformat() if hasattr(t,'date') else str(t)[:10]) for t in t_out])
gi = [i for i,t in enumerate(t_out) if str(t)[:10] in ("2021-06-17","2021-06-18","2021-06-19")]
print("gap days indices:", gi, "max mhw on those days:", int(mask_out[gi].max()))
# event boundaries
ev1_end = [i for i,t in enumerate(t_out) if str(t)[:10]=="2021-06-16"][0]
ev2_start = [i for i,t in enumerate(t_out) if str(t)[:10]=="2021-06-20"][0]
print("mhw sum on 06-16:", int(mask_out[ev1_end].sum()), " on 06-20:", int(mask_out[ev2_start].sum()),
      " on 07-20:", int(mask_out[[i for i,t in enumerate(t_out) if str(t)[:10]=='2021-07-20'][0]].sum()))

print(json.dumps(json.load(open('output/report.json')), indent=1)[:1200])
