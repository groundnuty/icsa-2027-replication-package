import numpy as np, json, datetime as dt
import xarray as xr

# --- verify the NetCDF ---
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("dims:", dict(ds.sizes))
m = ds['mhw']
print("mhw dtype:", m.dtype, "| attrs:", dict(m.attrs))
mv = m.values
print("mhw unique values:", np.unique(mv), "| shape:", mv.shape)
print("time:", str(ds.time.values[0])[:10], "..", str(ds.time.values[-1])[:10], "| n:", ds.sizes['time'])
print("lat:", float(ds.lat[0]), "..", float(ds.lat[-1]), "| lon:", float(ds.lon[0]), "..", float(ds.lon[-1]))

# --- verify report ---
with open('output/report.json') as f_:
    rep = json.load(f_)
print("report keys:", sorted(rep.keys()))
print("events:", rep['events'])
assert set(rep.keys()) == {"region","baseline_analysed","target_analysed","events","complete","caveats"}
assert all(set(e.keys()) == {"onset","end"} for e in rep['events'])

# --- verify mask consistency with independent recomputation ---
mhw_mask = np.load('work/mhw_mask.npy')
print("mask identical to pipeline result:", np.array_equal(mv.astype(bool), mhw_mask))

# --- re-verify regional events from the file's own mask ---
T = np.load('work/T.npy').astype(np.float64)
thr_s = np.load('work/thr_s.npy')
def leap(y): return y%4==0 and (y%100!=0 or y%400==0)
def doy_of(d):
    n = (d - dt.date(d.year,1,1)).days + 1
    if d.month >= 3 and not leap(d.year): n += 1
    return n
tdates = [dt.date(2021,6,1)+dt.timedelta(days=i) for i in range(92)]
hot = np.isfinite(T) & (T >= thr_s[[doy_of(d)-1 for d in tdates]])
# per-cell MHW + events, all in one fresh pass
def runs(h):
    idx = np.flatnonzero(h)
    if len(idx)==0: return []
    brk = np.flatnonzero(np.diff(idx)>1)
    st = np.concatenate([[idx[0]], idx[brk+1]]); en = np.concatenate([idx[brk], [idx[-1]]])
    return [(int(a), int(b)) for a, b in zip(st, en)]
active = np.zeros(92, bool)
n_pc = 0
for i in range(60):
    for j in range(60):
        h = hot[:, i, j]
        cand = [(a,b) for a,b in runs(h) if b-a+1 >= 5]
        if not cand: continue
        merged = [list(cand[0])]
        for a,b in cand[1:]:
            if a - merged[-1][1] - 1 <= 2: merged[-1][1] = b
            else: merged.append([a,b])
        for a,b in merged:
            active[a:b+1] = True; n_pc += 1
evs = runs(active)
print("re-verified regional events:", [(tdates[a].isoformat(), tdates[b].isoformat()) for a,b in evs])
print("re-verified n per-cell MHWs:", n_pc)
# report events match file-derived events?
rep_ev = [(e['onset'], e['end']) for e in rep['events']]
file_ev = [(tdates[a].isoformat(), tdates[b].isoformat()) for a,b in evs]
print("report events == re-verified:", rep_ev == file_ev)

# --- final file listing ---
import os
for p in ['output/mhw_mask.nc', 'output/report.json']:
    print(p, os.path.getsize(p), "bytes")
