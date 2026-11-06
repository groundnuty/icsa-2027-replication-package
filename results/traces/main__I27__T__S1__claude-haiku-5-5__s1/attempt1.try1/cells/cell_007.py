import fsspec, xarray as xr, numpy as np
fs = fsspec.filesystem('onedata')
B='icsa2027_data_20261101T090944Z/s1z/'
with fs.open(B+'sst_20080601.nc','rb') as f:
    ds=xr.open_dataset(f,engine='h5netcdf').load()
print(ds.attrs['comment'])
print(ds.analysed_sst.attrs)
la=ds.latitude.values.astype(float); lo=ds.longitude.values.astype(float)
ilat=np.where((la>=57.83-1e-6)&(la<=59.03+1e-6))[0]; ilon=np.where((lo>=17.41-1e-6)&(lo<=18.61+1e-6))[0]
print(len(ilat),len(ilon), la[ilat][[0,-1]], lo[ilon][[0,-1]])
sub=ds.analysed_sst.isel(latitude=ilat,longitude=ilon).values[0]
print(np.isfinite(sub).sum(), sub.size, np.nanmin(sub), np.nanmax(sub))