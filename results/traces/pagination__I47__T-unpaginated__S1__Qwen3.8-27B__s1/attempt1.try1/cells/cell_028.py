
import xarray as xr, json, numpy as np, fsspec

ds = xr.open_dataset('/work/output/mhw_mask.nc')
print(ds)
m = ds['mhw'].values
print("dtype:", m.dtype, "shape:", m.shape)
print("unique values:", np.unique(m))
print("time[0], time[-1]:", ds['time'].values[0], ds['time'].values[-1], ds['time'].dtype)
print("lat range:", ds['latitude'].values[0], ds['latitude'].values[-1], ds['latitude'].dtype)
print("lon range:", ds['longitude'].values[0], ds['longitude'].values[-1], ds['longitude'].dtype)

# active days from mask
active_idx = np.where(m.any(axis=(1,2)))[0]
print("active days:", len(active_idx))
runs = []
s = p = active_idx[0]
for i in active_idx[1:]:
    if i == p + 1:
        p = i
    else:
        runs.append((s, p)); s = p = i
runs.append((s, p))
print("mask events:", [(str(ds['time'].values[a])[:10], str(ds['time'].values[b])[:10]) for a, b in runs])

rep = json.load(open('/work/output/report.json'))
print("report events:", [(e['onset'], e['end']) for e in rep['events']])
print("fields:", sorted(rep.keys()))
print("region:", rep['region'])
print("baseline_analysed:", rep['baseline_analysed'])
print("target_analysed:", rep['target_analysed'])
print("complete:", rep['complete'])
print("caveats len:", len(rep['caveats']))

# compare coordinates against source dataset exactly
fs = fsspec.filesystem('onedata')
f = fs.open('/icsa2027_data_20261101T090944Z/s1z/sst_20190601.nc', 'rb')
src = xr.open_dataset(f, engine="h5netcdf")
print("lat identical:", (src['latitude'].values[545:605] == ds['latitude'].values).all())
print("lon identical:", (src['longitude'].values[721:781] == ds['longitude'].values).all())
# check a few source land/sea cells match mask structure
sst0 = src['analysed_sst'].values[0, 545:605, 721:781]
print("land (NaN day0) all zero in mask:", bool((m[:, ~np.isfinite(sst0)] == 0).all()))
src.close(); f.close()
ds.close()
