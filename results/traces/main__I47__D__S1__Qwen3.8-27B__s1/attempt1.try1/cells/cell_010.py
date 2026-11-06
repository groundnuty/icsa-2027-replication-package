import numpy as np, datetime as dt, time
data = np.load('/work/S.npz', allow_pickle=True)
S_base = data['S_base']; S_tgt = data['S_tgt']
reg_lat = data['reg_lat']; reg_lon = data['reg_lon']
dates = [dt.date.fromisoformat(s) for s in data['dates']]
n_base = 4028
base_dates = dates[:n_base]   # 1991-12-27 .. 2003-01-05
tgt_dates  = dates[n_base:]   # 2019-06-01 .. 2019-08-31
assert base_dates[0].isoformat()=='1991-12-27' and base_dates[-1].isoformat()=='2003-01-05'
assert tgt_dates[0].isoformat()=='2019-06-01' and tgt_dates[-1].isoformat()=='2019-08-31'

def doy(d):
    # (month,day)-based leap-year-template day-of-year: Jan1=1, Feb28=59, Feb29=60, Mar1=61, Dec31=366
    return (d.replace(year=2020) - dt.date(2020,1,1)).days + 1

# sanity checks of the mapping
assert doy(dt.date(2019,1,1))==1 and doy(dt.date(2019,2,28))==59 and doy(dt.date(2020,2,29))==60
assert doy(dt.date(2019,3,1))==61 and doy(dt.date(2019,12,31))==366 and doy(dt.date(2019,8,31))==244

sea = np.isfinite(S_tgt).all(axis=0)
n_sea = int(sea.sum())
print("sea cells:", n_sea, "land:", 3600-n_sea)
Sb = S_base[:, sea].astype(np.float64)
St = S_tgt[:, sea].astype(np.float64)

# baseline date indices and their doys
d0 = base_dates[0]
bidx = [(b - d0).days for b in base_dates]
bl_start = (dt.date(1992,1,1) - d0).days
bl_end   = (dt.date(2002,12,31) - d0).days
baseline_pos = np.arange(bl_start, bl_end+1)          # positions in S_base
bl_doy = np.array([doy(base_dates[p]) for p in baseline_pos])

# pool t-sets per doy d (d != 60): union of [b-5, b+5] over baseline positions with doy==d
pools = {}
for d in range(1, 367):
    if d == 60: continue
    pos = baseline_pos[bl_doy == d]
    lo = pos.min() - 5; hi = pos.max() + 5
    tset = np.arange(max(lo,0), min(hi, n_base-1)+1)
    pools[d] = tset

sizes = {d: len(p) for d,p in pools.items()}
print("pool size set:", set(sizes.values()))
# verify all 11 years represented per pool
for d in (1, 59, 61, 153, 244, 365, 366):
    pos = baseline_pos[bl_doy == d]
    print(d, "n baseline dates:", len(pos), "pool size:", len(pools[d]))
