import datetime as dt, os, fsspec, time
import xarray as xr, numpy as np

fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
os.makedirs('/work/data', exist_ok=True)
os.makedirs('/work/probe', exist_ok=True)

# region index (from probe): j0=329, j1=389, i0=550, i1=610
j0, j1, i0, i1 = 329, 389, 550, 610

def load_day(date):
    name = f"sst_{date:%Y%m%d}.nc"
    local = f"/work/data/{name}"
    fs.get(f"{base}/{name}", local)
    ds = xr.open_dataset(local, engine="h5netcdf")
    arr = ds["analysed_sst"].isel(time=0).values[j0:j1+1, i0:i1+1].astype(np.float64)
    t = ds["time"].values[0]
    ds.close()
    return arr, t

# probe 12 dates across period, verify time, coords, NaN mask consistency
probe = [dt.date(1991,12,28), dt.date(1992,1,1), dt.date(1992,2,29), dt.date(1996,2,29),
         dt.date(2002,12,31), dt.date(2003,1,4), dt.date(2012,6,1), dt.date(2012,7,15), dt.date(2012,8,31)]
t0 = time.time()
masks = []
for d in probe:
    arr, t = load_day(d)
    masks.append(np.isfinite(arr))
    pd = d.toordinal()
    expect = np.datetime64(f"{d:%Y-%m-%d}T00:00:00.000000000")
    print(f"{d} time={t} expect={expect} ok={t==expect} range=({np.nanmin(arr):.2f},{np.nanmax(arr):.2f}) finite={masks[-1].sum()}")
print(f"{len(probe)} files in {time.time()-t0:.2f}s")

# check mask consistency across probes
ref = masks[0]
same = all((m == ref).all() for m in masks)
print("all masks identical:", same)
if not same:
    for d, m in zip(probe, masks):
        print(d, int((m != ref).sum()))
np.save('/work/sea_mask_probe.npy', ref)
