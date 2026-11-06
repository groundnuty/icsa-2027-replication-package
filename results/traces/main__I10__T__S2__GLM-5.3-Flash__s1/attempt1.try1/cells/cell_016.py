import numpy as np, pandas as pd

d = np.load("work/coords.npz"); t_tgt = pd.to_datetime(d['t_tgt'])
m = np.load("work/mhw.npz"); mhw, hot, active = m['mhw'], m['hot'], m['active']
c = np.load("work/clim.npz"); thr, sea, tgt = c['thr'], c['sea'], c['tgt']
nt = len(t_tgt)

def describe_cell_runs(ci_flat):
    col = hot.reshape(nt,-1)[:, ci_flat]
    starts = list(np.where((~col[:-1]) & col[1:])[0] + 1)
    if col[0]: starts = [0] + starts
    ends = list(np.where(col[:-1] & (~col[1:]))[0])
    if col[-1]: ends = ends + [nt-1]
    return [(s,e,e-s+1) for s,e in zip(starts,ends)]

for idx in [30, 31, 32, 49]:
    cells = np.where(mhw[idx].ravel())[0]
    print(f"--- {t_tgt[idx].date()}: {len(cells)} cell(s) in MHW")
    for ci in cells:
        runs = describe_cell_runs(ci)
        in_mhw = [r for r in runs if r[0] <= idx <= r[1] and (r[2] >= 5)]
        lat_i, lon_i = divmod(int(ci), 60)
        print(f"   cell (lat {lat_i}, lon {lon_i}) hot runs (start,end,len): {runs}  -> MHW runs: {in_mhw}")

# the single hot cell on 2005-07-01 (idx 30) and why it's not in an MHW
cells30 = np.where(hot[30].ravel())[0]
for ci in cells30:
    lat_i, lon_i = divmod(int(ci), 60)
    print(f"idx30 hot cell (lat {lat_i}, lon {lon_i}) runs: {describe_cell_runs(int(ci))}")
# threshold values near event for a central sea cell (lat 30, lon 30)
li, oi = 30, 30
print("central cell SST vs thr vs clm 07-02..07-20:")
CUM = np.load("work/clim.npz")['clm']
for i in range(30, 51):
    dd = 152 + (i)  # dummy, use stored doy
print("sample thresholds (doy 184..202) at cell (30,30):", np.round(thr[30,30,183:203],2))
print("sample SST           at cell (30,30):", np.round(tgt[30:50,30,30],2))
