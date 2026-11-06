import xarray as xr, json
m=xr.open_dataset('/work/../output/mhw_mask.nc',engine='h5netcdf') if False else xr.open_dataset('output/mhw_mask.nc',engine='h5netcdf')
print(m.mhw.dims, m.mhw.shape, m.mhw.dtype, int(m.mhw.sum()), str(m.time.values[0])[:10], str(m.time.values[-1])[:10])
print(json.load(open('output/report.json'))['events'])