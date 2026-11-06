import numpy as np, datetime as dt, json, os
import xarray as xr

mhw_mask = np.load('work/mhw_mask.npy')   # (92, 60, 60) bool
tdates = [dt.date(2021,6,1)+dt.timedelta(days=i) for i in range(92)]
T = np.load('work/T.npy')

# regional events from mask
active = mhw_mask.any(axis=(1,2))
idx = np.flatnonzero(active)
brk = np.flatnonzero(np.diff(idx) > 1)
ss = np.concatenate([[idx[0]], idx[brk+1]]); ee = np.concatenate([idx[brk], [idx[-1]]])
events = [(int(a), int(b)) for a, b in zip(ss, ee)]
for a, b in events:
    print("event:", tdates[a].isoformat(), "->", tdates[b].isoformat(), f"({b-a+1} d)")

os.makedirs('output', exist_ok=True)
lat = np.load('work/lat.npy') if os.path.exists('work/lat.npy') else None
lon = np.load('work/lon.npy') if os.path.exists('work/lon.npy') else None
print("lat/lon cached:", lat is not None, lon is not None)
