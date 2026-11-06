import xarray as xr, numpy as np, json
ds = xr.open_dataset("output/mhw_mask.nc", engine="h5netcdf")
print(ds)
v = ds['mhw']
print("dtype:", v.dtype, "dims:", v.dims)
print("time:", v.time.values[0], "...", v.time.values[-1], "n:", v.time.size)
print("lat:", v.latitude.values[0], "...", v.latitude.values[-1], "n:", v.latitude.size)
print("lon:", v.longitude.values[0], "...", v.longitude.values[-1], "n:", v.longitude.size)
print("values:", np.unique(v.values), "sum:", int(v.values.sum()))
# consistency vs in-memory mask
st2 = np.load("cache/stage2.npz"); st1 = np.load("cache/stage1.npz"); d = np.load("cache/region.npz")
mhw = st2['mhw']; nsea_all = st1['nsea_all']
mask_full = np.zeros((92,60,60), np.uint8); mask_full[:, nsea_all.reshape(60,60)] = mhw
assert np.array_equal(v.values, mask_full)
# active days recomputed from file match events
active = (v.values.sum(axis=(1,2)) > 0)
dd = np.diff(active.view(np.int8))
starts = [int(i)+1 for i in np.flatnonzero(dd==1)] + ([0] if active[0] else [])
ends   = [int(i) for i in np.flatnonzero(dd==-1)] + ([91] if active[-1] else [])
tt = d['time_tgt']
file_events = [(str(tt[s])[:10], str(tt[e])[:10]) for s,e in zip(starts,ends)]
rep = json.load(open("output/report.json"))
rep_events = [(e['onset'], e['end']) for e in rep['events']]
print("file events :", file_events)
print("report events:", rep_events)
assert file_events == rep_events
assert set(rep.keys()) == {"region","baseline_analysed","target_analysed","events","complete","caveats"}
print("ALL FINAL CHECKS PASS")