import fsspec, xarray as xr, io, numpy as np
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
for d in ['19920615','20021231','20030105','20070831']:
    with fs.open(f'{base}/sst_{d}.nc','rb') as f:
        ds = xr.open_dataset(f, engine='h5netcdf')
        print(d, '->', str(ds.time.values[0])[:10], ds.analysed_sst.shape,
              float(ds.analysed_sst.isel(time=0, latitude=300, longitude=500)),
              'nanfrac', float(np.isnan(ds.analysed_sst.values).mean()))
        ds.close()
