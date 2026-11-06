
import fsspec, xarray as xr, numpy as np
fs = fsspec.filesystem('onedata')
base = '/icsa2027_data_20261101T090944Z/s1z'
p = f'{base}/sst_20140601.nc'
with fs.open(p, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    v = ds['analysed_sst']
    print("encoding:", v.encoding)
    sst = v.values
# check a land-like cell: look at corners of region
i0 = 278; j0 = 613
sub = sst[0, i0:i0+60, j0:j0+60]
print("NaNs:", np.isnan(sub).sum())
print("min of finite:", np.nanmin(sub))
# check raw data for fill: use raw=True
with fs.open(p, 'rb') as f:
    ds2 = xr.open_dataset(f, engine='h5netcdf', decode_cf=False)
    v2 = ds2['analysed_sst']
    print("raw attrs:", v2.attrs)
    sub2 = v2.values[0, i0:i0+60, j0:j0+60]
    import collections
    c = collections.Counter()
    for val in sub2[~np.isfinite(sub2) if sub2.dtype.kind=='f' else np.ones(sub2.shape,bool)]:
        pass
    rawvals = sub2.ravel()
    print("raw unique count:", len(np.unique(rawvals)))
    print("raw min/max:", rawvals.min(), rawvals.max())
