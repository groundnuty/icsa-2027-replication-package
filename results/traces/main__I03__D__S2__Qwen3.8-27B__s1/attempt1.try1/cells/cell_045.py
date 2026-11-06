import numpy as np, xarray as xr, json

o = xr.open_dataset('/work/output/mhw_mask.nc')
print(o)
mhw = o.mhw
assert o.mhw.dtype == np.uint8, o.mhw.dtype
assert o.mhw.dims == ('time','lat','lon')
assert o.time.size == 92 and o.lat.size == 60 and o.lon.size == 60
assert str(o.time.values[0]) == '2014-06-01T00:00:00.000000000'
assert str(o.time.values[-1]) == '2014-08-31T00:00:00.000000000'
print("lat first/last:", o.lat.values[0], o.lat.values[-1])
print("lon first/last:", o.lon.values[0], o.lon.values[-1])
print("unique mhw values:", np.unique(mhw.values))
assert set(np.unique(mhw.values).tolist()) <= {0,1}

# coordinates match source dataset exactly
src = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
assert np.array_equal(o.lat.values, src.latitude.values[34:94])
assert np.array_equal(o.lon.values, src.longitude.values[213:273])
assert np.array_equal(o.time.values, src.time.values[10226:10318]) if False else True
i0 = int(np.searchsorted(src.time.values, np.datetime64('2014-06-01')))
assert np.array_equal(o.time.values, src.time.values[i0:i0+92])

# re-derive events from the file itself
flat = mhw.values.reshape(92, -1).any(axis=1)
ev = []
i = 0
td = pd.to_datetime(o.time.values) if (import_pd := __import__('pandas')) else None
td = __import__('pandas').to_datetime(o.time.values)
while i < 92:
    if flat[i]:
        j = i
        while j+1 < 92 and flat[j+1]: j += 1
        ev.append((str(td[i].date()), str(td[j].date()))); i = j+1
    else: i += 1
print("events re-derived from output file:", ev)

r = json.load(open('/work/output/report.json'))
assert set(r.keys()) == {"region","baseline_analysed","target_analysed","events","complete","caveats"}
assert [ (e["onset"], e["end"]) for e in r["events"] ] == ev
assert r["complete"] is True and isinstance(r["caveats"], str)
print("report.json fields OK; events consistent:", ev)
print("ALL CHECKS PASSED")
