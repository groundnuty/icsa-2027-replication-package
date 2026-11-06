import xarray as xr, numpy as np, json
ds = xr.open_dataset('/work/workspace/output/mhw_mask.nc', engine='netcdf4')
print(ds)
m = ds['mhw']
print("dtype:", m.dtype, "| dims:", m.dims, "| shape:", m.shape)
print("unique:", np.unique(m.values), "| sum:", int(m.values.sum()))
# cross-check against computed mask
mhw = np.load('/tmp/mhw_result.npz')['mhw']; sea = np.load('/tmp/thr_clim.npz')['sea']
ref = np.zeros((92,60,60), dtype=np.uint8); ref[:, sea] = mhw.astype(np.uint8)
print("grid equality:", np.array_equal(m.values, ref))
rep = json.load(open('/work/workspace/output/report.json'))
print(json.dumps(rep, indent=1))
# verify regional events derived from mask alone match report
mg = m.values.reshape(m.shape[0], -1)
act = mg.any(axis=1)
runs = []
s = None
for i,a in enumerate(act):
    if a and s is None: s = i
    if not a and s is not None: runs.append((s,i-1)); s=None
if s is not None: runs.append((s,len(act)-1))
tt = ds['time'].values.astype('datetime64[D]')
print("events from mask:", [(str(tt[a]), str(tt[b])) for a,b in runs])
